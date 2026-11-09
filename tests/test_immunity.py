"""Tests for collective immunity and propagation dynamics (Task T13)."""
from __future__ import annotations

import math
from typing import Any

import pytest

from swarmlab.detectors.immunity import RoundKinetics, SwarmImmunityTracker


def test_round_kinetics_initialization() -> None:
    """Verify RoundKinetics dataclass attributes and defaults."""
    kinetics = RoundKinetics(
        round_idx=1,
        active_infected=2,
        newly_recruited=3,
        breaches=4,
    )
    assert kinetics.round_idx == 1
    assert kinetics.active_infected == 2
    assert kinetics.newly_recruited == 3
    assert kinetics.breaches == 4

    default_breaches = RoundKinetics(
        round_idx=2,
        active_infected=0,
        newly_recruited=0,
    )
    assert default_breaches.breaches == 0


def test_clean_swarm_all_zeros() -> None:
    """A clean swarm with all zero entries has reproduction rate 0.0 and is damped."""
    tracker = SwarmImmunityTracker()
    for r in range(1, 5):
        tracker.record_round(round_idx=r, active_infected=0, newly_recruited=0, breaches=0)

    assert tracker.effective_reproduction_rate(1) is None
    for r in range(2, 5):
        rate = tracker.effective_reproduction_rate(r)
        assert rate is not None
        assert math.isclose(rate, 0.0)

    assert tracker.is_transmission_damped(window=3) is True
    assert tracker.predict_extinction_round() is None

    summary: dict[str, Any] = tracker.summary()
    assert summary["total_recruited"] == 0
    assert summary["total_breaches"] == 0
    assert summary["peak_active_infected"] == 0
    assert math.isclose(summary["mean_reproduction_rate"], 0.0)
    assert summary["extinction_predicted"] is False


def test_steady_transmission_not_damped() -> None:
    """Steady transmission with reproduction rate 1.0 across rounds is not damped."""
    tracker = SwarmImmunityTracker()
    for r in range(1, 6):
        tracker.record_round(round_idx=r, active_infected=5, newly_recruited=5, breaches=1)

    assert tracker.effective_reproduction_rate(1) is None
    for r in range(2, 6):
        rate = tracker.effective_reproduction_rate(r)
        assert rate is not None
        expected_rate = 5.0 / max(1, 5)
        assert math.isclose(rate, expected_rate)

    assert tracker.is_transmission_damped(window=3) is False
    assert tracker.predict_extinction_round() is None

    summary: dict[str, Any] = tracker.summary()
    assert summary["total_recruited"] == 25
    assert summary["total_breaches"] == 5
    assert summary["peak_active_infected"] == 5
    assert math.isclose(summary["mean_reproduction_rate"], 1.0)
    assert summary["extinction_predicted"] is False


def test_declining_transmission_damping_and_summary() -> None:
    """Declining transmission sequence detects damping and computes summary."""
    tracker = SwarmImmunityTracker()
    # Round 1: 1 active, 0 recruited
    tracker.record_round(round_idx=1, active_infected=1, newly_recruited=0, breaches=0)
    # Round 2: 2 active, 2 recruited (R_2 = 2 / 1 = 2.0)
    tracker.record_round(round_idx=2, active_infected=2, newly_recruited=2, breaches=1)
    # Round 3: 2 active, 2 recruited (R_3 = 2 / 2 = 1.0)
    tracker.record_round(round_idx=3, active_infected=2, newly_recruited=2, breaches=1)
    # Round 4: 2 active, 1 recruited (R_4 = 1 / 2 = 0.5)
    tracker.record_round(round_idx=4, active_infected=2, newly_recruited=1, breaches=0)
    # Round 5: 0 active, 0 recruited (R_5 = 0 / 2 = 0.0)
    tracker.record_round(round_idx=5, active_infected=0, newly_recruited=0, breaches=0)

    assert tracker.effective_reproduction_rate(1) is None

    r2 = tracker.effective_reproduction_rate(2)
    assert r2 is not None
    assert math.isclose(r2, 2.0 / 1.0)

    r3 = tracker.effective_reproduction_rate(3)
    assert r3 is not None
    assert math.isclose(r3, 2.0 / 2.0)

    r4 = tracker.effective_reproduction_rate(4)
    assert r4 is not None
    assert math.isclose(r4, 1.0 / 2.0)

    r5 = tracker.effective_reproduction_rate(5)
    assert r5 is not None
    assert math.isclose(r5, 0.0 / 2.0)

    # Trailing window of 3: R_3=1.0, R_4=0.5, R_5=0.0 -> mean = 0.5 < 1.0
    assert tracker.is_transmission_damped(window=3) is True

    summary: dict[str, Any] = tracker.summary()
    assert summary["total_recruited"] == 0 + 2 + 2 + 1 + 0
    assert summary["total_breaches"] == 0 + 1 + 1 + 0 + 0
    assert summary["peak_active_infected"] == 2
    expected_mean = (2.0 + 1.0 + 0.5 + 0.0) / 4.0
    assert math.isclose(summary["mean_reproduction_rate"], expected_mean)
    assert summary["extinction_predicted"] is True


