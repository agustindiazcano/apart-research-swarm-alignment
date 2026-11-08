"""Threshold computation and persistence utilities for detectors."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from swarmlab.metrics.stats import smoothed_threshold_at_fpr, threshold_at_fpr


@dataclass(frozen=True)
class ThresholdSet:
    """Decision threshold values for a detector at a target false positive rate."""

    detector: str
    target_fpr: float
    raw: float
    smoothed: float
    n_negatives: int


def compute_thresholds(
    detector: str, negative_scores: Sequence[float], target_fpr: float
) -> ThresholdSet:
    """Compute empirical and smoothed thresholds from negative calibration scores."""
    raw = threshold_at_fpr(negative_scores, target_fpr)
    smoothed = smoothed_threshold_at_fpr(negative_scores, target_fpr)
    return ThresholdSet(
        detector=detector,
        target_fpr=target_fpr,
        raw=raw,
        smoothed=smoothed,
        n_negatives=len(negative_scores),
    )


def select_negatives(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Select non-recruitment, non-leak messages regardless of sender state."""
    return [
        row
        for row in rows
        if not bool(row.get("l1", False))
        and not bool(row.get("l2", False))
    ]


def save_thresholds(path: Path, sets: Sequence[ThresholdSet]) -> None:
    """Write standard JSON; null raw thresholds represent no attainable cutoff."""
    data = {}
    for item in sets:
        record = asdict(item)
        if item.raw == float("inf"):
            record["raw"] = None
        data[f"{item.detector}@{item.target_fpr}"] = record
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n"
    path.write_bytes(serialized.encode("utf-8"))


def load_thresholds(path: Path) -> dict[str, ThresholdSet]:
    """Load threshold sets from JSON keyed by detector@target_fpr."""
    raw_bytes = path.read_bytes()
    data = json.loads(raw_bytes.decode("utf-8"))
    result: dict[str, ThresholdSet] = {}
    if isinstance(data, dict):
        for key, val in data.items():
            result[key] = ThresholdSet(
                detector=str(val["detector"]),
                target_fpr=float(val["target_fpr"]),
                raw=float("inf") if val["raw"] is None else float(val["raw"]),
                smoothed=float(val["smoothed"]),
                n_negatives=int(val["n_negatives"]),
            )
    elif isinstance(data, list):
        for val in data:
            item = ThresholdSet(
                detector=str(val["detector"]),
                target_fpr=float(val["target_fpr"]),
                raw=float("inf") if val["raw"] is None else float(val["raw"]),
                smoothed=float(val["smoothed"]),
                n_negatives=int(val["n_negatives"]),
            )
            result[f"{item.detector}@{item.target_fpr}"] = item
    return result


def realized_fpr(negative_scores: Sequence[float], threshold: float) -> float:
    """Calculate the fraction of negative scores at or above the threshold."""
    arr = np.asarray(negative_scores, dtype=float)
    n = len(arr)
    if n == 0:
        raise ValueError("negative_scores must not be empty")
    return float(np.mean(arr >= threshold))
