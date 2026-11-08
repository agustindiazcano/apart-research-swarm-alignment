"""Tests for decision threshold utilities."""
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from swarmlab.detectors.thresholds import (
    ThresholdSet,
    compute_thresholds,
    load_thresholds,
    realized_fpr,
    save_thresholds,
    select_negatives,
)
from swarmlab.metrics.stats import smoothed_threshold_at_fpr, threshold_at_fpr


def test_compute_thresholds() -> None:
    # Fixture: negative scores sequence
    fixture_scores = [0.05, 0.12, 0.22, 0.35, 0.48, 0.61, 0.73, 0.84, 0.91, 0.98]
    target_fpr = 0.2

    expected_raw = threshold_at_fpr(fixture_scores, target_fpr)
    expected_smoothed = smoothed_threshold_at_fpr(fixture_scores, target_fpr)

    result = compute_thresholds("d1", fixture_scores, target_fpr)
    assert result.detector == "d1"
    assert result.target_fpr == target_fpr
    assert result.raw == expected_raw
    assert result.smoothed == expected_smoothed
    assert result.n_negatives == len(fixture_scores)


def test_select_negatives() -> None:
    # Fixture: message rows with various label combinations
    fixture_rows: list[Mapping[str, Any]] = [
        {"msg_id": "m1", "l1": False, "l2": False, "sender_infected": False},
        {"msg_id": "m2", "l1": True, "l2": False, "sender_infected": False},
        {"msg_id": "m3", "l1": False, "l2": True, "sender_infected": False},
        {"msg_id": "m4", "l1": False, "l2": False, "sender_infected": True},
        {"msg_id": "m5", "l1": False, "l2": False, "sender_infected": False},
    ]

    selected = select_negatives(fixture_rows)
    expected = [
        row
        for row in fixture_rows
        if not bool(row.get("l1", False))
        and not bool(row.get("l2", False))
    ]
    assert selected == expected
    assert [row["msg_id"] for row in selected] == ["m1", "m4", "m5"]


def test_realized_fpr() -> None:
    # Fixture: 100 uniformly spaced negative scores
    fixture_scores = [float(i) / 100.0 for i in range(1, 101)]

    for target_fpr in [0.02, 0.05, 0.10, 0.20]:
        t_set = compute_thresholds("d1", fixture_scores, target_fpr)
        fpr = realized_fpr(fixture_scores, t_set.raw)
        assert fpr <= target_fpr

        # Verify realized FPR matches direct count computation
        count_at_or_above = sum(1 for s in fixture_scores if s >= t_set.raw)
        expected_ratio = count_at_or_above / len(fixture_scores)
        assert fpr == pytest.approx(expected_ratio)


def test_realized_fpr_empty_raises() -> None:
    with pytest.raises(ValueError):
        realized_fpr([], 0.5)


def test_save_and_load_thresholds_roundtrip(tmp_path: Path) -> None:
    sets = [
        ThresholdSet(detector="d1", target_fpr=0.005, raw=0.45, smoothed=0.44, n_negatives=500),
        ThresholdSet(detector="d1", target_fpr=0.010, raw=0.40, smoothed=0.39, n_negatives=500),
    ]
    out_file = tmp_path / "thresholds.json"
    save_thresholds(out_file, sets)

    file_bytes = out_file.read_bytes()
    assert file_bytes.endswith(b"\n")

    parsed_json = json.loads(file_bytes.decode("utf-8"))
    assert list(parsed_json.keys()) == sorted(parsed_json.keys())

    loaded = load_thresholds(out_file)
    assert set(loaded.keys()) == {"d1@0.005", "d1@0.01"}
    assert loaded["d1@0.005"] == sets[0]
    assert loaded["d1@0.01"] == sets[1]


def test_unreachable_raw_threshold_uses_standard_json(tmp_path: Path) -> None:
    # Fixture: no observed threshold can meet the requested tail probability.
    threshold = compute_thresholds("d1", [i / 10 for i in range(10)], 0.005)
    assert math.isinf(threshold.raw)
    path = tmp_path / "thresholds.json"
    save_thresholds(path, [threshold])

    def reject_nonfinite(constant: str) -> object:
        raise ValueError(f"nonstandard JSON number: {constant}")

    data = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_nonfinite)
    assert data["d1@0.005"]["raw"] is None
    assert load_thresholds(path)["d1@0.005"] == threshold