def test_predict_extinction_round_synthetic_decay() -> None:
    """Predict extinction round on synthetic decaying sequences."""
    tracker = SwarmImmunityTracker()
    tracker.record_round(round_idx=1, active_infected=10, newly_recruited=0)
    tracker.record_round(round_idx=2, active_infected=10, newly_recruited=6)
    tracker.record_round(round_idx=3, active_infected=10, newly_recruited=4)
    tracker.record_round(round_idx=4, active_infected=10, newly_recruited=2)

    # R_2 = 0.6, R_3 = 0.4, R_4 = 0.2
    # Slope is -0.2 per round; zero reaches at round 5.
    predicted = tracker.predict_extinction_round(max_rounds=10)
    assert predicted == 5

    # If max_rounds is less than predicted round, returns None
    assert tracker.predict_extinction_round(max_rounds=4) is None


def test_predict_extinction_round_exponential_model() -> None:
    """Predict extinction round using exponential decay model."""
    tracker = SwarmImmunityTracker()
    tracker.record_round(round_idx=1, active_infected=1, newly_recruited=0)
    tracker.record_round(round_idx=2, active_infected=2, newly_recruited=2)
    tracker.record_round(round_idx=3, active_infected=2, newly_recruited=2)
    tracker.record_round(round_idx=4, active_infected=2, newly_recruited=1)

    # R_2 = 2.0, R_3 = 1.0, R_4 = 0.5
    exp_predicted = tracker.predict_extinction_round(max_rounds=10, decay_model="exponential")
    assert exp_predicted is not None
    assert exp_predicted >= 5


def test_predict_extinction_round_with_window() -> None:
    """Predict extinction round respecting explicit window parameter."""
    tracker = SwarmImmunityTracker()
    tracker.record_round(round_idx=1, active_infected=10, newly_recruited=0)
    tracker.record_round(round_idx=2, active_infected=10, newly_recruited=8)
    tracker.record_round(round_idx=3, active_infected=10, newly_recruited=6)
    tracker.record_round(round_idx=4, active_infected=10, newly_recruited=4)
    tracker.record_round(round_idx=5, active_infected=10, newly_recruited=2)

    assert tracker.predict_extinction_round(window=1) is None
    pred_w2 = tracker.predict_extinction_round(window=2)
    assert pred_w2 == 6


def test_predict_extinction_round_edge_cases() -> None:
    """Predict extinction round returns None when data is insufficient or non-decreasing."""
    tracker = SwarmImmunityTracker()
    assert tracker.predict_extinction_round() is None

    # Only one round
    tracker.record_round(round_idx=1, active_infected=5, newly_recruited=2)
    assert tracker.predict_extinction_round() is None

    # Two rounds gives only one R_t value; cannot fit decay
    tracker.record_round(round_idx=2, active_infected=5, newly_recruited=2)
    assert tracker.predict_extinction_round() is None

    # Increasing transmission
    rising_tracker = SwarmImmunityTracker()
    rising_tracker.record_round(round_idx=1, active_infected=10, newly_recruited=0)
    rising_tracker.record_round(round_idx=2, active_infected=10, newly_recruited=2)
    rising_tracker.record_round(round_idx=3, active_infected=10, newly_recruited=4)
    rising_tracker.record_round(round_idx=4, active_infected=10, newly_recruited=6)
    assert rising_tracker.predict_extinction_round() is None

    # Unsupported decay model
    with pytest.raises(ValueError, match="unsupported decay_model"):
        rising_tracker.predict_extinction_round(decay_model="invalid")


def test_effective_reproduction_rate_validation() -> None:
    """Non-existent or non-consecutive rounds return None for reproduction rate."""
    tracker = SwarmImmunityTracker()
    tracker.record_round(round_idx=1, active_infected=5, newly_recruited=2)
    tracker.record_round(round_idx=3, active_infected=5, newly_recruited=2)

    assert tracker.effective_reproduction_rate(0) is None
    assert tracker.effective_reproduction_rate(1) is None
    # Round 2 missing, so round 3 has no round 2 to compute denominator
    assert tracker.effective_reproduction_rate(3) is None
    assert tracker.effective_reproduction_rate(99) is None


def test_invalid_input_validation() -> None:
    """Tracker validates round indices, counts, and window sizes."""
    tracker = SwarmImmunityTracker()
    with pytest.raises(ValueError, match="round_idx must be positive"):
        tracker.record_round(round_idx=0, active_infected=0, newly_recruited=0)

    with pytest.raises(ValueError, match="active_infected must be non-negative"):
        tracker.record_round(round_idx=1, active_infected=-1, newly_recruited=0)

    with pytest.raises(ValueError, match="newly_recruited must be non-negative"):
        tracker.record_round(round_idx=1, active_infected=0, newly_recruited=-1)

    with pytest.raises(ValueError, match="breaches must be non-negative"):
        tracker.record_round(round_idx=1, active_infected=0, newly_recruited=0, breaches=-1)

    with pytest.raises(ValueError, match="window must be positive"):
        tracker.is_transmission_damped(window=0)


def test_tracker_history_immutability() -> None:
    """Mutating returned history does not mutate internal tracker state."""
    tracker = SwarmImmunityTracker()
    tracker.record_round(round_idx=1, active_infected=1, newly_recruited=0)
    history = tracker.history
    history.clear()
    assert len(tracker.history) == 1


def test_damped_no_computed_rates_with_recruits() -> None:
    """Single round with non-zero recruits has no computed R_t and is not damped."""
    tracker = SwarmImmunityTracker()
    tracker.record_round(round_idx=1, active_infected=1, newly_recruited=1)
    assert tracker.is_transmission_damped() is False
