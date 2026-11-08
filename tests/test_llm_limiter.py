from __future__ import annotations

import asyncio
from typing import Any

import pytest

from swarmlab.llm.limiter import (
    CallFailed,
    CallPolicy,
    CallStats,
    ProviderLimiter,
    RetryableError,
    call_with_policy,
)


class RecordingSleep:
    """Records sleep durations instead of wall-clock sleeping."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


@pytest.mark.asyncio
async def test_call_with_policy_success_first_attempt() -> None:
    recorder = RecordingSleep()
    policy = CallPolicy()

    async def fn() -> str:
        return "ok"

    res, stats = await call_with_policy(fn, policy, sleep=recorder)
    assert res == "ok"
    assert stats.attempts == 1
    assert stats.retries == 0
    assert stats.timeouts == 0
    assert recorder.delays == []


@pytest.mark.asyncio
async def test_call_with_policy_retry_delay_sequence_and_exhaustion() -> None:
    recorder = RecordingSleep()
    base_s = 1.0  # fixture
    cap_s = 20.0  # fixture
    retries = 3  # fixture
    policy = CallPolicy(
        timeout_s=10.0,
        max_retries=retries,
        backoff_base_s=base_s,
        backoff_cap_s=cap_s,
    )

    attempts_made = 0

    async def fn() -> Any:
        nonlocal attempts_made
        attempts_made += 1
        raise RetryableError("rate limited")

    with pytest.raises(CallFailed) as exc_info:
        await call_with_policy(fn, policy, sleep=recorder)

    stats: CallStats = exc_info.value.stats
    # Analytic derivation: retry_index i from 0 to retries-1 gives base * 2^i capped at cap_s
    expected_delays = [min(cap_s, base_s * (2**i)) for i in range(retries)]
    expected_attempts = retries + 1

    assert recorder.delays == expected_delays
    assert stats.attempts == expected_attempts
    assert stats.retries == retries
    assert stats.timeouts == 0
    assert attempts_made == expected_attempts


@pytest.mark.asyncio
async def test_call_with_policy_backoff_cap_enforced() -> None:
    recorder = RecordingSleep()
    base_s = 1.0  # fixture
    cap_s = 3.0  # fixture
    retries = 3  # fixture
    policy = CallPolicy(
        timeout_s=10.0,
        max_retries=retries,
        backoff_base_s=base_s,
        backoff_cap_s=cap_s,
    )

    async def fn() -> Any:
        raise RetryableError("transient error")

    with pytest.raises(CallFailed):
        await call_with_policy(fn, policy, sleep=recorder)

    expected_delays = [min(cap_s, base_s * (2**i)) for i in range(retries)]
    assert recorder.delays == expected_delays


@pytest.mark.asyncio
async def test_call_with_policy_counts_timeouts() -> None:
    recorder = RecordingSleep()
    policy = CallPolicy(timeout_s=0.01, max_retries=2, backoff_base_s=0.5)

    async def hanging_fn() -> Any:
        await asyncio.sleep(1.0)
        return "done"

    with pytest.raises(CallFailed) as exc_info:
        await call_with_policy(fn=hanging_fn, policy=policy, sleep=recorder)

    stats = exc_info.value.stats
    expected_retries = 2
    expected_attempts = expected_retries + 1
    assert stats.timeouts == expected_attempts
    assert stats.retries == expected_retries
    assert stats.attempts == expected_attempts


@pytest.mark.asyncio
async def test_call_with_policy_non_retryable_propagates_immediately() -> None:
    recorder = RecordingSleep()
    policy = CallPolicy(max_retries=3)

    attempts = 0

    async def failing_fn() -> Any:
        nonlocal attempts
        attempts += 1
        raise ValueError("non-retryable issue")

    with pytest.raises(ValueError, match="non-retryable issue"):
        await call_with_policy(failing_fn, policy, sleep=recorder)

    assert attempts == 1
    assert recorder.delays == []


@pytest.mark.asyncio
async def test_provider_limiter_concurrency() -> None:
    limiter = ProviderLimiter({"fast": 2, "slow": 1}, default=3)
    sem_fast = limiter.semaphore("fast")
    sem_slow = limiter.semaphore("slow")
    sem_default = limiter.semaphore("other")

    # Same instance returned on subsequent calls
    assert limiter.semaphore("fast") is sem_fast

    # Check semaphore limits by acquiring concurrently
    acquired: list[str] = []

    async def worker(sem: asyncio.Semaphore, name: str) -> None:
        async with sem:
            acquired.append(name)
            await asyncio.sleep(0.01)

    t1 = asyncio.create_task(worker(sem_fast, "f1"))
    t2 = asyncio.create_task(worker(sem_fast, "f2"))
    t3 = asyncio.create_task(worker(sem_slow, "s1"))
    t4 = asyncio.create_task(worker(sem_default, "d1"))

    await asyncio.gather(t1, t2, t3, t4)
    assert len(acquired) == 4
