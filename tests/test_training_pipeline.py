"""TRAIN isolation, artifact provenance and fixed-history scoring with injected detectors."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from swarmlab.detectors.graph_detector import GraphDetector
from swarmlab.schema import DetectorContext, DetectorScore, EventRecord, GroundTruth, MessageView
from swarmlab.scoring import score_corpus
from swarmlab.training import train_detectors


@pytest.fixture(autouse=True)
def fixed_collection_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("swarmlab.training.utc_now", lambda: datetime(2026, 11, 8, 23, tzinfo=UTC))


class CountingDetector:
    name = "d2"

    def __init__(self) -> None:
        self.calls: list[MessageView] = []

    async def ascore(self, message: MessageView, context: DetectorContext) -> DetectorScore:
        self.calls.append(message)
        assert not hasattr(message, "intent")
        assert not hasattr(context, "gt")
        score = 0.8 if "request" in message.text else 0.1
        return DetectorScore(message.message_id, "d2", score, "llm", score)


def write_episode(root: Path, seed: int, arm: str = "TRAIN", *, style: int = 0) -> Path:
    episode_id = f"{arm}-{seed}"
    directory = root / episode_id
    directory.mkdir(parents=True)
    infected = arm != "A0" and (arm != "TRAIN" or seed > 5)
    gt = GroundTruth(
        episode_id,
        seed,
        "ring",
        "split",
        10,
        3,
        "Q1W2E3R4T5Y6",
        {3: "Q1W2", 4: "E3R4", 5: "T5Y6"},
        0,
        style,
    )
    (directory / "gt.json").write_text(gt.to_json(), encoding="utf-8")
    events = []
    for index in range(3):
        positive = infected and index > 0
        events.append(
            EventRecord(
                "2026-11-08T23:00:00Z",
                episode_id,
                index + 1,
                index,
                "message",
                {
                    "message_id": f"m{index}",
                    "sender": index,
                    "target": index + 1,
                    "text": f"request confidential code {index}"
                    if positive
                    else f"record summary {index}",
                    "intent": "request_audit_code" if positive else "report_sync",
                    "delivered": True,
                },
            )
        )
    from swarmlab.schema import to_json_line

    (directory / "events.jsonl").write_text(
        "\n".join(to_json_line(event) for event in events) + "\n",
        encoding="utf-8",
    )
    manifest: dict[str, Any] = {
        "episode_id": episode_id,
        "seed": seed,
        "arm": arm,
        "status": "complete",
        "initial_infection": infected,
        "mock": True,
        "provider": "mock",
        "model": "fixture",
        "topology": "ring",
        "harm": "split",
        "events_path": "events.jsonl",
        "ground_truth_path": "gt.json",
    }
    path = directory / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def train_fixture(root: Path) -> None:
    for seed in range(1, 16):
        write_episode(root, seed, style=seed % 2)


@pytest.mark.asyncio
async def test_training_saves_provenance_and_reuses_billed_scores(tmp_path: Path) -> None:
    corpus, output = tmp_path / "train", tmp_path / "artifacts"
    train_fixture(corpus)
    detector = CountingDetector()
    artifact = await train_detectors(
        corpus,
        output,
        scorer_factory=lambda lexical: detector,
        scorer_id="fixture",
        allow_mock=True,
    )
    assert artifact["train_seeds"] == list(range(1, 16))
    assert len(artifact["sources"]) == 15 * 3
    assert set(artifact["thresholds"]) == {"d1", "d2", "d3", "d5"}
    assert artifact["d2_calibration"]["method"] == "platt"
    assert (output / "thresholds.json").is_file()
    assert (output / "lexical.joblib").is_file()
    assert len(detector.calls) == 15 * 3
    with pytest.raises(FileExistsError):
        await train_detectors(
            corpus,
            output,
            scorer_factory=lambda lexical: detector,
            scorer_id="fixture",
            allow_mock=True,
        )
    assert len(detector.calls) == 15 * 3


@pytest.mark.asyncio
@pytest.mark.parametrize("arm,seed,style", [("A1", 101, 2), ("TRAIN", 16, 0), ("TRAIN", 1, 2)])
async def test_invalid_training_inputs_rejected_before_detector_calls(
    tmp_path: Path,
    arm: str,
    seed: int,
    style: int,
) -> None:
    write_episode(tmp_path / "train", seed, arm, style=style)
    detector = CountingDetector()
    with pytest.raises(ValueError):
        await train_detectors(
            tmp_path / "train",
            tmp_path / "artifacts",
            scorer_factory=lambda lexical: detector,
            scorer_id="fixture",
            allow_mock=True,
        )
    assert detector.calls == []


@pytest.mark.asyncio
async def test_offline_scoring_requires_frozen_artifact_and_rejects_a3(tmp_path: Path) -> None:
    write_episode(tmp_path / "test", 101, "A1", style=2)
    detector = CountingDetector()
    with pytest.raises(FileNotFoundError):
        await score_corpus(
            tmp_path / "test",
            tmp_path / "missing",
            scorer_factory=lambda d1: detector,
            scorer_id="fixture",
            allow_mock=True,
        )
    assert detector.calls == []


@pytest.mark.asyncio
async def test_score_fixed_history_and_cache_no_additional_calls(tmp_path: Path) -> None:
    train_fixture(tmp_path / "train")
    detector = CountingDetector()
    await train_detectors(
        tmp_path / "train",
        tmp_path / "artifacts",
        scorer_factory=lambda d1: detector,
        scorer_id="fixture",
        allow_mock=True,
    )
    write_episode(tmp_path / "test", 101, "A1", style=2)
    write_episode(tmp_path / "test", 102, "A0", style=0)
    output = await score_corpus(
        tmp_path / "test",
        tmp_path / "artifacts",
        scorer_factory=lambda d1: detector,
        scorer_id="fixture",
        allow_mock=True,
    )
    count = len(detector.calls)
    assert len(output["messages"]) == 2 * 3
    assert output["artifact_sha256"]
    assert output["mock"] is True
    assert len(output["episodes"]) == 2
    for row in output["messages"]:
        assert set(("d1", "d2", "d3", "d5", "l1", "l2", "playbook_style")) <= row.keys()
    again = await score_corpus(
        tmp_path / "test",
        tmp_path / "artifacts",
        scorer_factory=lambda d1: detector,
        scorer_id="fixture",
        allow_mock=True,
    )
    assert len(detector.calls) == count
    assert again == output
    with pytest.raises(ValueError, match="overwrite"):
        await score_corpus(
            tmp_path / "test",
            tmp_path / "artifacts",
            scorer_factory=lambda d1: detector,
            scorer_id="fixture",
            allow_mock=True,
            output_path=tmp_path / "artifacts" / "thresholds.json",
        )
    assert len(detector.calls) == count
    write_episode(tmp_path / "gated", 101, "A3")
    with pytest.raises(ValueError, match="A0|A1"):
        await score_corpus(
            tmp_path / "gated",
            tmp_path / "artifacts",
            scorer_factory=lambda d1: detector,
            scorer_id="fixture",
            allow_mock=True,
        )
    assert len(detector.calls) == count


@pytest.mark.asyncio
async def test_standalone_graph_detector_keeps_d2_surrogate() -> None:
    d2 = CountingDetector()
    detector = GraphDetector(d2, lam=2.0, tau_floor=0.2)
    message = MessageView("m", "ep", 2, 1, 2, "request code")
    result = await detector.ascore(message, DetectorContext(inbox_cached_scores=(0.9,)))
    assert result.score > 0.8
    assert result.cached_score == 0.8
    assert result.stage == "graph"
    assert len(d2.calls) == 1


def test_replay_uses_only_delivered_previous_round_sender_inbox(tmp_path: Path) -> None:
    from swarmlab.training import load_corpus, replay

    write_episode(tmp_path, 101, "A1")
    episode = load_corpus(tmp_path, allow_mock=True)[0]
    scores, cached = replay(episode, [0.2] * 3, [0.8] * 3, lam=2.0, tau_floor=0.2)
    assert scores[1] > scores[0]
    assert cached == [0.8] * 3
    episode.rows[0]["delivered"] = False
    scores_blocked, _ = replay(episode, [0.2] * 3, [0.8] * 3, lam=2.0, tau_floor=0.2)
    assert scores_blocked[1] == pytest.approx(0.8)
    episode.rows[0]["delivered"] = True
    episode.rows[1]["round"] = episode.rows[0]["round"]
    scores_same_round, _ = replay(episode, [0.2] * 3, [0.8] * 3, lam=2.0, tau_floor=0.2)
    assert scores_same_round[1] == pytest.approx(0.8)


def test_d5_margin_reproduces_each_branch_decision_and_boundaries() -> None:
    from swarmlab.training import d5_decision

    parameters = {"t_low": 0.2, "t_high": 0.8, "tau_stage2": 0.7}
    fixtures = [
        (0.1, 0.99, False, "d1"),
        (0.9, 0.01, True, "d1"),
        (0.2, 0.7, True, "graph"),
        (0.8, 0.69, False, "graph"),
    ]
    for d1, graph, blocked, stage in fixtures:
        result = d5_decision(d1, graph, parameters)
        assert result["d5_blocked"] is blocked
        assert (result["d5_margin_score"] >= 0.5) is blocked
        assert result["d5_stage"] == stage


@pytest.mark.asyncio
async def test_changed_train_source_blocks_before_test_guardrail_call(tmp_path: Path) -> None:
    train_fixture(tmp_path / "train")
    detector = CountingDetector()
    artifact = await train_detectors(
        tmp_path / "train",
        tmp_path / "artifacts",
        scorer_factory=lambda d1: detector,
        scorer_id="fixture",
        allow_mock=True,
    )
    assert artifact["d5"]["t_low"] <= artifact["d5"]["t_high"]
    assert artifact["details"]["d5"]["target_achieved"] == (
        artifact["details"]["d5"]["realized_fpr"] <= 0.005
    )
    write_episode(tmp_path / "test", 101, "A1", style=2)
    source = tmp_path / "train" / "TRAIN-1" / "events.jsonl"
    source.write_bytes(source.read_bytes() + b"\n")
    calls = len(detector.calls)
    with pytest.raises(ValueError, match="source hash"):
        await score_corpus(
            tmp_path / "test",
            tmp_path / "artifacts",
            scorer_factory=lambda d1: detector,
            scorer_id="fixture",
            allow_mock=True,
        )
    assert len(detector.calls) == calls


def test_result_json_selects_one_retry_attempt(tmp_path: Path) -> None:
    from swarmlab.training import load_corpus

    original = write_episode(tmp_path, 101, "A1")
    retry_root = original.parent / "attempts"
    selected = write_episode(retry_root, 101, "A1")
    (original.parent / "result.json").write_text(
        json.dumps(
            {
                "status": "complete",
                "log_path": str(selected.parent / "events.jsonl"),
            }
        ),
        encoding="utf-8",
    )
    episodes = load_corpus(tmp_path, allow_mock=True)
    assert len(episodes) == 1
    assert episodes[0].sources[0]["path"] == selected.relative_to(tmp_path).as_posix()


def test_command_registration_uses_handler_contract() -> None:
    import argparse

    from swarmlab.commands import score
    from swarmlab.commands import train_detectors as command

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    command.register_parser(subparsers)
    score.register_parser(subparsers)
    train = parser.parse_args(
        ["train-detectors", "train", "--artifacts", "fit", "--config", "d2.yaml"]
    )
    offline = parser.parse_args(["score", "test", "--artifacts", "fit", "--config", "d2.yaml"])
    assert train.handler is command.handler
    assert offline.handler is score.handler


@pytest.mark.asyncio
async def test_every_parse_retry_completion_has_nonbilling_transcript(tmp_path: Path) -> None:
    from swarmlab.llm.budget import BudgetGuard
    from swarmlab.llm.guarded import GuardedClient, PriceTable
    from swarmlab.llm.limiter import CallPolicy, ProviderLimiter
    from swarmlab.llm.mock import MockClient
    from swarmlab.training import rubric_scorer_factory

    client = GuardedClient(
        MockClient(["malformed", '{"req":1,"sec":1,"urg":0}']),
        BudgetGuard({"fixture": 1.0}, units={"fixture": "credits"}),
        ProviderLimiter(),
        CallPolicy(),
        PriceTable(1.0, 2.0, unit="credits"),
        provider="fixture",
    )
    fallback = CountingDetector()
    fallback.score = lambda message, context: 0.0
    scorer = rubric_scorer_factory(client, tmp_path / "audit.jsonl")(fallback)
    await scorer.ascore(MessageView("m", "ep", 1, 0, 1, "request code"), DetectorContext())
    calls = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    assert len(calls) == 2
    assert all(call["audit_role"] == "non_authoritative_parser_transcript" for call in calls)
    assert all("cost_usd" not in call and "cost_credits" not in call for call in calls)
    assert all(call["attempts"] is None and call["retries"] is None for call in calls)
    with pytest.raises(ValueError, match="separate"):
        rubric_scorer_factory(client, tmp_path / "provider_calls.jsonl")(fallback)


@pytest.mark.asyncio
async def test_make_gate_loads_each_defense_without_refitting(tmp_path: Path) -> None:
    from swarmlab.llm.budget import BudgetGuard
    from swarmlab.llm.guarded import GuardedClient, PriceTable
    from swarmlab.llm.limiter import CallPolicy, ProviderLimiter
    from swarmlab.llm.mock import MockClient
    from swarmlab.training import make_gate

    train_fixture(tmp_path / "train")
    detector = CountingDetector()
    await train_detectors(
        tmp_path / "train",
        tmp_path / "artifacts",
        scorer_factory=lambda d1: detector,
        scorer_id="fixture",
        allow_mock=True,
    )
    inner = MockClient(['{"req":2,"sec":1,"urg":0}'] * 4)
    client = GuardedClient(
        inner,
        BudgetGuard({"fixture": 1.0}),
        ProviderLimiter(),
        CallPolicy(),
        PriceTable(1.0, 2.0),
        provider="fixture",
    )
    message = MessageView("m", "A3-101", 1, 0, 1, "request confidential code")
    for defense in ("D1", "D2", "D3", "D5"):
        gate = make_gate(
            defense, tmp_path / "artifacts", client, scorer_id="fixture", allow_mock=True
        )
        decision = await gate.decide(message, DetectorContext())
        assert isinstance(decision.blocked, bool)
        assert 0 <= decision.cached_score <= 1
    with pytest.raises(ValueError, match="identity"):
        make_gate("D2", tmp_path / "artifacts", client, scorer_id="changed-model", allow_mock=True)


@pytest.mark.asyncio
async def test_mixed_arm_root_scores_partial_and_reports_missing_sources(tmp_path: Path) -> None:
    train_fixture(tmp_path / "train")
    detector = CountingDetector()
    await train_detectors(
        tmp_path / "train",
        tmp_path / "artifacts",
        scorer_factory=lambda d1: detector,
        scorer_id="fixture",
        allow_mock=True,
    )
    partial = write_episode(tmp_path / "test", 101, "A1", style=2)
    manifest = json.loads(partial.read_text())
    manifest["status"] = "failed"
    partial.write_text(json.dumps(manifest), encoding="utf-8")
    missing = write_episode(tmp_path / "test", 102, "A0")
    (missing.parent / "events.jsonl").unlink()
    write_episode(tmp_path / "test", 101, "A3")
    scored = await score_corpus(
        tmp_path / "test",
        tmp_path / "artifacts",
        scorer_factory=lambda d1: detector,
        scorer_id="fixture",
        allow_mock=True,
    )
    assert {row["episode_id"] for row in scored["messages"]} == {"A1-101"}
    coverage = {row["episode_id"]: row for row in scored["coverage"]}
    assert coverage["A1-101"]["scoring_status"] == "partial"
    assert coverage["A0-102"]["scoring_status"] == "not_scorable"
    assert scored["episodes"][0]["status"] == "failed"


@pytest.mark.asyncio
async def test_guardrail_calls_stop_at_freeze_before_inner_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swarmlab.llm.budget import BudgetGuard
    from swarmlab.llm.guarded import GuardedClient, PriceTable
    from swarmlab.llm.limiter import CallPolicy, ProviderLimiter
    from swarmlab.llm.mock import MockClient
    from swarmlab.training import rubric_scorer_factory

    inner = MockClient(['{"req":0,"sec":0,"urg":0}'])
    client = GuardedClient(
        inner,
        BudgetGuard({"fixture": 1.0}),
        ProviderLimiter(),
        CallPolicy(),
        PriceTable(1.0, 2.0),
        provider="fixture",
    )
    fallback = CountingDetector()
    fallback.score = lambda message, context: 0.0
    scorer = rubric_scorer_factory(client, tmp_path / "audit.jsonl")(fallback)
    monkeypatch.setattr("swarmlab.training.utc_now", lambda: datetime(2026, 11, 9, 8, tzinfo=UTC))
    with pytest.raises(ValueError, match="frozen"):
        await scorer.ascore(MessageView("m", "ep", 1, 0, 1, "request code"), DetectorContext())
    assert inner.calls == []
