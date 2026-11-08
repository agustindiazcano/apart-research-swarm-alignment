"""Budget guard for tracking and capping LLM provider spending."""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping
from typing import Literal, TypedDict

logger = logging.getLogger(__name__)
BillingUnit = Literal["usd", "credits"]


class BudgetSnapshot(TypedDict):
    """One provider's balance, without conversion to another unit."""

    cap: float | None
    spent: float
    unit: BillingUnit


class BudgetError(Exception):
    """Base exception for budget errors."""


class BudgetCapMissing(BudgetError):
    """Raised when a provider has no spend cap configured."""


class BudgetExceeded(BudgetError):
    """Raised when spending exceeds the configured cap."""


class BudgetGuard:
    """Track and bound spending in each provider's configured billing unit.

    The caps_usd parameter name is retained for compatibility. Its values use the
    provider's configured unit, which defaults to USD. No currency conversion occurs.
    """

    def __init__(
        self, caps_usd: Mapping[str, float | None], *,
        units: Mapping[str, BillingUnit] | None = None,
    ) -> None:
        if any(
            cap is not None and (not math.isfinite(cap) or cap < 0.0)
            for cap in caps_usd.values()
        ):
            raise ValueError("Budget caps must be finite and nonnegative, or None")
        self._caps: dict[str, float | None] = dict(caps_usd)
        if units is not None:
            if any(provider not in self._caps for provider in units):
                raise ValueError("Billing units reference an unconfigured provider")
            if any(unit not in ("usd", "credits") for unit in units.values()):
                raise ValueError("Billing unit must be usd or credits")
        self._units: dict[str, BillingUnit] = {
            provider: (units or {}).get(provider, "usd") for provider in self._caps
        }
        self._spent: dict[str, float] = {p: 0.0 for p in self._caps}

    def unit(self, provider: str) -> BillingUnit:
        """Return the configured unit, or fail for an unconfigured provider."""
        if provider not in self._units:
            raise BudgetCapMissing(f"No budget cap configured for provider: {provider}")
        return self._units[provider]

    def authorize(self, provider: str) -> None:
        """Authorize a call or raise if cap is missing or reached."""
        if provider not in self._caps:
            raise BudgetCapMissing(f"No budget cap configured for provider: {provider}")
        cap = self._caps[provider]
        unit = self.unit(provider)
        if cap is None:
            raise BudgetCapMissing(f"Budget cap in {unit} is None for provider: {provider}")
        spent = self._spent.get(provider, 0.0)
        if spent >= cap:
            raise BudgetExceeded(
                f"Budget cap of {cap:.4f} {unit} reached or exceeded for provider: {provider} "
                f"(spent: {spent:.4f} {unit})"
            )

    def record(self, provider: str, cost_usd: float) -> None:
        """Record cost in the provider unit; cost_usd retains its legacy parameter name."""
        unit = self.unit(provider)
        if not math.isfinite(cost_usd) or cost_usd < 0.0:
            raise ValueError("Cost must be finite and nonnegative")
        current = self._spent.get(provider, 0.0)
        new_total = current + cost_usd
        self._spent[provider] = new_total
        logger.debug(
            "Recorded %.6f %s for provider %s, total: %.6f %s",
            cost_usd,
            unit,
            provider,
            new_total,
            unit,
        )

        cap = self._caps.get(provider)
        if cap is not None and new_total > cap:
            raise BudgetExceeded(
                f"Spending of {new_total:.4f} {unit} exceeded cap of {cap:.4f} {unit} "
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
            raise BudgetCapMissing(
                f"Budget cap in {self.unit(provider)} is None for provider: {provider}"
            )
        return cap - self._spent.get(provider, 0.0)

    def snapshot(self) -> dict[str, BudgetSnapshot]:
        """Return separate balances and units; never sum USD and credits."""
        return {
            provider: {
                "cap": self._caps[provider],
                "spent": self._spent.get(provider, 0.0),
                "unit": self.unit(provider),
            }
            for provider in self._caps
        }
