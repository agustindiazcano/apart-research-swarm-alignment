"""Guarded LLM client applying budget caps, rate limiting, and cost tracking."""

from __future__ import annotations

import asyncio
import logging
import math
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypedDict

from swarmlab.llm.budget import BillingUnit, BudgetCapMissing, BudgetGuard
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
    """Prices in the declared unit per one million tokens, without currency conversion."""

    input_per_m: float
    output_per_m: float
    unit: BillingUnit = "usd"

    def __post_init__(self) -> None:
        if self.unit not in ("usd", "credits"):
            raise ValueError("Price billing unit must be usd or credits")
        if any(
            not math.isfinite(price) or price < 0.0
            for price in (self.input_per_m, self.output_per_m)
        ):
            raise ValueError("Token prices must be finite and nonnegative")


class CostRecord(TypedDict):
    """Per-result cost with one populated amount and its billing unit."""

    cost_usd: float | None
    cost_credits: float | None
    billing_unit: BillingUnit


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
        on_result: Callable[[LLMResult, CallStats, CostRecord], None] | None = None,
    ) -> None:
        try:
            guard_unit = guard.unit(provider)
        except BudgetCapMissing:
            # Preserve the deferred missing-cap check in complete, before any call.
            pass
        else:
            if guard_unit != prices.unit:
                raise ValueError(
                    f"Billing unit mismatch for {provider}: "
                    f"budget={guard_unit}, prices={prices.unit}"
                )
        self._inner = inner
        self._guard = guard
        self._limiter = limiter
        self._policy = policy
        self._prices = prices
        self._provider = provider
        self._sleep = sleep
        self._on_result = on_result
        self.stats = CallStats()
        self.last_cost_usd: float | None = 0.0 if prices.unit == "usd" else None
        self.last_cost_credits: float | None = 0.0 if prices.unit == "credits" else None

    @property
    def billing_unit(self) -> BillingUnit:
        """Unit shared by token prices and this provider's budget."""
        return self._prices.unit

    def cost_of(self, result: LLMResult) -> float:
        """Return cost in billing_unit, independently of other calls or conversion rates."""
        return (
            result.tokens_in * self._prices.input_per_m
            + result.tokens_out * self._prices.output_per_m
        ) / 1_000_000.0

    def cost_record(self, result: LLMResult) -> CostRecord:
        """Return unit-tagged per-result amounts without labeling credits as USD."""
        amount = self.cost_of(result)
        return {
            "cost_usd": amount if self.billing_unit == "usd" else None,
            "cost_credits": amount if self.billing_unit == "credits" else None,
            "billing_unit": self.billing_unit,
        }

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
        self.last_cost_usd = cost if self.billing_unit == "usd" else None
        self.last_cost_credits = cost if self.billing_unit == "credits" else None
        if not result.timestamp_utc:
            result.timestamp_utc = datetime.now(UTC).isoformat()

        try:
            if self._on_result is not None:
                self._on_result(result, call_stats, self.cost_record(result))
        finally:
            # Persist returned usage even if the observer or budget check aborts the run.
            self._guard.record(self._provider, cost)

        logger.debug(
            "Call finished for provider %s: cost=%.6f %s, tokens_in=%d, tokens_out=%d",
            self._provider,
            cost,
            self.billing_unit,
            result.tokens_in,
            result.tokens_out,
        )
        return result
