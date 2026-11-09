"""CLI fixtures run locally with mocked providers and synthetic records."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from swarmlab import cli
from swarmlab import execution as execution_module
from swarmlab.execution import RuntimeFactory, execute_episode
from swarmlab.llm.guarded import GuardedClient
from swarmlab.llm.mock import MockClient
from swarmlab.metrics.events import read_events
from swarmlab.metrics.extract import episode_summary
from swarmlab.schema import EpisodeSpec, GroundTruth


def fixture_config() -> dict[str, object]:
    return {"provider": "mock", "model": "mock-cli", "rounds": 3, "initial_infection": False}


def test_run_episode_cli_persists_provenance_and_summary(tmp_path: Path) -> None:
    config_path = tmp_path / "fixture.yaml"
    config_path.write_text(yaml.safe_dump(fixture_config()), encoding="utf-8")
    outdir = tmp_path / "out"
    assert (
        cli.main(
            [
                "run-episode",
                "--config",
                str(config_path),
                "--world-seed",
                "901",
                "--topology",
                "ring",
                "--arm",
                "A0",
                "--outdir",
                str(outdir),
            ]
        )
        == 0
    )
    directory = outdir / "A0-ring-split-none-s901"
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["status"] == "complete"
    assert manifest["mock"] is True
    assert manifest["initial_infection"] is False
    assert (
        manifest["config_sha256"]
        == hashlib.sha256((directory / "config.yaml").read_bytes()).hexdigest()
    )
    assert manifest["git_commit"]
    events = read_events(directory / "events.jsonl")
    summary = json.loads((directory / "episode_summary.json").read_text())
    assert summary["n_infected"] == 0
    assert summary["utility"] == 1.0
    assert all(
        event.payload["response_id"].startswith("mock-")
        for event in events
        if event.kind == "llm_call"
    )


def test_existing_complete_episode_is_not_overwritten(tmp_path: Path) -> None:
    spec = EpisodeSpec("fixture-episode", 901, "ring", "split", "A0", None)
    config = fixture_config()
    factory = RuntimeFactory(config)
    first = asyncio.run(execute_episode(spec, config, tmp_path, factory=factory))
    assert first.status == "complete"
    path = tmp_path / spec.episode_id / (first.log_path or "")
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        asyncio.run(execute_episode(spec, config, tmp_path, factory=factory))
    assert path.read_bytes() == original


def test_batch_resumes_without_new_calls_or_log_changes(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump(fixture_config()), encoding="utf-8")
    matrix = tmp_path / "matrix.yaml"
    matrix.write_text(
        yaml.safe_dump(
            {
                "arm": "A0",
                "topologies": ["ring"],
                "harms": ["split"],
                "defenses": [None],
                "seeds": [901, 902],
            }
        ),
        encoding="utf-8",
    )
    argv = [
        "batch",
        "--config",
        str(config),
        "--matrix",
        str(matrix),
        "--outdir",
        str(tmp_path / "out"),
        "--resume",
    ]
    assert cli.main(argv) == 0
    logs = sorted((tmp_path / "out").rglob("events.jsonl"))
    before = {path: path.read_bytes() for path in logs}
    assert len(logs) == 2
    assert cli.main(argv) == 0
    assert {path: path.read_bytes() for path in logs} == before


@pytest.mark.parametrize(
    "missing", ["cap", "input_per_m", "output_per_m", "unit", "source", "verified"]
)
def test_real_factory_blocks_incomplete_billing_before_adapter_creation(missing: str) -> None:
    billing: dict[str, object] = {
        "cap": 1.0,
        "input_per_m": 1.0,
        "output_per_m": 2.0,
        "unit": "credits",
        "source": "fixture source",
        "verified": True,
    }
    del billing[missing]
    config = {"provider": "adaption", "model": "fixture-model", "billing": billing}
    with pytest.raises(ValueError, match="billing"):
        RuntimeFactory(config, environ={})


def test_credit_price_cannot_be_used_with_usd_unit() -> None:
    config = {
        "provider": "adaption",
        "model": "fixture-model",
        "billing": {
            "cap": 500,
            "input_per_m": 1,
            "output_per_m": 2,
            "unit": "usd",
            "source": "fixture source",
            "verified": True,
        },
    }
    with pytest.raises(ValueError, match="credits"):
        RuntimeFactory(config, environ={})


def real_fixture_config() -> dict[str, object]:
    return {
        "provider": "adaption",
        "model": "fixture-model",
        "rounds": 1,
        "billing": {
            "cap": 1,
            "input_per_m": 1,
            "output_per_m": 2,
            "unit": "credits",
            "source": "fixture source",
            "verified": True,
        },
    }


def test_factory_wraps_real_adapter_and_keeps_provider_limits_shared() -> None:
    inner = MockClient(['{"action":"noop"}'])
    factory = RuntimeFactory(real_fixture_config(), adapter_factory=lambda *args: inner)
    assert isinstance(factory.create_client(), GuardedClient)
    assert factory.create_client() is factory.create_client()
    assert factory.guard is not None
    assert factory.guard.unit("adaption") == "credits"


def test_real_execution_is_blocked_after_freeze_before_provider_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[bool] = []
    monkeypatch.setattr(execution_module, "utc_now", lambda: datetime(2026, 11, 9, 8, tzinfo=UTC))
    factory = RuntimeFactory(
        real_fixture_config(), adapter_factory=lambda *args: called.append(True)
    )
    spec = EpisodeSpec("freeze-fixture", 901, "ring", "split", "A0", None)
    with pytest.raises(ValueError, match="frozen"):
        asyncio.run(execute_episode(spec, factory.config, tmp_path, factory=factory))
    assert called == []
    assert not (tmp_path / spec.episode_id).exists()


def test_credit_episode_summary_is_computed_from_committed_format_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(execution_module, "utc_now", lambda: datetime(2026, 11, 8, tzinfo=UTC))
    config = real_fixture_config()
    inner = MockClient(lambda messages: '{"action":"noop"}', provider="adaption")
    factory = RuntimeFactory(config, adapter_factory=lambda *args: inner)
    spec = EpisodeSpec("credit-fixture", 901, "ring", "split", "A0", None)
    result = asyncio.run(execute_episode(spec, config, tmp_path, factory=factory))
    assert result.status == "complete"
    directory = (tmp_path / spec.episode_id / (result.log_path or "")).parent
    events = read_events(directory / "events.jsonl")
    truth = GroundTruth.from_json((directory / "gt.json").read_text())
    summary = json.loads((directory / "episode_summary.json").read_text())
    assert summary == episode_summary(events, truth, initial_infection=False)
    assert summary["cost_usd"] is None
    assert summary["cost_credits"] > 0


def test_failed_attempt_reruns_same_world_in_new_directory(tmp_path: Path) -> None:
    spec = EpisodeSpec("retry-fixture", 901, "ring", "split", "A0", None)
    config = fixture_config()
    factory = RuntimeFactory(config)

    class FailedFactory(RuntimeFactory):
        def create_client(self) -> object:
            raise RuntimeError("fixture construction failure")

    first = asyncio.run(execute_episode(spec, config, tmp_path, factory=FailedFactory(config)))
    assert first.status == "failed"
    path = tmp_path / spec.episode_id / (first.log_path or "")
    before = path.read_bytes()
    second = asyncio.run(execute_episode(spec, config, tmp_path, factory=factory))
    assert second.status == "complete"
    assert Path(second.log_path or "").parent.name == "attempt-002"
    assert path.read_bytes() == before
    assert (path.parent / "gt.json").read_bytes() == (
        tmp_path / spec.episode_id / Path(second.log_path or "").parent / "gt.json"
    ).read_bytes()


def test_prereg_cli_requires_inputs_and_preserves_existing_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from swarmlab import prereg

    for name in [
        "docs/EXPERIMENT_DESIGN.md",
        "experiments/configs/pilot.yaml",
        "src/swarmlab/metrics/stats.py",
        "src/swarmlab/swarm/prompts.py",
        *[f"experiments/payloads/playbook_{style}.txt" for style in range(3)],
    ]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture input", encoding="utf-8")
    monkeypatch.setattr(prereg, "current_git_commit", lambda root: "fixture-commit")
    assert cli.main(["prereg", "--root", str(tmp_path)]) == 0
    path = tmp_path / "artifacts/preregistration_manifest.json"
    original = path.read_bytes()
    with pytest.raises(SystemExit):
        cli.main(["prereg", "--root", str(tmp_path)])
    assert path.read_bytes() == original


def test_resume_rejects_changed_configuration(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config = fixture_config()
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    matrix_path = tmp_path / "matrix.yaml"
    matrix_path.write_text(
        yaml.safe_dump(
            {
                "arm": "A0",
                "topologies": ["ring"],
                "harms": ["split"],
                "defenses": [None],
                "seeds": [901],
            }
        ),
        encoding="utf-8",
    )
    args = [
        "batch",
        "--config",
        str(config_path),
        "--matrix",
        str(matrix_path),
        "--outdir",
        str(tmp_path / "out"),
        "--resume",
    ]
    assert cli.main(args) == 0
    config["rounds"] = 2
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(SystemExit):
        cli.main(args)


def test_batch_records_attempt_history_for_failed_episodes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from swarmlab.commands import batch

    class FailingFactory(RuntimeFactory):
        def create_client(self) -> object:
            raise RuntimeError("fixture client construction failure")

    monkeypatch.setattr(batch, "RuntimeFactory", FailingFactory)
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump(fixture_config()), encoding="utf-8")
    matrix = tmp_path / "matrix.yaml"
    matrix.write_text(
        yaml.safe_dump(
            {
                "arm": "A0",
                "topologies": ["ring"],
                "harms": ["split"],
                "defenses": [None],
                "seeds": [901],
            }
        ),
        encoding="utf-8",
    )
    outdir = tmp_path / "out"
    assert (
        cli.main(
            ["batch", "--config", str(config), "--matrix", str(matrix), "--outdir", str(outdir)]
        )
        == 1
    )
    result = json.loads((outdir / "A0-ring-split-none-s901/result.json").read_text())
    assert result["status"] == "failed"
    assert result["attempts"] == len(result["attempt_history"]) == 3
    assert all(attempt["status"] == "failed" for attempt in result["attempt_history"])
    truths = [
        outdir / "A0-ring-split-none-s901" / Path(attempt["manifest_path"]).parent / "gt.json"
        for attempt in result["attempt_history"]
    ]
    assert len({truth.read_bytes() for truth in truths}) == 1


def test_budget_stop_records_unstarted_episodes_in_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from swarmlab.commands import batch
    from swarmlab.llm.budget import BudgetExceeded

    class ExhaustedFactory(RuntimeFactory):
        def create_client(self) -> object:
            raise BudgetExceeded("fixture budget exhausted")

    monkeypatch.setattr(batch, "RuntimeFactory", ExhaustedFactory)
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump(fixture_config()), encoding="utf-8")
    matrix = tmp_path / "matrix.yaml"
    matrix.write_text(
        yaml.safe_dump(
            {
                "arm": "A0",
                "topologies": ["ring"],
                "harms": ["split"],
                "defenses": [None],
                "seeds": [901, 902],
            }
        ),
        encoding="utf-8",
    )
    outdir = tmp_path / "out"
    assert (
        cli.main(
            [
                "batch",
                "--config",
                str(config),
                "--matrix",
                str(matrix),
                "--outdir",
                str(outdir),
                "--max-concurrency",
                "1",
            ]
        )
        == 1
    )
    results = [json.loads(path.read_text()) for path in sorted(outdir.glob("*/result.json"))]
    assert len(results) == 2
    assert all(result["status"] == "budget_abort" for result in results)
    assert results[1]["log_path"] is None
    assert results[1]["attempt_history"] == []


def test_cancelled_episode_manifest_is_failed(tmp_path: Path) -> None:
    from collections.abc import Mapping, Sequence

    from swarmlab.schema import LLMResult

    class WaitingClient:
        def __init__(self) -> None:
            self.started = asyncio.Event()

        async def complete(
            self,
            messages: Sequence[Mapping[str, str]],
            *,
            temperature: float | None = None,
            max_tokens: int = 256,
            logprobs: bool = False,
        ) -> LLMResult:
            self.started.set()
            await asyncio.Event().wait()
            raise AssertionError("fixture call unexpectedly released")

    async def scenario() -> None:
        factory = RuntimeFactory(fixture_config())
        client = WaitingClient()
        factory._client = client
        spec = EpisodeSpec("cancel-fixture", 901, "ring", "split", "A0", None)
        task = asyncio.create_task(execute_episode(spec, factory.config, tmp_path, factory=factory))
        await client.started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    manifest = json.loads((tmp_path / "cancel-fixture/manifest.json").read_text())
    assert manifest["status"] == "failed"
    assert manifest["finished_at"]


def test_result_and_attempt_selectors_are_relative_for_reproduction(tmp_path: Path) -> None:
    config = tmp_path / "fixture.yaml"
    config.write_text(yaml.safe_dump(fixture_config()), encoding="utf-8")
    outdir = tmp_path / "out"
    assert (
        cli.main(
            [
                "run-episode",
                "--config",
                str(config),
                "--world-seed",
                "901",
                "--topology",
                "ring",
                "--arm",
                "A0",
                "--outdir",
                str(outdir),
            ]
        )
        == 0
    )
    result_path = outdir / "A0-ring-split-none-s901/result.json"
    result = json.loads(result_path.read_text())
    assert not Path(result["log_path"]).is_absolute()
    assert (result_path.parent / result["log_path"]).is_file()
    for attempt in result["attempt_history"]:
        assert not Path(attempt["manifest_path"]).is_absolute()
        assert (result_path.parent / attempt["manifest_path"]).is_file()


def test_single_episode_uses_configured_arm_and_harm(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({**fixture_config(), "arm": "TRAIN", "harm": "solo"}))
    assert (
        cli.main(
            [
                "run-episode",
                "--config",
                str(path),
                "--world-seed",
                "1",
                "--topology",
                "ring",
                "--outdir",
                str(tmp_path / "out"),
            ]
        )
        == 0
    )
    result_path = tmp_path / "out/TRAIN-ring-solo-none-s1/result.json"
    assert json.loads(result_path.read_text())["arm"] == "TRAIN"


def test_configured_defense_is_not_silently_omitted(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({**fixture_config(), "defense": "D1"}))
    with pytest.raises(SystemExit):
        cli.main(
            [
                "run-episode",
                "--config",
                str(path),
                "--world-seed",
                "901",
                "--topology",
                "ring",
                "--outdir",
                str(tmp_path / "out"),
            ]
        )
