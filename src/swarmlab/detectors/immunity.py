"""Collective immunity and propagation dynamics tracker (Task T13)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import scipy.stats as st


@dataclass(frozen=True)
class RoundKinetics:
    """Kinetics observation recorded for one round."""

    round_idx: int
    active_infected: int
    newly_recruited: int
    breaches: int = 0


class SwarmImmunityTracker:
    """Tracks contagion dynamics over the discrete round horizon."""

    def __init__(self) -> None:
        self._history: list[RoundKinetics] = []
        self._by_round: dict[int, RoundKinetics] = {}

    @property
    def history(self) -> list[RoundKinetics]:
        """Return the sequence of recorded round kinetics."""
        return list(self._history)

    def record_round(
        self,
        round_idx: int,
        active_infected: int,
        newly_recruited: int,
        breaches: int = 0,
    ) -> None:
        """Record kinetics for a given round."""
        if round_idx < 1:
            raise ValueError(f"round_idx must be positive, got {round_idx}")
        if active_infected < 0:
            raise ValueError(f"active_infected must be non-negative, got {active_infected}")
        if newly_recruited < 0:
            raise ValueError(f"newly_recruited must be non-negative, got {newly_recruited}")
        if breaches < 0:
            raise ValueError(f"breaches must be non-negative, got {breaches}")

        kinetics = RoundKinetics(
            round_idx=round_idx,
            active_infected=active_infected,
            newly_recruited=newly_recruited,
            breaches=breaches,
        )
        self._history.append(kinetics)
        self._by_round[round_idx] = kinetics

    def effective_reproduction_rate(self, round_idx: int) -> float | None:
        """Compute the reproduction rate R_t = newly_recruited_t / max(1, active_infected_{t-1}).

        Returns None if round_idx <= 1 or if either round_idx or round_idx - 1 is absent.
        """
        if round_idx <= 1:
            return None
        curr = self._by_round.get(round_idx)
        prev = self._by_round.get(round_idx - 1)
        if curr is None or prev is None:
            return None

        denom = max(1, prev.active_infected)
        return float(curr.newly_recruited) / float(denom)

    def is_transmission_damped(self, window: int = 3) -> bool:
        """Return True if mean R_t over trailing window rounds is strictly below 1.0."""
        if window <= 0:
            raise ValueError(f"window must be positive, got {window}")

        rates: list[float] = []
        for rk in self._history:
            rate = self.effective_reproduction_rate(rk.round_idx)
            if rate is not None:
                rates.append(rate)

        if not rates:
            total_recruits = sum(rk.newly_recruited for rk in self._history)
            return total_recruits == 0

        trailing = rates[-window:]
        mean_rate = float(np.mean(trailing))
        return mean_rate < 1.0

    def predict_extinction_round(
        self,
        max_rounds: int = 10,
        *,
        window: int | None = None,
        decay_model: str = "linear",
    ) -> int | None:
        """Fit linear or exponential decay to recent positive R_t to project extinction round.

        Returns None if transmission is zero, non-decreasing, or projected round exceeds max_rounds.
        """
        if decay_model not in ("linear", "exponential"):
            raise ValueError(f"unsupported decay_model: {decay_model}")

        points: list[tuple[int, float]] = []
        for rk in self._history:
            rate = self.effective_reproduction_rate(rk.round_idx)
            if rate is not None and rate > 0.0:
                points.append((rk.round_idx, rate))

        if len(points) < 2:
            return None

        if window is not None:
            if window < 2:
                return None
            pts = points[-window:]
        else:
            max_val = max(p[1] for p in points)
            peak_idx = max(i for i, p in enumerate(points) if p[1] == max_val)
            pts = points[peak_idx:]

        if len(pts) < 2:
            return None

        t_arr = np.array([p[0] for p in pts], dtype=np.float64)
        if decay_model == "linear":
            r_arr = np.array([p[1] for p in pts], dtype=np.float64)
            res = st.linregress(t_arr, r_arr)
            slope = float(res.slope)
            intercept = float(res.intercept)

            if slope >= 0.0:
                return None

            t_zero = -intercept / slope
        elif decay_model == "exponential":
            log_r = np.log([p[1] for p in pts])
            res = st.linregress(t_arr, log_r)
            slope = float(res.slope)
            intercept = float(res.intercept)

            if slope >= 0.0:
                return None

            # Sub-unit threshold corresponds to less than one expected recruitment.
            threshold = 0.01
            t_zero = (math.log(threshold) - intercept) / slope
        else:
            raise ValueError(f"unsupported decay_model: {decay_model}")

        extinction_round = int(math.ceil(round(float(t_zero), 9)))
        if extinction_round < 1 or extinction_round > max_rounds:
            return None
        return extinction_round

    def summary(self) -> dict[str, Any]:
        """Return summary statistics dictionary for recorded rounds."""
        rates: list[float] = []
        for rk in self._history:
            rate = self.effective_reproduction_rate(rk.round_idx)
            if rate is not None:
                rates.append(rate)

        mean_rate = float(np.mean(rates)) if rates else 0.0
        total_recruited = sum(rk.newly_recruited for rk in self._history)
        total_breaches = sum(rk.breaches for rk in self._history)
        peak_active = max((rk.active_infected for rk in self._history), default=0)
        extinction_pred = self.predict_extinction_round() is not None

        return {
            "total_recruited": total_recruited,
            "total_breaches": total_breaches,
            "peak_active_infected": peak_active,
            "mean_reproduction_rate": mean_rate,
            "extinction_predicted": extinction_pred,
        }
