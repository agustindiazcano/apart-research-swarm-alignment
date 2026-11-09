"""D3 graph-contextual cascade score computation."""
from __future__ import annotations

import math
from collections.abc import Sequence

from swarmlab.metrics.stats import logit


def _sigmoid(z: float) -> float:
    """Compute numerically stable logistic sigmoid."""
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return float(ez / (1.0 + ez))


def graph_logit(
    d2_score: float,
    inbox_cached: Sequence[float],
    *,
    lam: float,
    tau_floor: float,
) -> float:
    """Compute graph logit combining local suspicion with sender inbox history.

    Calculates:
        logit(d2_score) + lam * indicator(d2_score > tau_floor) * max(inbox_cached, default=0.0)
    """
    indicator = 1.0 if d2_score > tau_floor else 0.0
    max_inbox = max(inbox_cached, default=0.0)
    return float(logit(d2_score) + lam * indicator * max_inbox)


def graph_score(
    d2_score: float,
    inbox_cached: Sequence[float],
    *,
    lam: float,
    tau_floor: float,
) -> float:
    """Compute graph score by applying sigmoid to graph logit."""
    z = graph_logit(d2_score, inbox_cached, lam=lam, tau_floor=tau_floor)
    return _sigmoid(z)
