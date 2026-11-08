"""Budgets and token prices retain their declared billing unit."""
from __future__ import annotations

import logging

import pytest

from swarmlab.llm.budget import BudgetCapMissing, BudgetExceeded, BudgetGuard
from swarmlab.llm.guarded import GuardedClient, PriceTable
from swarmlab.llm.limiter import CallPolicy, ProviderLimiter
from swarmlab.llm.mock import MockClient
from swarmlab.schema import LLMResult


def test_budget_snapshot_keeps_units_separate() -> None:
    guard = BudgetGuard({"muse": 20.0, "adaption": 500.0}, units={"adaption": "credits"})
    guard.record("muse", 1.5)
    guard.record("adaption", 3.0)
    assert guard.unit("muse") == "usd"
    assert guard.unit("adaption") == "credits"
    assert guard.snapshot() == {
        "muse": {"cap": 20.0, "spent": 1.5, "unit": "usd"},
        "adaption": {"cap": 500.0, "spent": 3.0, "unit": "credits"},
    }
    assert guard.remaining("muse") == pytest.approx(20.0 - 1.5)
    assert guard.remaining("adaption") == pytest.approx(500.0 - 3.0)


def test_unknown_unit_and_unconfigured_provider_mapping_rejected() -> None:
    with pytest.raises(ValueError, match="unit"):
        BudgetGuard({"adaption": 500.0}, units={"adaption": "tokens"})
    with pytest.raises(ValueError, match="provider"):
        BudgetGuard({"muse": 20.0}, units={"adaption": "credits"})
    with pytest.raises(ValueError, match="unit"):
        PriceTable(1.0, 2.0, unit="tokens")


def test_credit_cap_errors_and_logs_use_credits(caplog: pytest.LogCaptureFixture) -> None:
    guard = BudgetGuard({"adaption": 5.0}, units={"adaption": "credits"})
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(BudgetExceeded, match="credits"):
            guard.record("adaption", 6.0)
    assert "credits" in caplog.text
    assert "USD" not in caplog.text
    with pytest.raises(BudgetExceeded, match="credits"):
        guard.authorize("adaption")


@pytest.mark.parametrize("unit", ["usd", "credits"])
@pytest.mark.asyncio
async def test_guarded_cost_record_never_assigns_credits_to_usd(unit: str) -> None:
    guard = BudgetGuard({"fixture": 10.0}, units={"fixture": unit})
    prices = PriceTable(2.0, 5.0, unit=unit)
    client = GuardedClient(
        MockClient(["response"]), guard, ProviderLimiter(), CallPolicy(), prices,
        provider="fixture",
    )
    result = await client.complete([{"role": "user", "content": "question"}])
    amount = (
        result.tokens_in * prices.input_per_m + result.tokens_out * prices.output_per_m
    ) / 10**6
    assert client.billing_unit == unit
    assert client.cost_of(result) == pytest.approx(amount)
    assert client.cost_record(result) == {
        "cost_usd": amount if unit == "usd" else None,
        "cost_credits": amount if unit == "credits" else None,
        "billing_unit": unit,
    }
    assert client.last_cost_usd == (amount if unit == "usd" else None)
    assert client.last_cost_credits == (amount if unit == "credits" else None)
    assert guard.spent("fixture") == pytest.approx(amount)


@pytest.mark.parametrize("guard_unit,price_unit", [("credits", "usd"), ("usd", "credits")])
def test_guarded_constructor_rejects_unit_mismatch_before_inner_call(
    guard_unit: str, price_unit: str,
) -> None:
    inner = MockClient(["unused"])
    with pytest.raises(ValueError, match="unit"):
        GuardedClient(
            inner, BudgetGuard({"fixture": 10.0}, units={"fixture": guard_unit}),
            ProviderLimiter(), CallPolicy(), PriceTable(1.0, 2.0, unit=price_unit),
            provider="fixture",
        )
    assert inner.calls == []


@pytest.mark.asyncio
async def test_missing_credit_cap_blocks_provider() -> None:
    inner = MockClient(["unused"])
    client = GuardedClient(
        inner, BudgetGuard({"fixture": None}, units={"fixture": "credits"}),
        ProviderLimiter(), CallPolicy(), PriceTable(1.0, 2.0, unit="credits"), provider="fixture",
    )
    with pytest.raises(BudgetCapMissing, match="credits"):
        await client.complete([])
    assert inner.calls == []


def test_cost_record_is_per_result_without_shared_last_cost_state() -> None:
    prices = PriceTable(2.0, 3.0, unit="credits")
    client = GuardedClient(
        MockClient([]), BudgetGuard({"fixture": 10.0}, units={"fixture": "credits"}),
        ProviderLimiter(), CallPolicy(), prices, provider="fixture",
    )
    first = LLMResult("first", "fixture", "model", "r1", 2, 3, 0.0)
    second = LLMResult("second", "fixture", "model", "r2", 5, 7, 0.0)
    expected_first = (2 * prices.input_per_m + 3 * prices.output_per_m) / 10**6
    expected_second = (5 * prices.input_per_m + 7 * prices.output_per_m) / 10**6
    assert client.cost_record(second)["cost_credits"] == pytest.approx(expected_second)
    assert client.cost_record(first)["cost_credits"] == pytest.approx(expected_first)
    assert client.cost_record(first)["cost_usd"] is None
