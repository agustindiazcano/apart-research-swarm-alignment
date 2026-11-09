from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from datetime import datetime

import pytest

from swarmlab.llm.budget import BudgetCapMissing, BudgetExceeded, BudgetGuard
from swarmlab.llm.guarded import GuardedClient, PriceTable
from swarmlab.llm.limiter import CallPolicy, ProviderLimiter, RetryableError
from swarmlab.llm.mock import MockClient
from swarmlab.schema import LLMClient, LLMResult


class RecordingSleep:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


@pytest.mark.parametrize("price", [float("nan"), float("inf"), -1.0])
def test_prices_must_be_finite_and_nonnegative(price: float) -> None:
    with pytest.raises(ValueError):
        PriceTable(input_per_m=price, output_per_m=1.0)
    with pytest.raises(ValueError):
        PriceTable(input_per_m=1.0, output_per_m=price)


def test_guarded_client_has_complete_method() -> None:
    inner = MockClient(["ok"])
    guard = BudgetGuard({"test": 1.0})
    limiter = ProviderLimiter()
    policy = CallPolicy()
    prices = PriceTable(input_per_m=1.0, output_per_m=2.0)
    client: LLMClient = GuardedClient(
        inner, guard, limiter, policy, prices, provider="test"
    )
    assert hasattr(client, "complete")
    assert callable(client.complete)


@pytest.mark.asyncio
async def test_guarded_client_blocks_when_cap_missing() -> None:
    inner = MockClient(["ok"])
    guard = BudgetGuard({"other": 1.0})  # "test" provider missing
    limiter = ProviderLimiter()
    policy = CallPolicy()
    prices = PriceTable(input_per_m=1.0, output_per_m=2.0)
    client = GuardedClient(inner, guard, limiter, policy, prices, provider="test")

    with pytest.raises(BudgetCapMissing):
        await client.complete([{"role": "user", "content": "hello"}])


@pytest.mark.asyncio
async def test_guarded_client_blocks_at_cap() -> None:
    cap = 0.05  # fixture
    inner = MockClient(["ok"])
    guard = BudgetGuard({"test": cap})
    guard.record("test", cap)  # spent is at cap
    limiter = ProviderLimiter()
    policy = CallPolicy()
    prices = PriceTable(input_per_m=1.0, output_per_m=2.0)
    client = GuardedClient(inner, guard, limiter, policy, prices, provider="test")

    with pytest.raises(BudgetExceeded):
        await client.complete([{"role": "user", "content": "hello"}])


@pytest.mark.asyncio
async def test_guarded_client_records_exact_cost() -> None:
    input_price = 3.0  # fixture: 3.0 USD per million
    output_price = 15.0  # fixture: 15.0 USD per million
    prices = PriceTable(input_per_m=input_price, output_per_m=output_price)

    mock = MockClient(["response text for test"])
    guard = BudgetGuard({"test": 1.0})
    limiter = ProviderLimiter()
    policy = CallPolicy()
    client = GuardedClient(mock, guard, limiter, policy, prices, provider="test")

    res = await client.complete([{"role": "user", "content": "query message"}])

    # Formula derivation: (tokens_in * input_per_m + tokens_out * output_per_m) / 1e6
    expected_cost = (
        res.tokens_in * input_price + res.tokens_out * output_price
    ) / 1_000_000.0

    assert client.last_cost_usd == pytest.approx(expected_cost)
    assert guard.spent("test") == pytest.approx(expected_cost)


@pytest.mark.asyncio
async def test_guarded_client_retries_on_retryable_error() -> None:
    recorder = RecordingSleep()
    attempts = 0

    class TransientFailClient:
        async def complete(
            self,
            messages: Sequence[Mapping[str, str]],
            *,
            temperature: float | None = None,
            max_tokens: int = 256,
            logprobs: bool = False,
        ) -> LLMResult:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RetryableError("rate limit 429")
            return LLMResult(
                text="recovered",
                provider="test",
                model="test-m",
                response_id="test-1",
                tokens_in=10,
                tokens_out=5,
                latency_ms=0.0,
                timestamp_utc=datetime.now().isoformat(),
            )

    guard = BudgetGuard({"test": 1.0})
    limiter = ProviderLimiter()
    policy = CallPolicy(max_retries=2, backoff_base_s=0.5)
    prices = PriceTable(input_per_m=1.0, output_per_m=1.0)
    client = GuardedClient(
        TransientFailClient(),
        guard,
        limiter,
        policy,
        prices,
        provider="test",
        sleep=recorder,
    )

    res = await client.complete([{"role": "user", "content": "hi"}])
    assert res.text == "recovered"
    assert attempts == 2
    assert client.stats.attempts == 2
    assert client.stats.retries == 1
    assert len(recorder.delays) == 1


