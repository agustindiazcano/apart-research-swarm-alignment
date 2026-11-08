"""Call policy, rate limiter, and concurrency management for LLM requests."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass(frozen=True)
class CallPolicy:
    """Retry, timeout, and backoff parameters for LLM calls."""

    timeout_s: float = 30.0
    max_retries: int = 3
    backoff_base_s: float = 1.0
    backoff_cap_s: float = 20.0


@dataclass
class CallStats:
    """Counters for call attempts, retries, and timeouts."""

    attempts: int = 0
    retries: int = 0
    timeouts: int = 0


class RetryableError(Exception):
    """Raised for transient provider failures and rate limits (e.g. HTTP 429)."""


class CallFailed(Exception):
    """Raised after all retries are exhausted under a CallPolicy."""

    def __init__(self, message: str = "", stats: CallStats | None = None) -> None:
        super().__init__(message)
        self.stats: CallStats = stats if stats is not None else CallStats()


async def call_with_policy(
    fn: Callable[[], Awaitable[T]],
    policy: CallPolicy,
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> tuple[T, CallStats]:
    """Execute fn with timeout and retries according to CallPolicy."""
    stats = CallStats()
    while True:
        stats.attempts += 1
        is_timeout = False
        is_retryable = False
        last_exc: BaseException | None = None
        try:
            res = await asyncio.wait_for(fn(), timeout=policy.timeout_s)
            return res, stats
        except TimeoutError as exc:
            stats.timeouts += 1
            is_timeout = True
            last_exc = exc
            logger.warning(
                "Call timed out after %.2f s (attempt %d)", policy.timeout_s, stats.attempts
            )
        except RetryableError as exc:
            is_retryable = True
            last_exc = exc
            logger.warning("Retryable error: %s (attempt %d)", exc, stats.attempts)

        if is_timeout or is_retryable:
            if stats.retries < policy.max_retries:
                delay = min(policy.backoff_cap_s, policy.backoff_base_s * (2**stats.retries))
                stats.retries += 1
                logger.debug("Sleeping %.2f s before retry %d", delay, stats.retries)
                await sleep(delay)
                continue

            msg = f"Call failed after {stats.attempts} attempts and {stats.retries} retries"
            failure_exc = CallFailed(msg, stats=stats)
            raise failure_exc from last_exc


class ProviderLimiter:
    """Manages per-provider asyncio semaphores for concurrency bounding."""

    def __init__(
        self,
        max_concurrency: Mapping[str, int] | None = None,
        default: int = 10,
    ) -> None:
        self._limits: dict[str, int] = dict(max_concurrency) if max_concurrency else {}
        self._default: int = default
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    def semaphore(self, provider: str) -> asyncio.Semaphore:
        """Return the asyncio.Semaphore for the specified provider."""
        if provider not in self._semaphores:
            limit = self._limits.get(provider, self._default)
            self._semaphores[provider] = asyncio.Semaphore(limit)
        return self._semaphores[provider]
