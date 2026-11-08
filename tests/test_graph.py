"""Unit tests for the D3 graph-contextual score."""
from __future__ import annotations

import math

from swarmlab.detectors.graph import graph_logit, graph_score
from swarmlab.metrics.stats import logit


def _sigmoid(z: float) -> float:
    """Independent sigmoid implementation for verification."""
    return 1.0 / (1.0 + math.exp(-z))


def test_graph_score_empty_inbox_returns_d2_score() -> None:
    """When inbox is empty, graph score equals plain d2 score."""
    # Derivation: max((), default=0.0) == 0.0, so lam * indicator * 0.0 == 0.0.
    # Therefore graph_logit == logit(d2_score), and sigmoid(logit(p)) == p.
    test_scores = (0.05, 0.2, 0.5, 0.85)
    for s in test_scores:
        g_logit = graph_logit(s, (), lam=1.5, tau_floor=0.1)
        expected_logit = logit(s)
        assert math.isclose(g_logit, expected_logit, abs_tol=1e-7)

        g_score = graph_score(s, (), lam=1.5, tau_floor=0.1)
        assert math.isclose(g_score, s, abs_tol=1e-7)


def test_graph_score_absent_below_or_at_floor() -> None:
    """When d2_score <= tau_floor, the graph term is absent."""
    # Indicator(d2_score > tau_floor) is 0 for d2_score <= tau_floor.
    # Even with high inbox suspicion, benign outgoing replies must not be amplified.
    tau_floor = 0.3
    inbox = (0.85, 0.95, 0.7)
    lam = 2.0

    # Test strictly below floor
    s_below = 0.2
    assert graph_logit(s_below, inbox, lam=lam, tau_floor=tau_floor) == logit(s_below)
    assert math.isclose(graph_score(s_below, inbox, lam=lam, tau_floor=tau_floor), s_below)

    # Test exactly at floor
    s_at = tau_floor
    assert graph_logit(s_at, inbox, lam=lam, tau_floor=tau_floor) == logit(s_at)
    assert math.isclose(graph_score(s_at, inbox, lam=lam, tau_floor=tau_floor), s_at)


def test_graph_score_present_above_floor() -> None:
    """When d2_score > tau_floor, graph term amplifies score based on max inbox suspicion."""
    d2 = 0.4
    tau_floor = 0.25
    inbox = (0.1, 0.75, 0.4)
    lam = 1.2

    # Analytical derivation:
    # indicator = 1.0 (since 0.4 > 0.25)
    # max(inbox) = 0.75
    # expected_logit = logit(0.4) + 1.2 * 1.0 * 0.75
    expected_logit = logit(d2) + lam * 0.75
    expected_score = _sigmoid(expected_logit)

    computed_logit = graph_logit(d2, inbox, lam=lam, tau_floor=tau_floor)
    computed_score = graph_score(d2, inbox, lam=lam, tau_floor=tau_floor)

    assert math.isclose(computed_logit, expected_logit, rel_tol=1e-9)
    assert math.isclose(computed_score, expected_score, rel_tol=1e-9)
    assert computed_score > d2


def test_graph_score_monotone_in_lambda() -> None:
    """Score must be strictly non-decreasing with lambda when above floor and inbox > 0."""
    d2 = 0.5
    tau_floor = 0.3
    inbox = (0.6, 0.2)
    lambdas = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0)

    scores = [graph_score(d2, inbox, lam=lam_val, tau_floor=tau_floor) for lam_val in lambdas]
    for i in range(len(scores) - 1):
        assert scores[i] < scores[i + 1]


def test_graph_score_boundary_clipping() -> None:
    """Handles boundary d2 values (0.0 and 1.0) stably via logit clipping."""
    inbox = (0.5,)
    tau_floor = 0.1
    # At d2 = 0.0, d2 <= tau_floor, so indicator is 0
    score_zero = graph_score(0.0, inbox, lam=1.0, tau_floor=tau_floor)
    assert score_zero >= 0.0

    # At d2 = 1.0, d2 > tau_floor, score remains bounded in [0, 1]
    score_one = graph_score(1.0, inbox, lam=1.0, tau_floor=tau_floor)
    assert 0.0 <= score_one <= 1.0
