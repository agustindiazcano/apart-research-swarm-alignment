"""Budget guard for tracking and capping LLM provider spending."""

from __future__ import annotations

import logging
from collections.abc import Mapping

logger = logging.getLogger(__name__)


class BudgetError(Exception):
    """Base exception for budget errors."""


class BudgetCapMissing(BudgetError):
    """Raised when a provider has no spend cap configured."""


class BudgetExceeded(BudgetError):
    """Raised when spending exceeds the configured cap."""


class BudgetGuard:
    """Tracks and bounds spending per provider in USD."""

    def __init__(self, caps_usd: Mapping[str, float | None]) -> None:
        self._caps: dict[str, float | None] = dict(caps_usd)
        self._spent: dict[str, float] = {p: 0.0 for p in self._caps}

    def authorize(self, provider: str) -> None:
        """Authorize a call or raise if cap is missing or reached."""
        if provider not in self._caps:
            raise BudgetCapMissing(f"No budget cap configured for provider: {provider}")
        cap = self._caps[provider]
        if cap is None:
            raise BudgetCapMissing(f"Budget cap is None for provider: {provider}")
        spent = self._spent.get(provider, 0.0)
        if spent >= cap:
            raise BudgetExceeded(
                f"Budget cap of {cap:.4f} USD reached or exceeded for provider: {provider} "
                f"(spent: {spent:.4f} USD)"
            )

    def record(self, provider: str, cost_usd: float) -> None:
        """Record cost and raise BudgetExceeded if total exceeds cap."""
        if cost_usd < 0.0:
            raise ValueError(f"Cost cannot be negative: {cost_usd}")
        current = self._spent.get(provider, 0.0)
        new_total = current + cost_usd
        self._spent[provider] = new_total
        logger.debug(
            "Recorded %.6f USD for provider %s, total: %.6f USD",
            cost_usd,
            provider,
            new_total,
        )

        cap = self._caps.get(provider)
        if cap is not None and new_total > cap:
            raise BudgetExceeded(
                f"Spending of {new_total:.4f} USD exceeded cap of {cap:.4f} USD "
                f"for provider: {provider}"
            )

    def spent(self, provider: str) -> float:
        """Return total spent for a provider."""
        return self._spent.get(provider, 0.0)

    def remaining(self, provider: str) -> float:
        """Return remaining budget for a provider, raising if cap is missing."""
        if provider not in self._caps:
            raise BudgetCapMissing(f"No budget cap configured for provider: {provider}")
        cap = self._caps[provider]
        if cap is None:
            raise BudgetCapMissing(f"Budget cap is None for provider: {provider}")
        return cap - self._spent.get(provider, 0.0)

    def snapshot(self) -> dict[str, dict[str, float | None]]:
        """Return a snapshot of cap and spent for each configured provider."""
        return {
            provider: {
                "cap": self._caps[provider],
                "spent": self._spent.get(provider, 0.0),
            }
            for provider in self._caps
        }
