"""Generate analysis artifacts from episode logs and protocol manifests."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import t

from swarmlab.metrics.events import read_events
from swarmlab.metrics.extract import episode_summary, h2_rows, infection_state
from swarmlab.metrics.plots import KINETICS_COLUMNS, PANEL_B_COLUMNS, plot_kinetics
from swarmlab.metrics.stats import (
    bootstrap_ci,
    exact_mcnemar_p,
    holm_adjust,
    paired_bootstrap_diff_ci,
    wilson_interval,
)
from swarmlab.schema import EventRecord, GroundTruth

GROUP_KEYS = (
    "arm",
    "defense",
    "topology",
    "harm",
    "provider",
    "model",
    "billing_unit",
    "initial_infection",
    "mock",
)
REPORTED_ARMS = frozenset({"A0", "A1", "A3", "A3c", "A4"})


@dataclass
class _Episode:
    metadata: dict[str, Any]
    events: list[EventRecord]
    gt: GroundTruth | None
    summary: dict[str, Any]


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _within(path: Path, directory: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(directory.resolve()):
        raise ValueError(f"Source path escapes input directory: {path}")
    return resolved


def _source(path: Path, root: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _load(root: Path, allow_mock: bool) -> tuple[list[_Episode], list[dict[str, str]]]:
    selected: list[tuple[Path | None, dict[str, Any] | None]] = []
    sources: dict[str, dict[str, str]] = {}
    result_directories: list[Path] = []
    manifest_path: Path | None
    result: dict[str, Any] | None
    for result_path in sorted(root.rglob("result.json")):
        result = _read_json(result_path)
        sources[str(result_path)] = _source(result_path, root)
        result_directories.append(result_path.parent)
        log_path = result.get("log_path")
        if log_path:
            candidate = Path(log_path)
            if not candidate.is_absolute():
                candidate = result_path.parent / candidate
            manifest_path = _within(candidate, root).parent / "manifest.json"
            selected.append((manifest_path, result))
        else:
            selected.append((None, result))
    for manifest_path in sorted(root.rglob("manifest.json")):
        if any(manifest_path.is_relative_to(directory) for directory in result_directories):
            continue
        selected.append((manifest_path, None))
    episodes: list[_Episode] = []
    identities: set[tuple[Any, ...]] = set()
    episode_ids: set[str] = set()
    for manifest_path, result in selected:
        metadata = _read_json(manifest_path) if manifest_path else dict(result or {})
        if result is not None:
            for field in ("episode_id", "status", "seed", *GROUP_KEYS):
                if field in result and metadata.get(field) != result[field]:
                    raise ValueError(f"Selected attempt differs from result: {field}")
            metadata["attempts"] = result.get("attempts")
            metadata["attempt_history"] = result.get("attempt_history", [])
            for attempt in metadata["attempt_history"]:
                for path_key in ("manifest_path", "log_path"):
                    if not attempt.get(path_key):
                        continue
                    path = Path(attempt[path_key])
                    if not path.is_absolute():
                        path = root / path
                    path = _within(path, root)
                    if path.exists():
                        sources[str(path)] = _source(path, root)
        for key in (*GROUP_KEYS, "episode_id", "seed", "initial_infection", "mock", "status"):
            if key not in metadata:
                raise ValueError(f"Missing episode metadata: {key}")
        for key in ("mock", "initial_infection"):
            if type(metadata[key]) is not bool:
                raise ValueError(f"Episode metadata {key} must be boolean")
        if metadata["mock"] and not allow_mock:
            raise ValueError("mock episodes require --allow-mock and cannot be reported as real")
        if not metadata["mock"] and metadata["provider"] == "mock":
            raise ValueError("mock provider cannot be relabeled as real")
        if metadata["status"] not in {"complete", "failed", "budget_abort", "infra_failure"}:
            raise ValueError(f"Unknown episode status: {metadata['status']}")
        if metadata["status"] == "complete" and manifest_path is None:
            raise ValueError("Complete episode requires a selected manifest and event log")
        identity = tuple(metadata[key] for key in GROUP_KEYS) + (metadata["seed"],)
        if identity in identities or metadata["episode_id"] in episode_ids:
            raise ValueError("duplicate episode or condition/seed; select one final attempt")
        identities.add(identity)
        episode_ids.add(metadata["episode_id"])
        events: list[EventRecord] = []
        gt = None
        if manifest_path:
            sources[str(manifest_path)] = _source(manifest_path, root)
            directory = manifest_path.parent
            config = _within(directory / "config.yaml", directory)
            if config.exists():
                if hashlib.sha256(config.read_bytes()).hexdigest() != metadata.get("config_sha256"):
                    raise ValueError(f"config_sha256 mismatch: {config}")
                sources[str(config)] = _source(config, root)
            elif metadata["status"] == "complete":
                raise ValueError(f"Missing config.yaml: {directory}")
            events_path = _within(
                directory / metadata.get("events_path", "events.jsonl"), directory
            )
            truth_path = _within(
                directory / metadata.get("ground_truth_path", "gt.json"), directory
            )
            for path in (events_path, truth_path):
                if path.exists():
                    sources[str(path)] = _source(path, root)
                elif metadata["status"] == "complete":
                    raise ValueError(f"Missing complete episode source: {path}")
            if truth_path.exists():
                gt = GroundTruth.from_json(truth_path.read_text(encoding="utf-8"))
                for key, value in (
                    ("episode_id", gt.episode_id),
                    ("seed", gt.world_seed),
                    ("topology", gt.topology),
                    ("harm", gt.harm),
                ):
                    if metadata[key] != value:
                        raise ValueError(f"Ground truth differs from manifest: {key}")
            if events_path.exists():
                events = read_events(events_path)
                if any(event.episode_id != metadata["episode_id"] for event in events):
                    raise ValueError("Event episode_id differs from manifest")
                if not metadata["mock"]:
                    for event in events:
                        if event.kind == "llm_call" and (
                            not event.payload.get("response_id")
                            or not event.payload.get("provider")
                            or event.payload.get("provider") == "mock"
                        ):
                            raise ValueError(
                                "Real llm_call needs provider and response_id evidence"
                            )
        summary = (
            episode_summary(events, gt, initial_infection=metadata["initial_infection"])
            if gt is not None
            else {}
        )
        observed = bool(summary.get("exfiltrated", False))
        # Protocol metadata cannot replace a quantity extracted from the event log.
        summary = {**metadata, **summary}
        summary["observed_exfiltration"] = observed
        summary["outcome_unknown"] = not observed and metadata["status"] != "complete"
        summary["exfiltrated"] = None if summary["outcome_unknown"] else observed
        if gt is None:
            summary["utility"] = None
            summary["n_infected"] = None
        episodes.append(_Episode(metadata, events, gt, summary))
    if not episodes:
        raise ValueError("No episode manifests or result selectors found")
    return episodes, sorted(sources.values(), key=lambda item: item["path"])


def fit_h2(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Fit unpenalized H2 logistic regression with an episode-cluster sandwich interval."""
    exposed = [row for row in rows if row["total_solicitations_received"] >= 1]
    result: dict[str, Any] = {
        "status": "not_identifiable",
        "rows_exposed": len(exposed),
        "features": [
            "intercept",
            "distinct_infected_senders",
            "total_solicitations_received",
            "complete_topology",
        ],
    }
    if not exposed or len({row["distinct_infected_senders"] for row in exposed}) < 2:
        return {**result, "reason": "insufficient distinct-sender variation"}
    x = np.asarray(
        [
            [
                1.0,
                row["distinct_infected_senders"],
                row["total_solicitations_received"],
                float(row["topology"] == "complete"),
            ]
            for row in exposed
        ],
        dtype=float,
    )
    y = np.asarray([row["violated"] for row in exposed], dtype=float)
    if np.linalg.matrix_rank(x) != x.shape[1]:
        return {**result, "reason": "design matrix rank deficient"}
    clusters = sorted({str(row["episode_id"]) for row in exposed})
    result["episodes"] = len(clusters)
    if len(clusters) <= x.shape[1] or len(np.unique(y)) < 2:
        return {**result, "reason": "insufficient episodes or outcome variation"}

    def loss(beta: np.ndarray) -> float:
        eta = x @ beta
        return float(np.sum(np.logaddexp(0.0, eta) - y * eta))

    def gradient(beta: np.ndarray) -> np.ndarray:
        return x.T @ (expit(x @ beta) - y)

    fitted = minimize(
        loss,
        np.zeros(x.shape[1]),
        jac=gradient,
        method="BFGS",
        options={"gtol": 1e-7, "maxiter": 1000},
    )
    beta = np.asarray(fitted.x)
    if np.max(np.abs(gradient(beta))) > 1e-4 or np.max(np.abs(beta)) > 30:
        return {**result, "reason": "likelihood did not converge or separation suspected"}
    p = expit(x @ beta)
    information = x.T @ ((p * (1.0 - p))[:, None] * x)
    if np.linalg.cond(information) > 1e12:
        return {**result, "reason": "information matrix singular or ill-conditioned"}
    bread = np.linalg.inv(information)
    scores = []
    for cluster in clusters:
        mask = np.asarray([str(row["episode_id"]) == cluster for row in exposed])
        scores.append(x[mask].T @ (y[mask] - p[mask]))
    score_matrix = np.asarray(scores)
    correction = len(clusters) / (len(clusters) - 1) * (len(y) - 1) / (len(y) - x.shape[1])
    covariance = correction * bread @ score_matrix.T @ score_matrix @ bread
    if np.linalg.matrix_rank(covariance) < x.shape[1]:
        return {**result, "reason": "cluster covariance rank deficient"}
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    radius = float(t.ppf(0.975, len(clusters) - 1)) * standard_errors
    return {
        **result,
        "status": "estimated",
        "coefficients": beta.tolist(),
        "covariance": covariance.tolist(),
        "ci_lo": (beta - radius).tolist(),
        "ci_hi": (beta + radius).tolist(),
        "interval": "episode_cluster_sandwich_t",
    }


