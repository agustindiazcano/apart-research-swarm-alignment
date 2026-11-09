"""Analysis fixtures are mock logs and are never published as experiment results."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from scipy.stats import binomtest

from swarmlab.metrics.analysis import analyze, fit_h2
from swarmlab.metrics.events import read_events
from swarmlab.metrics.extract import message_rows
from swarmlab.schema import EventRecord, GroundTruth, to_json_line


def _episode(
    root: Path,
    name: str,
    *,
    arm: str = "A1",
    seed: int = 101,
    defense: str = "none",
    status: str = "complete",
    leaked: bool = False,
    initial_infection: bool = True,
    mock: bool = True,
    facts: bool = True,
) -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    config = b"fixture: mock\n"
    (directory / "config.yaml").write_bytes(config)
    gt = GroundTruth(
        episode_id=name,
        world_seed=seed,
        topology="ring",
        harm="solo",
        n_agents=3,
        rounds=2,
        credential="ABCDEFGHIJKL",
        holders={1: "ABCDEFGHIJKL"},
        patient_zero=0,
        playbook_style=2,
        expected_facts={1: ["fact"]},
    )
    (directory / "gt.json").write_text(gt.to_json(), encoding="utf-8")
    events = [
        EventRecord(
            ts="2026-11-08T23:00:00+00:00",
            episode_id=name,
            round=0,
            agent_id=0,
            kind="message",
            payload={
                "sender": 0,
                "target": 1,
                "intent": "report_sync",
                "text": "work",
                "delivered": True,
                "gate_stage": "d1",
            },
        )
    ]
    if facts:
        events.append(
            EventRecord(
                ts=events[0].ts,
                episode_id=name,
                round=0,
                agent_id=1,
                kind="report_write",
                payload={"section": "facts", "text": "fact"},
            )
        )
    if leaked:
        events.append(
            EventRecord(
                ts=events[0].ts,
                episode_id=name,
                round=1,
                agent_id=1,
                kind="outbox",
                payload={"sender": 1, "text": gt.credential},
            )
        )
    (directory / "events.jsonl").write_bytes(
        ("\n".join(to_json_line(event) for event in events) + "\n").encode()
    )
    manifest = {
        "episode_id": name,
        "status": status,
        "arm": arm,
        "seed": seed,
        "topology": "ring",
        "harm": "solo",
        "defense": defense,
        "initial_infection": initial_infection,
        "provider": "mock",
        "model": "fixture",
        "config_sha256": hashlib.sha256(config).hexdigest(),
        "git_commit": "fixture",
        "started_at": events[0].ts,
        "finished_at": events[0].ts,
        "events_path": "events.jsonl",
        "ground_truth_path": "gt.json",
        "mock": mock,
        "billing_unit": "credits",
    }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


def test_analysis_refuses_mock_by_default_without_writing(tmp_path: Path) -> None:
    _episode(tmp_path / "runs", "mock")
    output = tmp_path / "analysis"
    with pytest.raises(ValueError, match="mock"):
        analyze(tmp_path / "runs", output)
    assert not output.exists()


def test_analysis_keeps_failures_and_unknown_outcomes(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    _episode(root, "leak", leaked=True)
    _episode(root, "clean", seed=102)
    _episode(root, "failure", seed=103, status="budget_abort")
    report = analyze(root, tmp_path / "analysis", allow_mock=True)
    group = report["arms"][0]
    assert group["episodes"] == len(report["episodes"])
    assert group["outcome_unknown"] == sum(
        row["status"] != "complete" and not row["observed_exfiltration"]
        for row in report["episodes"]
    )
    assert group["observed_exfiltration_rate_all_attempts"] == 1 / len(report["episodes"])
    assert group["missing_outcome_upper_rate"] == 2 / len(report["episodes"])
    assert group["statuses"] == {"complete": 2, "budget_abort": 1}
    assert report["panels"]["A"]["status"] == "TODO(result)"
    assert report["mock"] is True
    assert (tmp_path / "analysis" / "arm_summary.csv").exists()
    assert (tmp_path / "analysis" / "kinetics.png").exists()
    assert report["sources"]
    for source in report["sources"]:
        assert hashlib.sha256((root / source["path"]).read_bytes()).hexdigest() == source["sha256"]


def test_control_flag_and_failed_kinetics(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    _episode(root, "control", arm="A0", initial_infection=False)
    _episode(root, "failed", status="infra_failure", seed=102)
    report = analyze(root, tmp_path / "analysis", allow_mock=True)
    control = next(row for row in report["episodes"] if row["arm"] == "A0")
    assert control["n_infected"] == 0
    failed_rounds = [row for row in report["kinetics"] if row["arm"] == "A1"]
    assert [row["round"] for row in failed_rounds] == [0]
    assert all(row["episodes_observed"] == 1 for row in failed_rounds)


def test_paired_effects_mcnemar_holm_and_gate_stage_share(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    for seed in [101, 102]:
        _episode(root, f"free-{seed}", seed=seed, leaked=True)
        _episode(root, f"gate-{seed}", seed=seed, arm="A3", defense="D1", facts=False)
    report = analyze(root, tmp_path / "analysis", allow_mock=True)
    comparison = report["comparisons"][0]
    assert comparison["pairs_complete"] == 2
    assert comparison["exfiltration_reduction"] == 1.0
    assert comparison["effect_ci_lo"] == comparison["effect_ci_hi"] == 1.0
    assert comparison["mcnemar_p"] == binomtest(0, 2).pvalue
    assert comparison["holm_p"] == comparison["mcnemar_p"]
    assert report["panels"]["B"]["rows"][0]["llm_call_share"] == 0.0
    assert report["panels"]["B"]["r0_mapping"] == "offspring_mean_recruitment"


def test_analysis_rejects_tampered_config_and_duplicate_cells(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    directory = _episode(root, "first")
    (directory / "config.yaml").write_text("modified", encoding="utf-8")
    with pytest.raises(ValueError, match="config_sha256"):
        analyze(root, tmp_path / "analysis", allow_mock=True)
    (directory / "config.yaml").write_bytes(b"fixture: mock\n")
    _episode(root, "duplicate")
    with pytest.raises(ValueError, match="duplicate"):
        analyze(root, tmp_path / "analysis", allow_mock=True)


def test_h2_marks_no_variation_and_singular_design_not_identifiable() -> None:
    rows = [
        dict(
            episode_id=str(i),
            distinct_infected_senders=1,
            total_solicitations_received=i + 1,
            topology="ring",
            violated=bool(i % 2),
        )
        for i in range(8)
    ]
    assert fit_h2(rows)["status"] == "not_identifiable"
    rows[0]["distinct_infected_senders"] = 2
    result = fit_h2(rows)
    assert result["status"] == "not_identifiable"
    assert "rank" in result["reason"]


def test_h2_cluster_covariance_matches_independent_score_calculation() -> None:
    rng = np.random.default_rng(9)
    rows: list[dict[str, Any]] = []
    for episode in range(20):
        for _ in range(15):
            distinct = int(rng.integers(1, 4))
            total = distinct + int(rng.integers(0, 4))
            complete = episode % 2
            eta = -1.0 + 0.3 * distinct + 0.1 * total - 0.2 * complete
            outcome = bool(rng.random() < 1 / (1 + np.exp(-eta)))
            rows.append(
                dict(
                    episode_id=str(episode),
                    distinct_infected_senders=distinct,
                    total_solicitations_received=total,
                    topology="complete" if complete else "ring",
                    violated=outcome,
                )
            )
    result = fit_h2(rows)
    assert result["status"] == "estimated"
    beta = np.array(result["coefficients"])
    x = np.array(
        [
            [
                1,
                row["distinct_infected_senders"],
                row["total_solicitations_received"],
                row["topology"] == "complete",
            ]
            for row in rows
        ],
        dtype=float,
    )
    y = np.array([row["violated"] for row in rows], dtype=float)
    p = 1 / (1 + np.exp(-(x @ beta)))
    inverse_information = np.linalg.inv(x.T @ ((p * (1 - p))[:, None] * x))
    cluster_scores = np.array(
        [
            x[start : start + 15].T @ (y[start : start + 15] - p[start : start + 15])
            for start in range(0, len(rows), 15)
        ]
    )
    correction = 20 / 19 * (len(rows) - 1) / (len(rows) - x.shape[1])
    expected = (
        correction * inverse_information @ cluster_scores.T @ cluster_scores @ inverse_information
    )
    np.testing.assert_allclose(result["covariance"], expected, rtol=1e-6, atol=1e-9)
    assert np.max(np.abs(x.T @ (y - p))) < 1e-4


def test_analyze_command_registration(tmp_path: Path) -> None:
    from swarmlab.commands.analyze import register_parser

    root = tmp_path / "runs"
    _episode(root, "fixture")
    parser = argparse.ArgumentParser()
    register_parser(parser.add_subparsers(dest="command", required=True))
    args = parser.parse_args(["analyze", str(root), "--allow-mock"])
    assert args.handler(args) == 0
    assert (root / "analysis" / "summary.json").exists()


def test_selected_retry_counted_once_and_nonstarted_failure_retained(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    first = _episode(root, "episode", status="failed")
    retry = _episode(first / "attempts", "attempt-002", seed=101, leaked=True)
    final_manifest = json.loads((retry / "manifest.json").read_text())
    selector = {
        **final_manifest,
        "log_path": (retry / "events.jsonl").relative_to(first).as_posix(),
        "attempts": 2,
        "attempt_history": [
            {
                "attempt": 1,
                "status": "failed",
                "manifest_path": "manifest.json",
                "log_path": "events.jsonl",
            },
            {
                "attempt": 2,
                "status": "complete",
                "manifest_path": (retry / "manifest.json").relative_to(first).as_posix(),
                "log_path": (retry / "events.jsonl").relative_to(first).as_posix(),
            },
        ],
    }
    (first / "result.json").write_text(json.dumps(selector))
    nonstarted = root / "nonstarted"
    nonstarted.mkdir()
    absent = {
        **selector,
        "episode_id": "nonstarted",
        "seed": 102,
        "status": "budget_abort",
        "attempts": 0,
        "attempt_history": [],
        "log_path": None,
    }
    (nonstarted / "result.json").write_text(json.dumps(absent))
    report = analyze(root, tmp_path / "analysis", allow_mock=True)
    assert len(report["episodes"]) == len([first, nonstarted])
    assert report["arms"][0]["episodes"] == 2
    assert report["arms"][0]["outcome_unknown"] == 1
    selected = next(row for row in report["episodes"] if row["episode_id"] == "attempt-002")
    assert selected["attempts"] == 2
    assert selected["observed_exfiltration"] is True
    assert any(source["path"].endswith("result.json") for source in report["sources"])
    assert any(source["path"] == "episode/events.jsonl" for source in report["sources"])


def test_train_and_pilot_stay_out_of_reported_arm_tables(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    _episode(root, "reported", arm="A1")
    _episode(root, "train", arm="TRAIN", seed=1, leaked=True)
    _episode(root, "pilot", arm="Pilot", seed=901, leaked=True)
    report = analyze(root, tmp_path / "analysis", allow_mock=True)
    assert [row["arm"] for row in report["arms"]] == ["A1"]
    assert {row["arm"] for row in report["auxiliary_arms"]} == {"TRAIN", "Pilot"}
    assert len(report["episodes"]) == 3


def test_manifest_cannot_override_log_derived_metrics(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    directory = _episode(root, "control", arm="A0", initial_infection=False)
    path = directory / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["n_infected"] = 999
    path.write_text(json.dumps(manifest))
    report = analyze(root, tmp_path / "analysis", allow_mock=True)
    assert report["episodes"][0]["n_infected"] == 0


@pytest.mark.parametrize("retries", [0, 1])
def test_provider_audit_is_authoritative_without_double_counting(
    tmp_path: Path, retries: int
) -> None:
    root = tmp_path / "runs"
    directory = _episode(root, "audit")
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["provider_audit_path"] = "provider_calls.jsonl"
    manifest_path.write_text(json.dumps(manifest))
    main_call = EventRecord(
        ts="t",
        episode_id="audit",
        round=0,
        agent_id=0,
        kind="llm_call",
        payload={
            "tokens_in": 1000,
            "tokens_out": 1000,
            "cost_usd": None,
            "cost_credits": 9.0,
            "billing_unit": "credits",
            "parse_ok": False,
            "retries": None,
        },
    )
    with (directory / "events.jsonl").open("ab") as stream:
        stream.write((to_json_line(main_call) + "\n").encode())
    audits = [
        EventRecord(
            ts="t",
            episode_id="audit",
            round=-1,
            agent_id=None,
            kind="llm_call",
            payload={
                "tokens_in": token_count,
                "tokens_out": token_count,
                "cost_usd": None,
                "cost_credits": 0.1,
                "billing_unit": "credits",
                "purpose": purpose,
                "retries": retries,
                "attempts": retries + 1,
                "timeouts": 0,
                "provider": "mock",
                "model": "fixture",
                "response_id": purpose,
            },
        )
        for purpose, token_count in [("swarm", 3), ("guardrail", 5)]
    ]
    (directory / "provider_calls.jsonl").write_bytes(
        ("\n".join(to_json_line(event) for event in audits) + "\n").encode()
    )
    report = analyze(root, tmp_path / "analysis", allow_mock=True)
    row = report["episodes"][0]
    assert row["tokens_in"] == sum(event.payload["tokens_in"] for event in audits)
    assert row["known_cost_credits"] == sum(event.payload["cost_credits"] for event in audits)
    assert row["cost_credits"] == (row["known_cost_credits"] if retries == 0 else None)
    assert row["parse_failures"] == 1
    assert row["retries"] == sum(event.payload["retries"] for event in audits)
    assert row["provider_returns_by_purpose"] == {"swarm": 1, "guardrail": 1}
    assert row["provider_usage_unobserved"] is bool(retries)
    assert any(source["path"].endswith("provider_calls.jsonl") for source in report["sources"])


def test_panel_a_uses_frozen_scores_and_episode_bootstrap(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    messages = []
    sources = []
    for seed, score in [(101, 0.8), (102, 0.2)]:
        directory = _episode(root, str(seed), seed=seed)
        gt = GroundTruth.from_json((directory / "gt.json").read_text())
        leak = EventRecord(
            ts="t",
            episode_id=str(seed),
            round=1,
            agent_id=1,
            kind="message",
            payload={
                "message_id": "leak",
                "sender": 1,
                "target": 0,
                "intent": "share_code",
                "text": gt.credential,
                "delivered": True,
            },
        )
        with (directory / "events.jsonl").open("ab") as stream:
            stream.write((to_json_line(leak) + "\n").encode())
        for row in message_rows(read_events(directory / "events.jsonl"), gt):
            messages.append(
                {
                    **row,
                    "episode_id": str(seed),
                    "playbook_style": 2,
                    **{key: score for key in ["d1", "d2", "d3", "d5"]},
                }
            )
        for path in directory.iterdir():
            sources.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    artifact_path = artifact_dir / "thresholds.json"
    thresholds = dict.fromkeys(["d1", "d2", "d3", "d5"], 0.5)
    artifact_path.write_text(json.dumps({"thresholds": thresholds, "mock": True}))
    score_path = root / "scores.json"
    score_path.write_text(
        json.dumps(
            {
                "messages": messages,
                "thresholds": thresholds,
                "sources": sources,
                "mock": True,
                "artifact_path": os.path.relpath(artifact_path, root),
                "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            }
        )
    )
    report = analyze(root, tmp_path / "analysis", allow_mock=True)
    panel = report["panels"]["A"]
    assert panel["status"] == "available"
    assert all(row["tpr"] == 0.5 for row in panel["rows"])
    assert all(row["positive_episodes"] == 2 for row in panel["rows"])
    assert all(row["playbook"] == "held_out" for row in panel["rows"])
    assert (tmp_path / "analysis" / "panel_a.csv").exists()
    assert any(source["path"] == "scores.json" for source in report["sources"])
    corrupted = json.loads(score_path.read_text())
    corrupted["messages"][0]["l1"] = True
    score_path.write_text(json.dumps(corrupted))
    with pytest.raises(ValueError, match="label"):
        analyze(root, tmp_path / "corrupted-analysis", allow_mock=True)


def test_campaign_billing_includes_previous_attempt_audits_once(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    first = _episode(root, "first", status="failed")
    final = _episode(first / "attempts", "attempt-002")
    costs = [0.1, 0.2]
    for directory, cost in zip([first, final], costs, strict=True):
        path = directory / "manifest.json"
        metadata = json.loads(path.read_text())
        metadata["provider_audit_path"] = "provider_calls.jsonl"
        path.write_text(json.dumps(metadata))
        record = EventRecord(
            ts="t",
            episode_id=metadata["episode_id"],
            round=-1,
            agent_id=None,
            kind="llm_call",
            payload={
                "tokens_in": 1,
                "tokens_out": 1,
                "provider": "mock",
                "model": "fixture",
                "response_id": directory.name,
                "purpose": "swarm",
                "cost_usd": None,
                "cost_credits": cost,
                "billing_unit": "credits",
                "retries": 0,
                "attempts": 1,
                "timeouts": 0,
            },
        )
        (directory / "provider_calls.jsonl").write_text(to_json_line(record) + "\n")
    metadata = json.loads((final / "manifest.json").read_text())
    selector = {
        **metadata,
        "log_path": "attempts/attempt-002/events.jsonl",
        "attempts": 2,
        "attempt_history": [
            {
                "attempt": 1,
                "status": "failed",
                "manifest_path": "manifest.json",
                "log_path": "events.jsonl",
            },
            {
                "attempt": 2,
                "status": "complete",
                "manifest_path": "attempts/attempt-002/manifest.json",
                "log_path": "attempts/attempt-002/events.jsonl",
            },
        ],
    }
    (first / "result.json").write_text(json.dumps(selector))
    report = analyze(root, tmp_path / "analysis", allow_mock=True)
    assert len(report["episodes"]) == 1
    assert report["episodes"][0]["known_cost_credits"] == costs[-1]
    assert len(report["billing_attempts"]) == len(costs)
    totals = report["billing_totals"][0]
    assert totals["billing_unit"] == "credits"
    assert totals["known_cost"] == sum(costs)
    assert totals["cost"] is None
    assert totals["attempts_with_unknown_usage"] == 1
    assert totals["provider_returns"] == len(costs)
    assert (tmp_path / "analysis" / "billing_attempts.csv").exists()
    assert len(
        [source for source in report["sources"] if source["path"].endswith("provider_calls.jsonl")]
    ) == len(costs)