@pytest.mark.asyncio
async def test_guarded_client_concurrency_bounded_by_semaphore() -> None:
    concurrency_limit = 2  # fixture
    in_flight = 0
    max_in_flight = 0

    class ConcurrencyTrackingClient:
        async def complete(
            self,
            messages: Sequence[Mapping[str, str]],
            *,
            temperature: float | None = None,
            max_tokens: int = 256,
            logprobs: bool = False,
        ) -> LLMResult:
            nonlocal in_flight, max_in_flight
            in_flight += 1
            if in_flight > max_in_flight:
                max_in_flight = in_flight
            await asyncio.sleep(0.02)
            in_flight -= 1
            return LLMResult(
                text="ok",
                provider="test",
                model="test-m",
                response_id="c-1",
                tokens_in=4,
                tokens_out=4,
                latency_ms=0.0,
                timestamp_utc="",
            )

    guard = BudgetGuard({"test": 10.0})
    limiter = ProviderLimiter({"test": concurrency_limit})
    policy = CallPolicy()
    prices = PriceTable(input_per_m=1.0, output_per_m=1.0)
    client = GuardedClient(
        ConcurrencyTrackingClient(),
        guard,
        limiter,
        policy,
        prices,
        provider="test",
    )

    num_tasks = 6  # fixture: more than concurrency limit
    tasks = [client.complete([{"role": "user", "content": "hi"}]) for _ in range(num_tasks)]
    results = await asyncio.gather(*tasks)

    assert len(results) == num_tasks
    assert max_in_flight <= concurrency_limit
    # Verify timestamp was populated when empty
    for r in results:
        assert r.timestamp_utc != ""


@pytest.mark.asyncio
async def test_cost_of_each_result_survives_concurrent_calls() -> None:
    prices = PriceTable(input_per_m=3.0, output_per_m=7.0)
    client = GuardedClient(
        MockClient(["short", "a longer response with different token usage"]),
        BudgetGuard({"test": 1.0}),
        ProviderLimiter({"test": 2}),
        CallPolicy(),
        prices,
        provider="test",
    )
    results = await asyncio.gather(
        client.complete([{"role": "user", "content": "first"}]),
        client.complete([{"role": "user", "content": "second longer prompt"}]),
    )
    expected = [
        (r.tokens_in * prices.input_per_m + r.tokens_out * prices.output_per_m) / 10**6
        for r in results
    ]
    assert expected[0] != expected[1]
    assert [client.cost_of(r) for r in results] == pytest.approx(expected)


@pytest.mark.asyncio
async def test_queued_calls_recheck_budget_before_provider_request() -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    class WaitingClient:
        async def complete(
            self, messages: Sequence[Mapping[str, str]], *,
            temperature: float | None = None, max_tokens: int = 256,
            logprobs: bool = False,
        ) -> LLMResult:
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()
            return LLMResult("ok", "test", "fixture", "id", 1, 0, 0.0)

    client = GuardedClient(
        WaitingClient(), BudgetGuard({"test": 1.0}),
        ProviderLimiter({"test": 1}), CallPolicy(),
        PriceTable(input_per_m=10**6, output_per_m=0.0), provider="test",
    )
    first = asyncio.create_task(client.complete([]))
    await started.wait()
    second = asyncio.create_task(client.complete([]))
    await asyncio.sleep(0)
    release.set()
    outcomes = await asyncio.gather(first, second, return_exceptions=True)
    assert isinstance(outcomes[0], LLMResult)
    assert isinstance(outcomes[1], BudgetExceeded)
    assert calls == 1


@pytest.mark.asyncio
async def test_result_observer_retains_usage_before_budget_abort() -> None:
    observed: list[tuple[LLMResult, object, object]] = []
    guard = BudgetGuard({"test": 1.0})
    client = GuardedClient(
        MockClient(["reply"]), guard, ProviderLimiter(), CallPolicy(),
        PriceTable(input_per_m=2 * 10**6, output_per_m=0), provider="test",
        on_result=lambda result, stats, cost: observed.append((result, stats, cost)),
    )
    with pytest.raises(BudgetExceeded):
        await client.complete([{"role": "user", "content": "query"}])
    assert len(observed) == 1
    result, stats, cost = observed[0]
    assert result.response_id is not None
    assert stats.attempts == 1
    assert cost == client.cost_record(result)
    assert guard.spent("test") == client.cost_of(result)