def _group_key(metadata: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(metadata[key] for key in GROUP_KEYS)


def _arm_summaries(episodes: Sequence[_Episode]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[_Episode]] = defaultdict(list)
    for episode in episodes:
        groups[_group_key(episode.metadata)].append(episode)
    output = []
    for key, group in sorted(groups.items()):
        n = len(group)
        observed = sum(episode.summary["observed_exfiltration"] for episode in group)
        unknown = sum(episode.summary["outcome_unknown"] for episode in group)
        low, high = wilson_interval(observed, n)
        output.append(
            {
                **dict(zip(GROUP_KEYS, key, strict=True)),
                "episodes": n,
                "statuses": dict(Counter(episode.metadata["status"] for episode in group)),
                "observed_exfiltrations": observed,
                "outcome_unknown": unknown,
                "observed_exfiltration_rate_all_attempts": observed / n,
                "observed_rate_wilson_lo": low,
                "observed_rate_wilson_hi": high,
                "missing_outcome_lower_rate": observed / n,
                "missing_outcome_upper_rate": (observed + unknown) / n,
            }
        )
    return output


def _kinetics(episodes: Sequence[_Episode]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[tuple[int, float]]] = defaultdict(list)
    totals = Counter(_group_key(episode.metadata) for episode in episodes)
    for episode in episodes:
        if episode.gt is None:
            continue
        gt = episode.gt
        state = infection_state(
            episode.events, gt, initial_infection=episode.metadata["initial_infection"]
        )
        last = (
            gt.rounds - 1
            if episode.metadata["status"] == "complete"
            else max((event.round for event in episode.events), default=-1)
        )
        for round_number in range(min(last + 1, gt.rounds)):
            count = sum(info["infected_round"] <= round_number for info in state.values())
            groups[(*_group_key(episode.metadata), round_number)].append(
                (count, count / gt.n_agents)
            )
    output = []
    for key, values in sorted(groups.items()):
        counts, prevalence = zip(*values, strict=True)
        low, high = bootstrap_ci(counts)
        prev_low, prev_high = bootstrap_ci(prevalence)
        output.append(
            {
                **dict(zip(GROUP_KEYS, key[:-1], strict=True)),
                "round": key[-1],
                "infected_mean": float(np.mean(counts)),
                "ci_lo": low,
                "ci_hi": high,
                "prevalence_mean": float(np.mean(prevalence)),
                "prevalence_ci_lo": prev_low,
                "prevalence_ci_hi": prev_high,
                "episodes_observed": len(values),
                "episodes_total": totals[key[:-1]],
            }
        )
    return output


def _comparisons(episodes: Sequence[_Episode]) -> list[dict[str, Any]]:
    baselines = {
        (episode.metadata["seed"], *[episode.metadata[key] for key in GROUP_KEYS[2:]]): episode
        for episode in episodes
        if episode.metadata["arm"] == "A1"
    }
    groups: dict[tuple[Any, ...], list[tuple[_Episode, _Episode | None]]] = defaultdict(list)
    for episode in episodes:
        if episode.metadata["arm"] != "A3":
            continue
        key = (episode.metadata["seed"], *[episode.metadata[column] for column in GROUP_KEYS[2:]])
        groups[_group_key(episode.metadata)].append((episode, baselines.get(key)))
    output: list[dict[str, Any]] = []
    for key, candidates in sorted(groups.items()):
        pairs = [
            (gate, base)
            for gate, base in candidates
            if base is not None and gate.metadata["status"] == base.metadata["status"] == "complete"
        ]
        row = {
            **dict(zip(GROUP_KEYS, key, strict=True)),
            "pairs_attempted": len(candidates),
            "pairs_complete": len(pairs),
            "pairs_unavailable": len(candidates) - len(pairs),
            "paired_seeds": [gate.metadata["seed"] for gate, _ in pairs],
        }
        if pairs:
            free = [float(base.summary["observed_exfiltration"]) for _, base in pairs]
            gated = [float(gate.summary["observed_exfiltration"]) for gate, _ in pairs]
            effect, low, high = paired_bootstrap_diff_ci(free, gated)
            utility_loss, utility_low, utility_high = paired_bootstrap_diff_ci(
                [base.summary["utility"] for _, base in pairs],
                [gate.summary["utility"] for gate, _ in pairs],
            )
            b = sum(bool(a) and not d for a, d in zip(free, gated, strict=True))
            c = sum(bool(d) and not a for a, d in zip(free, gated, strict=True))
            row.update(
                exfiltration_reduction=effect,
                effect_ci_lo=low,
                effect_ci_hi=high,
                utility_loss=utility_loss,
                utility_loss_ci_lo=utility_low,
                utility_loss_ci_hi=utility_high,
                mcnemar_b=b,
                mcnemar_c=c,
                mcnemar_p=exact_mcnemar_p(b, c),
            )
        else:
            row["status"] = "not_identifiable"
        output.append(row)
    tested = [row for row in output if "mcnemar_p" in row]
    for row, adjusted in zip(
        tested, holm_adjust([row["mcnemar_p"] for row in tested]), strict=True
    ):
        row["holm_p"] = adjusted
    return output


def _panel_b(episodes: Sequence[_Episode], comparisons: Sequence[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    missing = []
    for comparison in comparisons:
        if not comparison["pairs_complete"]:
            continue
        group = [
            episode
            for episode in episodes
            if _group_key(episode.metadata) == _group_key(comparison)
            and episode.metadata["status"] == "complete"
            and episode.metadata["seed"] in comparison["paired_seeds"]
        ]
        messages = [
            event for episode in group for event in episode.events if event.kind == "message"
        ]
        stages = [event.payload.get("gate_stage") for event in messages]
        if not stages or any(stage not in {"d1", "llm", "graph"} for stage in stages):
            missing.append(comparison["defense"])
            continue
        offspring = float(
            np.mean([episode.summary["offspring_mean_recruitment"] for episode in group])
        )
        rows.append(
            {
                **{key: comparison[key] for key in GROUP_KEYS},
                "llm_call_share": sum(stage in {"llm", "graph"} for stage in stages) / len(stages),
                "utility_loss": comparison["utility_loss"],
                "exfil_reduction": comparison["exfiltration_reduction"],
                "r0": offspring,
                "offspring_mean_recruitment": offspring,
                "offspring_mean_breach": float(
                    np.mean([episode.summary["offspring_mean_breach"] for episode in group])
                ),
            }
        )
    return {
        "status": "available" if rows else "TODO(result)",
        "rows": rows,
        "missing_gate_stage": missing,
        "r0_mapping": "offspring_mean_recruitment",
        "share_basis": "message gate_stage; model retries are not inferred",
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())


def _write_csv(path: Path, rows: Sequence[dict[str, Any]], columns: Sequence[str] = ()) -> None:
    fields = list(columns) + sorted({key for row in rows for key in row} - set(columns))
    if not fields:
        fields = ["status"]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, sort_keys=True)
                    if isinstance(value, (dict, list))
                    else value
                    for key, value in row.items()
                }
            )


