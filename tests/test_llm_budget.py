from __future__ import annotations

import pytest

from swarmlab.llm.budget import (
    BudgetCapMissing,
    BudgetError,
    BudgetExceeded,
    BudgetGuard,
)


def test_budget_error_hierarchy() -> None:
    assert issubclass(BudgetCapMissing, BudgetError)
    assert issubclass(BudgetExceeded, BudgetError)


def test_authorize_success_within_cap() -> None:
    fixture_cap = 10.0  # fixture
    guard = BudgetGuard({"provider_a": fixture_cap})
    guard.authorize("provider_a")
    assert guard.spent("provider_a") == 0.0
    assert guard.remaining("provider_a") == fixture_cap


def test_authorize_missing_provider_blocks_calls() -> None:
    guard = BudgetGuard({"provider_a": 10.0})
    with pytest.raises(BudgetCapMissing):
        guard.authorize("provider_unknown")


def test_authorize_none_cap_blocks_calls() -> None:
    guard = BudgetGuard({"provider_a": None})
    with pytest.raises(BudgetCapMissing):
        guard.authorize("provider_a")


def test_authorize_at_or_above_cap_raises_budget_exceeded() -> None:
    fixture_cap = 5.0  # fixture
    guard = BudgetGuard({"provider_a": fixture_cap})
    guard.record("provider_a", fixture_cap)
    with pytest.raises(BudgetExceeded):
        guard.authorize("provider_a")


def test_record_accumulates_and_updates_remaining() -> None:
    fixture_cap = 10.0  # fixture
    cost_first = 1.25  # fixture
    cost_second = 2.50  # fixture
    expected_total = cost_first + cost_second
    expected_remaining = fixture_cap - expected_total

    guard = BudgetGuard({"provider_a": fixture_cap})
    guard.record("provider_a", cost_first)
    guard.record("provider_a", cost_second)

    assert guard.spent("provider_a") == pytest.approx(expected_total)
    assert guard.remaining("provider_a") == pytest.approx(expected_remaining)


def test_record_negative_cost_raises_value_error() -> None:
    guard = BudgetGuard({"provider_a": 10.0})
    with pytest.raises(ValueError):
        guard.record("provider_a", -0.01)


def test_record_exceeding_cap_records_then_raises() -> None:
    fixture_cap = 5.0  # fixture
    cost_over = 6.0  # fixture

    guard = BudgetGuard({"provider_a": fixture_cap})
    with pytest.raises(BudgetExceeded):
        guard.record("provider_a", cost_over)

    # Must still record the total even when raising
    assert guard.spent("provider_a") == pytest.approx(cost_over)
    assert guard.remaining("provider_a") == pytest.approx(fixture_cap - cost_over)


def test_remaining_raises_when_cap_missing() -> None:
    guard = BudgetGuard({"provider_none": None})
    with pytest.raises(BudgetCapMissing):
        guard.remaining("provider_none")

    with pytest.raises(BudgetCapMissing):
        guard.remaining("provider_unknown")


def test_snapshot_returns_per_provider_cap_and_spent() -> None:
    caps = {"provider_a": 10.0, "provider_b": None}  # fixture
    cost_a = 3.5  # fixture
    guard = BudgetGuard(caps)
    guard.record("provider_a", cost_a)

    snap = guard.snapshot()
    assert snap == {
        "provider_a": {"cap": 10.0, "spent": cost_a},
        "provider_b": {"cap": None, "spent": 0.0},
    }
