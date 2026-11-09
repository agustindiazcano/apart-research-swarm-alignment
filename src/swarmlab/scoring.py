"""Replay offline A0/A1 history using frozen TRAIN artifacts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from swarmlab.training import (
    DETECTORS,
    ScorerFactory,
    atomic_json,
    calibrated_scores,
    d5_decision,
    episode_alarms,
    load_corpus,
    load_detector_bundle,
    raw_scores,
    replay,
    sha256,
)


async def score_corpus(
    root: Path,
    artifact_dir: Path,
    *,
    scorer_factory: ScorerFactory,
    scorer_id: str,
    allow_mock: bool = False,
    output_path: Path | None = None,
) -> dict[str, Any]:
    artifact_path = artifact_dir / "thresholds.json"
    artifact, lexical = load_detector_bundle(artifact_dir)
    if artifact["scorer_id"] != scorer_id:
        raise ValueError("Scorer differs from frozen TRAIN artifact")
    coverage: list[dict[str, Any]] = []
    episodes = load_corpus(
        root,
        allow_mock=allow_mock,
        allowed_arms={"A0", "A1"},
        allow_partial=True,
        coverage=coverage,
    )
    destination = output_path or root / "scores.json"
    protected = {artifact_path.resolve(), (artifact_dir / "lexical.joblib").resolve()}
    protected.update((root / source["path"]).resolve() for ep in episodes for source in ep.sources)
    protected.update(
        (artifact_dir / artifact["train_root"] / source["path"]).resolve()
        for source in artifact["sources"]
    )
    if destination.resolve() in protected:
        raise ValueError("Scoring output must not overwrite sources or frozen artifacts")
    if any(
        not 101 <= ep.gt.world_seed <= 115 or ep.gt.playbook_style not in (0, 1, 2)
        for ep in episodes
    ):
        raise ValueError("Offline scoring requires TEST seeds 101..115 and declared playbooks")
    if episodes and artifact["mock"] != any(ep.metadata["mock"] for ep in episodes):
        raise ValueError("Mock and real training/scoring artifacts must not be mixed")
    raw = (
        await raw_scores(
            episodes,
            lambda: scorer_factory(lexical),
            cache_dir=artifact_dir / "cache",
            scorer_id=artifact["cache_identity"],
        )
        if episodes
        else {}
    )
    messages, episode_rows = [], []
    for episode in episodes:
        identity = episode.gt.episode_id
        d1 = lexical.scores([row["text"] for row in episode.rows])
        d2 = calibrated_scores(raw[identity], artifact["d2_calibration"])
        d3, d3_cached = replay(
            episode, d1, d2, lam=artifact["graph"]["lam"], tau_floor=artifact["graph"]["tau_floor"]
        )
        d5, d5_cached = replay(
            episode,
            d1,
            d2,
            lam=artifact["graph"]["lam"],
            tau_floor=artifact["graph"]["tau_floor"],
            t_low=artifact["d5"]["t_low"],
            t_high=artifact["d5"]["t_high"],
        )
        decisions = [
            d5_decision(s1, graph, artifact["d5"]) for s1, graph in zip(d1, d5, strict=True)
        ]
        maps = {
            "d1": d1,
            "d2": d2,
            "d3": d3,
            "d5": [decision["d5_margin_score"] for decision in decisions],
        }
        alarms = {
            name: episode_alarms(
                maps[name], artifact["thresholds"][name], artifact["cusum_thresholds"][name]
            )
            for name in DETECTORS
        }
        alarms["d5"]["crossings"] = sum(decision["d5_blocked"] for decision in decisions)
        alarms["d5"]["alarm"] = alarms["d5"]["crossings"] >= 2
        episode_rows.append(
            {
                "episode_id": identity,
                "arm": episode.metadata["arm"],
                "status": episode.metadata["status"],
                **alarms,
            }
        )
        for index, row in enumerate(episode.rows):
            # Labels are joined to completed scores; they are never detector inputs.
            messages.append(
                {
                    **row,
                    "episode_id": identity,
                    "playbook_style": episode.gt.playbook_style,
                    **decisions[index],
                    **{name: scores[index] for name, scores in maps.items()},
                    "d3_cached": d3_cached[index],
                    "d5_cached": d5_cached[index],
                    "d5_reaches_llm": artifact["d5"]["t_low"]
                    <= d1[index]
                    <= artifact["d5"]["t_high"],
                }
            )
    sources = {source["path"]: source for ep in episodes for source in ep.sources}
    for item in coverage:
        sources.update({source["path"]: source for source in item.get("sources", [])})
    output = {
        "version": 1,
        "messages": messages,
        "episodes": episode_rows,
        "thresholds": artifact["thresholds"],
        "mock": artifact["mock"],
        "sources": sorted(sources.values(), key=lambda source: source["path"]),
        "artifact_sha256": sha256(artifact_path),
        "artifact_path": os.path.relpath(
            artifact_path.resolve(), (output_path or root / "scores.json").parent.resolve()
        ),
        "arms": ["A0", "A1"],
        "selection_rule": "offline fixed-history arms only; intervention arms are excluded",
        "coverage": coverage,
    }
    atomic_json(destination, output)
    return output
