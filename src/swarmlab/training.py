"""Fit TRAIN-only detectors and persist thresholds with source provenance."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy.special import expit
from sklearn.linear_model import LogisticRegression

from swarmlab.detectors.graph import graph_score
from swarmlab.detectors.graph_detector import GraphDetector
from swarmlab.detectors.guardrail import RUBRIC_SYSTEM_PROMPT, GuardrailDetector
from swarmlab.detectors.layered import AsyncDetector, LayeredFilter, ThresholdGate
from swarmlab.detectors.lexical import LexicalDetector
from swarmlab.detectors.thresholds import compute_thresholds, select_negatives
from swarmlab.llm.guarded import GuardedClient
from swarmlab.metrics.events import read_events
from swarmlab.metrics.extract import message_rows
from swarmlab.metrics.stats import cusum_episode_score, logit
from swarmlab.schema import DetectorContext, DetectorScore, GroundTruth, LLMResult, MessageView

ScorerFactory = Callable[[LexicalDetector], AsyncDetector]
DETECTORS = ("d1", "d2", "d3", "d5")


def utc_now() -> datetime:
    return datetime.now(UTC)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, data: Mapping[str, Any]) -> None:
    """Replace a JSON artifact atomically, with strict JSON and LF bytes."""
    payload = (json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@dataclass
class CorpusEpisode:
    metadata: dict[str, Any]
    gt: GroundTruth
    rows: list[dict[str, Any]]
    sources: list[dict[str, str]]


def load_corpus(
    root: Path,
    *,
    allow_mock: bool = False,
    allowed_arms: set[str] | None = None,
    allow_partial: bool = False,
    coverage: list[dict[str, Any]] | None = None,
) -> list[CorpusEpisode]:
    """Load selected final attempts, rejecting ambiguous duplicates and escaped paths."""
    root = root.resolve()
    selected: list[Path] = []
    result_dirs: list[Path] = []
    selectors: dict[Path, Path] = {}
    for result_path in sorted(root.rglob("result.json")):
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if allowed_arms is not None and result.get("arm") not in allowed_arms and "arm" in result:
            result_dirs.append(result_path.parent)
            continue
        if not result.get("log_path") and allow_partial and coverage is not None:
            if allowed_arms is not None and result.get("arm") not in allowed_arms:
                raise ValueError("Missing selected log requires explicit arm metadata")
            coverage.append(
                {
                    "episode_id": result["episode_id"],
                    "arm": result["arm"],
                    "status": result.get("status"),
                    "scoring_status": "not_scorable",
                    "reason": "selected result has no log_path",
                    "observed_messages": None,
                    "sources": [
                        {
                            "path": result_path.relative_to(root).as_posix(),
                            "sha256": sha256(result_path),
                        }
                    ],
                }
            )
            result_dirs.append(result_path.parent)
            continue
        if (result.get("status") != "complete" and not allow_partial) or not result.get("log_path"):
            raise ValueError("Scoring requires complete selected episodes")
        log = Path(result["log_path"])
        log = (result_path.parent / log).resolve() if not log.is_absolute() else log.resolve()
        if not log.is_relative_to(root):
            raise ValueError("Selected source escapes corpus root")
        manifest = log.parent / "manifest.json"
        selected.append(manifest)
        selectors[manifest] = result_path
        result_dirs.append(result_path.parent)
    for path in sorted(root.rglob("manifest.json")):
        if not any(path.is_relative_to(directory) for directory in result_dirs):
            if "attempts" in path.relative_to(root).parts:
                raise ValueError("Retry attempts require an explicit result.json selector")
            selected.append(path)
    episodes: list[CorpusEpisode] = []
    identities: set[str] = set()
    for path in selected:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        if allowed_arms is not None and metadata.get("arm") not in allowed_arms:
            continue
        for key in ("episode_id", "seed", "arm", "status", "mock", "initial_infection"):
            if key not in metadata:
                raise ValueError(f"Missing episode metadata: {key}")
        if metadata["status"] != "complete" and not allow_partial:
            raise ValueError("Training and scoring require complete episodes")
        if type(metadata["mock"]) is not bool or type(metadata["initial_infection"]) is not bool:
            raise ValueError("mock and initial_infection must be booleans")
        if metadata["mock"] and not allow_mock:
            raise ValueError("Mock corpus requires allow_mock=True")
        if metadata["episode_id"] in identities:
            raise ValueError("Duplicate episode_id in corpus")
        identities.add(metadata["episode_id"])
        try:
            source_paths = [path]
            if path in selectors:
                source_paths.append(selectors[path])
            data_paths = []
            for key, default in (("events_path", "events.jsonl"), ("ground_truth_path", "gt.json")):
                candidate = (path.parent / metadata.get(key, default)).resolve()
                if not candidate.is_relative_to(path.parent.resolve()):
                    raise ValueError("Source path escapes selected episode")
                data_paths.append(candidate)
            log_path, truth_path = data_paths
            gt = GroundTruth.from_json(truth_path.read_text(encoding="utf-8"))
            if (
                gt.episode_id != metadata["episode_id"]
                or gt.world_seed != metadata["seed"]
                or type(metadata["seed"]) is not int
            ):
                raise ValueError("Manifest and ground truth identity mismatch")
            events = read_events(log_path)
            if any(event.episode_id != gt.episode_id for event in events):
                raise ValueError("Event identity differs from ground truth")
            config_path = path.parent / "config.yaml"
            if metadata.get("config_sha256"):
                if sha256(config_path) != metadata["config_sha256"]:
                    raise ValueError("Configuration hash differs from manifest")
                source_paths.append(config_path)
            if not metadata["mock"]:
                calls = [event for event in events if event.kind == "llm_call"]
                if not calls or any(
                    not event.payload.get("response_id")
                    or event.payload.get("provider") != metadata.get("provider")
                    for event in calls
                ):
                    raise ValueError("Real corpus needs provider response evidence")
            rows = message_rows(events, gt, initial_infection=metadata["initial_infection"])
            message_ids = [row["message_id"] for row in rows]
            if not all(message_ids) or len(set(message_ids)) != len(message_ids):
                raise ValueError("Message ids must be nonempty and unique within an episode")
            rows.sort(key=lambda row: row["round"])
            sources = [
                {"path": item.relative_to(root).as_posix(), "sha256": sha256(item)}
                for item in [*source_paths, *data_paths]
            ]
            episodes.append(CorpusEpisode(metadata, gt, rows, sources))
            if coverage is not None:
                coverage.append(
                    {
                        "episode_id": gt.episode_id,
                        "arm": metadata["arm"],
                        "status": metadata["status"],
                        "observed_messages": len(rows),
                        "scoring_status": "complete"
                        if metadata["status"] == "complete"
                        else "partial",
                    }
                )
        except (OSError, ValueError, KeyError, TypeError) as error:
            if not allow_partial or coverage is None:
                raise
            coverage.append(
                {
                    "episode_id": metadata["episode_id"],
                    "arm": metadata["arm"],
                    "status": metadata["status"],
                    "scoring_status": "not_scorable",
                    "reason": "selected source missing, unreadable or inconsistent: "
                    + type(error).__name__,
                    "observed_messages": None,
                    "sources": [
                        {"path": source.relative_to(root).as_posix(), "sha256": sha256(source)}
                        for source in [path, *data_paths]
                        if source.is_file()
                    ],
                }
            )
    if not episodes and not coverage:
        raise ValueError("No selected corpus episodes for allowed arms (A0/A1 for offline scoring)")
    if episodes and len({episode.metadata["mock"] for episode in episodes}) != 1:
        raise ValueError("Mock and real episodes must not be mixed")
    return episodes


def message_view(episode: CorpusEpisode, row: Mapping[str, Any]) -> MessageView:
    return MessageView(
        str(row["message_id"]),
        episode.gt.episode_id,
        int(row["round"]),
        int(row["sender"]),
        row["target"],
        str(row["text"]),
    )


class _AuditClient:
    """Record parser-visible completions; guarded runtime owns the provider billing audit."""

    def __init__(self, client: GuardedClient, path: Path) -> None:
        if path.name == "provider_calls.jsonl":
            raise ValueError("Parser transcript must use a separate audit destination")
        self.client, self.path = client, path
        self._check_destination()

    def _check_destination(self) -> None:
        if self.path.is_file():
            with self.path.open("rb") as handle:
                first = handle.readline()
            if (
                first
                and json.loads(first).get("audit_role") != "non_authoritative_parser_transcript"
            ):
                raise ValueError("Parser transcript cannot share an authoritative audit file")

    async def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int = 256,
        logprobs: bool = False,
    ) -> LLMResult:
        if utc_now() >= datetime(2026, 11, 9, 8, tzinfo=UTC):
            raise ValueError("Guardrail model calls are frozen after 2026-11-09 05:00 ART")
        self._check_destination()
        result = await self.client.complete(
            messages, temperature=temperature, max_tokens=max_tokens, logprobs=logprobs
        )
        record = {
            "audit_role": "non_authoritative_parser_transcript",
            "provider": result.provider,
            "model": result.model,
            "response_id": result.response_id,
            "timestamp_utc": result.timestamp_utc,
            "text": result.text,
            "request_sha256": hashlib.sha256(
                json.dumps(list(messages), sort_keys=True).encode()
            ).hexdigest(),
            "retries": None,
            "attempts": None,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._check_destination()
        with self.path.open("ab") as handle:
            handle.write((json.dumps(record, allow_nan=False) + "\n").encode())
            handle.flush()
        return result


def rubric_scorer_factory(client: GuardedClient, audit_path: Path) -> ScorerFactory:
    if not isinstance(client, GuardedClient):
        raise TypeError("Production guardrail requires GuardedClient")
    return lambda lexical: GuardrailDetector(
        _AuditClient(client, audit_path),
        mode="rubric",
        fallback=lexical,
        max_output_tokens=600,
    )


async def raw_scores(
    episodes: Sequence[CorpusEpisode],
    scorer_factory: Callable[[], AsyncDetector],
    *,
    cache_dir: Path,
    scorer_id: str,
) -> dict[str, list[float]]:
    if not scorer_id.strip():
        raise ValueError("scorer_id must identify model and scoring configuration")
    result = {}
    scorer: AsyncDetector | None = None
    for episode in episodes:
        key = hashlib.sha256(
            json.dumps(
                {"sources": episode.sources, "scorer_id": scorer_id}, sort_keys=True
            ).encode()
        ).hexdigest()
        cache_path = cache_dir / f"{key}.json"
        cache_dir.mkdir(parents=True, exist_ok=True)
        lock_path = cache_path.with_suffix(".lock")
        with lock_path.open("xb"):
            pass
        try:
            cache: dict[str, Any] = {
                "scorer_id": scorer_id,
                "sources": episode.sources,
                "scores": {},
            }
            if cache_path.exists():
                cache = json.loads(cache_path.read_text(encoding="utf-8"))
                if cache["scorer_id"] != scorer_id or cache["sources"] != episode.sources:
                    raise ValueError("Cached score provenance mismatch")
            values = []
            for row in episode.rows:
                identity = row["message_id"]
                if identity not in cache["scores"]:
                    if scorer is None:
                        scorer = scorer_factory()
                    score = (
                        await scorer.ascore(message_view(episode, row), DetectorContext())
                    ).score
                    if not math.isfinite(score) or not 0 <= score <= 1:
                        raise ValueError("D2 score must be finite and in [0,1]")
                    cache["scores"][identity] = score
                    atomic_json(cache_path, cache)
                score = float(cache["scores"][identity])
                if not math.isfinite(score) or not 0 <= score <= 1:
                    raise ValueError("Cached D2 score must be finite and in [0,1]")
                values.append(score)
            result[episode.gt.episode_id] = values
        finally:
            lock_path.unlink()
    return result


def calibrated_scores(raw: Sequence[float], calibration: Mapping[str, Any]) -> list[float]:
    return [
        float(expit(calibration["coefficient"] * logit(value) + calibration["intercept"]))
        for value in raw
    ]


class CalibratedGuardrail:
    name = "d2"

    def __init__(self, inner: AsyncDetector, calibration: Mapping[str, Any]) -> None:
        self.inner, self.calibration = inner, dict(calibration)

    async def ascore(self, message: MessageView, context: DetectorContext) -> DetectorScore:
        raw = await self.inner.ascore(message, context)
        score = calibrated_scores([raw.score], self.calibration)[0]
        return DetectorScore(message.message_id, "d2", score, "llm", score)


def scorer_identity(config: Mapping[str, Any]) -> str:
    """Fingerprint model and scoring behavior independently of billing or file location."""
    if config.get("mode", "rubric") != "rubric" or config.get("max_tokens", 600) != 600:
        raise ValueError("Frozen guardrail requires rubric mode and max_tokens=600")
    settings = {
        "provider": config["provider"],
        "model": config["model"],
        "mode": "rubric",
        "max_tokens": 600,
        "temperature": 0.0,
        "tie_weight": 0.05,
        "prompt_sha256": hashlib.sha256(RUBRIC_SYSTEM_PROMPT.encode()).hexdigest(),
    }
    return hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()


def load_detector_bundle(artifact_dir: Path) -> tuple[dict[str, Any], LexicalDetector]:
    artifact = json.loads((artifact_dir / "thresholds.json").read_text(encoding="utf-8"))
    if sha256(artifact_dir / "lexical.joblib") != artifact["lexical_sha256"]:
        raise ValueError("Lexical model hash differs from frozen artifact")
    for source in artifact["sources"]:
        source_path = artifact_dir / artifact["train_root"] / source["path"]
        if sha256(source_path) != source["sha256"]:
            raise ValueError("Frozen TRAIN source hash differs")
    return artifact, LexicalDetector.load(artifact_dir / "lexical.joblib")


def make_gate(
    defense: str,
    artifact_dir: Path,
    client: GuardedClient | None = None,
    *,
    scorer_id: str | None = None,
    audit_path: Path | None = None,
    allow_mock: bool = False,
) -> ThresholdGate | LayeredFilter:
    artifact, lexical = load_detector_bundle(artifact_dir)
    if artifact["mock"] and not allow_mock:
        raise ValueError("Mock-trained gate requires allow_mock=True")
    name = defense.lower()
    if name == "d1":
        return ThresholdGate(lexical, artifact["thresholds"]["d1"])
    if name not in {"d2", "d3", "d5"}:
        raise ValueError("Unknown defense")
    if client is None or scorer_id != artifact["scorer_id"]:
        raise ValueError("Guarded D2 client and matching frozen scorer identity required")
    base = rubric_scorer_factory(client, audit_path or artifact_dir / "online_parser_calls.jsonl")(
        lexical
    )
    d2 = CalibratedGuardrail(base, artifact["d2_calibration"])
    graph = artifact["graph"]
    if name == "d2":
        return ThresholdGate(d2, artifact["thresholds"]["d2"])
    if name == "d3":
        return ThresholdGate(
            GraphDetector(d2, lam=graph["lam"], tau_floor=graph["tau_floor"]),
            artifact["thresholds"]["d3"],
        )
    return LayeredFilter(
        lexical,
        d2,
        t_low=artifact["d5"]["t_low"],
        t_high=artifact["d5"]["t_high"],
        tau_stage2=artifact["d5"]["tau_stage2"],
        lam=graph["lam"],
        tau_floor=graph["tau_floor"],
    )


def replay(
    episode: CorpusEpisode,
    d1: Sequence[float],
    d2: Sequence[float],
    *,
    lam: float,
    tau_floor: float,
    t_low: float | None = None,
    t_high: float | None = None,
) -> tuple[list[float], list[float]]:
    """Use only delivered messages addressed to the sender in the previous round."""
    output: list[float] = []
    cached: list[float] = []
    for index, row in enumerate(episode.rows):
        inbox = [
            cached[j]
            for j in range(index)
            if episode.rows[j]["round"] == row["round"] - 1
            and episode.rows[j]["target"] == row["sender"]
            and episode.rows[j]["delivered"]
        ]
        fast = (
            t_low is not None and t_high is not None and (d1[index] < t_low or d1[index] > t_high)
        )
        cached.append(d1[index] if fast else d2[index])
        output.append(
            d1[index] if fast else graph_score(d2[index], inbox, lam=lam, tau_floor=tau_floor)
        )
    return output, cached


def threshold_detail(
    scores: Sequence[float],
    negatives: Sequence[bool],
    target: float,
) -> dict[str, Any]:
    negative = [score for score, flag in zip(scores, negatives, strict=True) if flag]
    threshold = compute_thresholds("fixture", negative, target)
    realized = float(np.mean(np.asarray(negative) >= threshold.smoothed))
    return {
        "raw": threshold.raw if math.isfinite(threshold.raw) else None,
        "smoothed": threshold.smoothed,
        "target_fpr": target,
        "realized_fpr": realized,
        "n_negatives": len(negative),
        "target_achieved": realized <= target,
    }


def episode_alarms(
    scores: Sequence[float],
    threshold: float,
    cusum_threshold: float,
) -> dict[str, Any]:
    crossings = sum(score >= threshold for score in scores)
    cusum = cusum_episode_score([logit(score) for score in scores], logit(threshold))
    return {
        "crossings": crossings,
        "alarm": crossings >= 2,
        "cusum": cusum,
        "cusum_alarm": cusum > cusum_threshold,
    }


def d5_decision(s1: float, graph: float, parameters: Mapping[str, Any]) -> dict[str, Any]:
    """Return the branch decision and a threshold-relative margin, not a probability."""
    if s1 < parameters["t_low"]:
        score, threshold, stage, blocked = s1, parameters["t_low"], "d1", False
    elif s1 > parameters["t_high"]:
        score, threshold, stage, blocked = s1, parameters["t_high"], "d1", True
    else:
        score, threshold, stage = graph, parameters["tau_stage2"], "graph"
        blocked = graph >= threshold
    if threshold > 1:
        margin = 0.0
    else:
        margin = float(expit(logit(score) - logit(threshold)))
    return {
        "d5_blocked": blocked,
        "d5_margin_score": margin,
        "d5_stage_score": score,
        "d5_stage_threshold": threshold,
        "d5_stage": stage,
    }


async def _train_detectors(
    root: Path,
    artifact_dir: Path,
    *,
    scorer_factory: ScorerFactory,
    scorer_id: str,
    allow_mock: bool = False,
    lam_grid: Sequence[float] = (0.0, 0.5, 1.0, 2.0),
    tau_floor_grid: Sequence[float] = (0.1, 0.25, 0.5),
    seed: int = 0,
) -> dict[str, Any]:
    if (artifact_dir / "thresholds.json").exists():
        raise FileExistsError("Frozen thresholds already exist; use a new artifact directory")
    episodes = load_corpus(root, allow_mock=allow_mock)
    for episode in episodes:
        if (
            episode.metadata["arm"] != "TRAIN"
            or type(episode.gt.world_seed) is not int
            or not 1 <= episode.gt.world_seed <= 15
            or episode.gt.playbook_style not in (0, 1)
        ):
            raise ValueError("Only TRAIN seeds 1..15 and playbooks 0/1 may fit detectors")
    if sorted(ep.gt.world_seed for ep in episodes) != list(range(1, 16)):
        raise ValueError("TRAIN requires each preregistered seed 1..15 exactly once")
    if sum(not ep.metadata["initial_infection"] for ep in episodes) != 5:
        raise ValueError("TRAIN requires five clean and ten infected episodes")
    if not lam_grid or not tau_floor_grid or any(not math.isfinite(x) or x < 0 for x in lam_grid):
        raise ValueError("lambda grid must be nonempty, finite and nonnegative")
    if any(not math.isfinite(x) or not 0 <= x <= 1 for x in tau_floor_grid):
        raise ValueError("tau_floor grid must be finite and in [0,1]")
    rows = [row for ep in episodes for row in ep.rows]
    labels = [int(row["l1"] or row["l2"]) for row in rows]
    texts = [row["text"] for row in rows]
    groups = [ep.gt.episode_id for ep in episodes for row in ep.rows]
    lexical = LexicalDetector(seed=seed).fit(texts, labels, episode_ids=groups)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_temp = artifact_dir / "lexical.joblib.tmp"
    lexical.save(model_temp)
    os.replace(model_temp, artifact_dir / "lexical.joblib")
    model_hash = sha256(artifact_dir / "lexical.joblib")
    cache_identity = scorer_id + ":" + model_hash
    raw = await raw_scores(
        episodes,
        lambda: scorer_factory(lexical),
        cache_dir=artifact_dir / "cache",
        scorer_id=cache_identity,
    )
    raw_flat = [value for ep in episodes for value in raw[ep.gt.episode_id]]
    platt = LogisticRegression(C=1e6, random_state=seed, max_iter=1000)
    platt.fit(np.asarray([logit(value) for value in raw_flat]).reshape(-1, 1), labels)
    calibration = {
        "method": "platt",
        "coefficient": float(platt.coef_[0, 0]),
        "intercept": float(platt.intercept_[0]),
    }
    d1_by_ep = {
        ep.gt.episode_id: lexical.scores([row["text"] for row in ep.rows]) for ep in episodes
    }
    d2_by_ep = {
        ep.gt.episode_id: calibrated_scores(raw[ep.gt.episode_id], calibration) for ep in episodes
    }
    negatives_set = {id(row) for row in select_negatives(rows)}
    negatives = [id(row) in negatives_set for row in rows]

    def flatten(values: Mapping[str, Sequence[float]]) -> list[float]:
        return [value for ep in episodes for value in values[ep.gt.episode_id]]

    details = {
        "d1": threshold_detail(flatten(d1_by_ep), negatives, 0.005),
        "d2": threshold_detail(flatten(d2_by_ep), negatives, 0.005),
    }
    best: tuple[tuple[float, ...], float, float, dict[str, list[float]], dict[str, Any]] | None = (
        None
    )
    for lam in lam_grid:
        for floor in tau_floor_grid:
            candidate = {
                ep.gt.episode_id: replay(
                    ep,
                    d1_by_ep[ep.gt.episode_id],
                    d2_by_ep[ep.gt.episode_id],
                    lam=lam,
                    tau_floor=floor,
                )[0]
                for ep in episodes
            }
            values = flatten(candidate)
            detail = threshold_detail(values, negatives, 0.005)
            tpr = float(
                np.mean(
                    [
                        value >= detail["smoothed"]
                        for value, label in zip(values, labels, strict=True)
                        if label
                    ]
                )
            )
            rank = (
                (1.0, tpr, -detail["realized_fpr"])
                if detail["target_achieved"]
                else (0.0, -detail["realized_fpr"], tpr)
            )
            if best is None or rank > best[0]:
                best = (rank, lam, floor, candidate, detail)
    assert best is not None
    _, lam, floor, d3_by_ep, details["d3"] = best
    positive_d1 = sorted(
        value for value, label in zip(flatten(d1_by_ep), labels, strict=True) if label
    )
    t_low_candidate = positive_d1[math.floor(0.01 * len(positive_d1))]
    t_high = threshold_detail(flatten(d1_by_ep), negatives, 0.001)["smoothed"]
    t_low = min(t_low_candidate, t_high)
    d5_by_ep = {
        ep.gt.episode_id: replay(
            ep,
            d1_by_ep[ep.gt.episode_id],
            d2_by_ep[ep.gt.episode_id],
            lam=lam,
            tau_floor=floor,
            t_low=t_low,
            t_high=t_high,
        )[0]
        for ep in episodes
    }
    d1_flat, d5_flat = flatten(d1_by_ep), flatten(d5_by_ep)
    forced = sum(flag and value > t_high for flag, value in zip(negatives, d1_flat, strict=True))
    gray_negatives = [
        score
        for score, s1, flag in zip(d5_flat, d1_flat, negatives, strict=True)
        if flag and t_low <= s1 <= t_high
    ]
    allowance = max(0.0, 0.005 * sum(negatives) - forced)
    if not gray_negatives or allowance <= 0:
        stage2 = math.nextafter(max(gray_negatives, default=1.0), math.inf)
    else:
        stage2 = compute_thresholds(
            "d5", gray_negatives, min(0.999, allowance / len(gray_negatives))
        ).smoothed
    d5_blocked = [
        s1 > t_high or t_low <= s1 <= t_high and score >= stage2
        for score, s1 in zip(d5_flat, d1_flat, strict=True)
    ]
    fpr_d5 = sum(block and flag for block, flag in zip(d5_blocked, negatives, strict=True)) / sum(
        negatives
    )
    details["d5"] = {
        "target_fpr": 0.005,
        "realized_fpr": fpr_d5,
        "target_achieved": fpr_d5 <= 0.005,
        "forced_fast_blocks": forced,
        "n_negatives": sum(negatives),
        "smoothed": 0.5,
        "raw": None,
    }
    d5_parameters = {
        "t_low": t_low,
        "t_high": t_high,
        "tau_stage2": stage2,
        "t_low_candidate": t_low_candidate,
        "t_low_clipped": t_low_candidate > t_high,
        "clipping_reason": "preserve ordered gray zone and positive retention",
        "score_definition": "sigmoid(logit(stage_score)-logit(stage_threshold))",
        "score_limitation": "threshold-relative margin, not calibrated probability",
    }
    d5_margin = {
        ep.gt.episode_id: [
            d5_decision(s1, graph, d5_parameters)["d5_margin_score"]
            for s1, graph in zip(
                d1_by_ep[ep.gt.episode_id], d5_by_ep[ep.gt.episode_id], strict=True
            )
        ]
        for ep in episodes
    }
    score_maps = {"d1": d1_by_ep, "d2": d2_by_ep, "d3": d3_by_ep, "d5": d5_margin}
    thresholds = {name: detail["smoothed"] for name, detail in details.items()}
    cusum_thresholds = {}
    for name in DETECTORS:
        clean = [
            episode_alarms(score_maps[name][ep.gt.episode_id], thresholds[name], math.inf)["cusum"]
            for ep in episodes
            if not ep.metadata["initial_infection"]
        ]
        cusum_thresholds[name] = float(np.quantile(clean, 0.95))
    artifact = {
        "version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "seed": seed,
        "train_seeds": sorted(ep.gt.world_seed for ep in episodes),
        "sources": [source for ep in episodes for source in ep.sources],
        "train_root": os.path.relpath(root.resolve(), artifact_dir.resolve()),
        "mock": any(ep.metadata["mock"] for ep in episodes),
        "scorer_id": scorer_id,
        "cache_identity": cache_identity,
        "audit_role": "guardrail parser transcript; authoritative provider billing audit separate",
        "lexical_sha256": model_hash,
        "d2_calibration": calibration,
        "thresholds": thresholds,
        "details": details,
        "cusum_thresholds": cusum_thresholds,
        "graph": {
            "lam": lam,
            "tau_floor": floor,
            "lam_grid": list(lam_grid),
            "tau_floor_grid": list(tau_floor_grid),
            "selection_rule": "maximize TPR among realized-FPR-feasible candidates; otherwise "
            "minimize realized FPR then maximize TPR; ties use grid order",
        },
        "d5": d5_parameters,
    }
    atomic_json(artifact_dir / "thresholds.json", artifact)
    return artifact


async def train_detectors(
    root: Path,
    artifact_dir: Path,
    *,
    scorer_factory: ScorerFactory,
    scorer_id: str,
    allow_mock: bool = False,
    lam_grid: Sequence[float] = (0.0, 0.5, 1.0, 2.0),
    tau_floor_grid: Sequence[float] = (0.1, 0.25, 0.5),
    seed: int = 0,
) -> dict[str, Any]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    lock = artifact_dir / "training.lock"
    # Acquire before writing model files or making billable scoring calls.
    with lock.open("xb"):
        pass
    try:
        return await _train_detectors(
            root,
            artifact_dir,
            scorer_factory=scorer_factory,
            scorer_id=scorer_id,
            allow_mock=allow_mock,
            lam_grid=lam_grid,
            tau_floor_grid=tau_floor_grid,
            seed=seed,
        )
    finally:
        lock.unlink()