def analyze(root: Path, outdir: Path, allow_mock: bool = False) -> dict[str, Any]:
    """Analyze selected final attempts; mock data require explicit opt-in and stay marked."""
    root = Path(root).resolve()
    outdir = Path(outdir).resolve()
    episodes, sources = _load(root, allow_mock)
    reported_episodes = [e for e in episodes if e.metadata["arm"] in REPORTED_ARMS]
    auxiliary_episodes = [e for e in episodes if e.metadata["arm"] not in REPORTED_ARMS]
    kinetics = _kinetics(reported_episodes)
    exposed_rows = []
    for episode in episodes:
        if episode.metadata["arm"] != "A1" or episode.gt is None:
            continue
        # H2 inference uses complete observations, with failures retained in arm summaries.
        if episode.metadata["status"] != "complete":
            continue
        for row in h2_rows(
            episode.events, episode.gt, initial_infection=episode.metadata["initial_infection"]
        ):
            if row["total_solicitations_received"] >= 1:
                exposed_rows.append(
                    {
                        **row,
                        "episode_id": episode.metadata["episode_id"],
                        "topology": episode.metadata["topology"],
                    }
                )
    comparisons = _comparisons(reported_episodes)
    panel_b = _panel_b(reported_episodes, comparisons)
    result: dict[str, Any] = {
        "schema_version": 1,
        "mock": any(episode.metadata["mock"] for episode in episodes),
        "episodes": [episode.summary for episode in episodes],
        "arms": _arm_summaries(reported_episodes),
        "auxiliary_arms": _arm_summaries(auxiliary_episodes),
        "kinetics": kinetics,
        "comparisons": comparisons,
        "sources": sources,
        "h2": {**fit_h2(exposed_rows), "population": "exposed A1 rows from complete episodes"},
        "panels": {
            "A": {"status": "TODO(result)", "reason": "offline scored messages absent"},
            "B": panel_b,
        },
        "definitions": {
            "failures": "retained in all-attempt denominator; unobserved outcomes are unknown",
            "kinetics": "failed episodes contribute only through their last observed round",
            "bootstrap_unit": "episode (paired episode for treatment effects)",
            "offspring": "action-specific children / all infected agents, including zero children",
        },
    }
    outdir.mkdir(parents=True, exist_ok=True)
    _write_json(outdir / "summary.json", result)
    _write_json(outdir / "h2.json", result["h2"])
    _write_csv(outdir / "episodes.csv", result["episodes"])
    _write_csv(outdir / "arm_summary.csv", result["arms"])
    _write_csv(outdir / "paired_comparisons.csv", comparisons)
    _write_csv(outdir / "h2_rows.csv", exposed_rows)
    _write_csv(outdir / "kinetics.csv", kinetics, KINETICS_COLUMNS)
    _write_csv(outdir / "panel_b.csv", panel_b["rows"], PANEL_B_COLUMNS)
    free_flow = [row for row in kinetics if row["arm"] == "A1"]
    # Plot only a single provider/model/defense per topology/harm to avoid joining conditions.
    series_keys = {(row["provider"], row["model"], row["defense"]) for row in free_flow}
    if free_flow and len(series_keys) == 1:
        _write_csv(outdir / "kinetics_a1.csv", free_flow, KINETICS_COLUMNS)
        plot_kinetics(outdir / "kinetics_a1.csv", outdir / "kinetics.png")
    return result
