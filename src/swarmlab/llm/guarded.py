"""Guarded LLM client applying budget caps, rate limiting, and cost tracking."""

from __future__ import annotations

import asyncio
import logging
import math
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from swarmlab.llm.budget import BudgetGuard
from swarmlab.llm.limiter import (
    CallFailed,
    CallPolicy,
    CallStats,
    ProviderLimiter,
    call_with_policy,
)
from swarmlab.schema import LLMClient, LLMResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PriceTable:
    """Pricing configuration in USD per one million tokens."""

    input_per_m: float
    output_per_m: float

    def __post_init__(self) -> None:
        if any(
            not math.isfinite(price) or price < 0.0
            for price in (self.input_per_m, self.output_per_m)
        ):
            raise ValueError("Token prices must be finite and nonnegative")


class GuardedClient:
    """Wraps an LLMClient with budget checks, rate limits, and cost accounting."""

    def __init__(
        self,
        inner: LLMClient,
        guard: BudgetGuard,
        limiter: ProviderLimiter,
        policy: CallPolicy,
        prices: PriceTable,
        *,
        provider: str,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._inner = inner
        self._guard = guard
        self._limiter = limiter
        self._policy = policy
        self._prices = prices
        self._provider = provider
        self._sleep = sleep
        self.stats = CallStats()
        self.last_cost_usd: float = 0.0

    def cost_of(self, result: LLMResult) -> float:
        """Return the configured token cost for this result, independent of other calls."""
        return (
            result.tokens_in * self._prices.input_per_m
            + result.tokens_out * self._prices.output_per_m
        ) / 1_000_000.0

    async def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int = 256,
        logprobs: bool = False,
    ) -> LLMResult:
        """Authorize against budget, acquire rate limit semaphore, call model, and record cost."""
        self._guard.authorize(self._provider)

        sem = self._limiter.semaphore(self._provider)
        async with sem:
            async def authorized_call() -> LLMResult:
                # Queued calls and retries recheck the budget before sending a request.
                # Charges for concurrent in-flight requests are unknown until they return;
                # this check does not reserve their eventual cost.
                self._guard.authorize(self._provider)
                return await self._inner.complete(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    logprobs=logprobs,
                )

            try:
                result, call_stats = await call_with_policy(
                    authorized_call,
                    self._policy,
                    sleep=self._sleep,
                )
            except CallFailed as exc:
                self.stats.attempts += exc.stats.attempts
                self.stats.retries += exc.stats.retries
                self.stats.timeouts += exc.stats.timeouts
                raise

            self.stats.attempts += call_stats.attempts
            self.stats.retries += call_stats.retries
            self.stats.timeouts += call_stats.timeouts

        cost = self.cost_of(result)
        self.last_cost_usd = cost
        self._guard.record(self._provider, cost)

        if not result.timestamp_utc:
            result.timestamp_utc = datetime.now(UTC).isoformat()

        logger.debug(
            "Call finished for provider %s: cost=%.6f USD, tokens_in=%d, tokens_out=%d",
            self._provider,
            cost,
            result.tokens_in,
            result.tokens_out,
        )
        return result
