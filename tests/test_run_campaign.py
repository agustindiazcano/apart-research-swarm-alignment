"""Unit tests for the experimental campaign orchestrator."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_campaign import (
    CAMPAIGN_STEPS,
    InsufficientBudgetError,
    build_step_args,
    build_step_command,
    check_budget_headroom,
    load_env_file,
    main,
    parse_args,
    run_campaign,
)


def test_campaign_step_ordering() -> None:
    expected_steps = (
        "train_clean_ring",
        "train_clean_complete",
        "train_infected_ring",
        "train_infected_complete",
        "train_detectors",
        "a0_ring",
        "a0_complete",
        "a1_free_flow",
        "a2_score",
        "a3_gating",
        "a3c_gate_cost",
        "analyze",
    )
    assert CAMPAIGN_STEPS == expected_steps


def test_build_step_args_matrix_and_commands(tmp_path: Path) -> None:
    config = tmp_path / "custom_config.yaml"
    outdir = tmp_path / "output"
    concurrency = 4

    # 1. train_clean_ring
    args_tcr = build_step_args(
        "train_clean_ring",
        config=config,
        outdir=outdir,
        max_concurrency=concurrency,
    )
    assert args_tcr == [
        "batch",
        "--config",
        str(config),
        "--matrix",
        "experiments/configs/matrices/train_clean_ring.yaml",
        "--outdir",
        str(outdir / "train"),
        "--resume",
        "--max-concurrency",
        str(concurrency),
    ]

    # 5. train_detectors
    args_td = build_step_args(
        "train_detectors",
        config=config,
        outdir=outdir,
        max_concurrency=concurrency,
    )
    assert args_td == [
        "train-detectors",
        str(outdir / "train"),
        "--artifacts",
        str(outdir / "detectors"),
        "--config",
        str(config),
    ]

    # 6. a0_ring
    args_a0 = build_step_args(
        "a0_ring",
        config=config,
        outdir=outdir,
        max_concurrency=concurrency,
    )
    assert args_a0 == [
        "batch",
        "--config",
        str(config),
        "--matrix",
        "experiments/configs/matrices/control_ring.yaml",
        "--outdir",
        str(outdir / "campaign"),
        "--resume",
        "--max-concurrency",
        str(concurrency),
    ]

    # 9. a2_score
    args_score = build_step_args(
        "a2_score",
        config=config,
        outdir=outdir,
        max_concurrency=concurrency,
    )
    assert args_score == [
        "score",
        str(outdir / "campaign"),
        "--artifacts",
        str(outdir / "detectors"),
        "--config",
        str(config),
        "--output",
        str(outdir / "campaign" / "scores.json"),
    ]

    # 12. analyze
    args_ana = build_step_args(
        "analyze",
        config=config,
        outdir=outdir,
        max_concurrency=concurrency,
    )
    assert args_ana == [
        "analyze",
        str(outdir / "campaign"),
        "--outdir",
        str(outdir / "campaign" / "analysis"),
    ]


def test_build_step_command_includes_python_and_module(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    outdir = tmp_path / "out"
    cmd = build_step_command(
        "train_clean_ring",
        config=config,
        outdir=outdir,
        max_concurrency=2,
    )
    assert cmd[:3] == [sys.executable, "-m", "swarmlab.cli"]
    assert cmd[3] == "batch"


def test_load_env_file_loads_variables_without_leaks(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    env_file = tmp_path / ".env.test"
    secret_key = "MUSE_API_KEY"
    secret_val = "secret_value_xyz_12345"
    other_key = "TEST_PORT"
    other_val = "8080"
    env_content = f"""
    # Comment line
    {secret_key}="{secret_val}"
    {other_key}={other_val}

    # Empty lines above and below
    """
    env_file.write_text(env_content, encoding="utf-8")

    with caplog.at_level(logging.DEBUG):
        loaded = load_env_file(env_file)

    assert loaded[secret_key] == secret_val
    assert loaded[other_key] == other_val
    assert os.environ.get(secret_key) == secret_val
    assert os.environ.get(other_key) == other_val

    # Ensure secret value never appears in stdout, stderr, or log records
    captured = capsys.readouterr()
    assert secret_val not in captured.out
    assert secret_val not in captured.err
    for record in caplog.records:
        assert secret_val not in record.getMessage()

    # Clean up environment variables
    os.environ.pop(secret_key, None)
    os.environ.pop(other_key, None)


def test_load_env_file_nonexistent_returns_empty(tmp_path: Path) -> None:
    missing = tmp_path / "missing.env"
    result = load_env_file(missing)
    assert result == {}


def test_check_budget_headroom_missing_file_returns_infinity(tmp_path: Path) -> None:
    missing_ledger = tmp_path / "missing_spend.json"
    headroom = check_budget_headroom(missing_ledger, provider="adaption", min_remaining=1.0)
    assert headroom == float("inf")


def test_check_budget_headroom_sufficient(tmp_path: Path) -> None:
    ledger_path = tmp_path / "provider_spend.json"
    cap = 50.0
    spent = 15.0
    expected_headroom = cap - spent
    ledger_content = {
        "schema": 1,
        "providers": {
            "adaption": {
                "cap": cap,
                "spent": spent,
                "unit": "credits",
            }
        },
    }
    ledger_path.write_text(json.dumps(ledger_content), encoding="utf-8")

    headroom = check_budget_headroom(ledger_path, provider="adaption", min_remaining=1.0)
    assert headroom == expected_headroom


def test_check_budget_headroom_insufficient(tmp_path: Path) -> None:
    ledger_path = tmp_path / "provider_spend.json"
    ledger_content = {
        "schema": 1,
        "providers": {
            "adaption": {
                "cap": 50.0,
                "spent": 49.5,
                "unit": "credits",
            }
        },
    }
    ledger_path.write_text(json.dumps(ledger_content), encoding="utf-8")

    with pytest.raises(InsufficientBudgetError) as exc_info:
        check_budget_headroom(ledger_path, provider="adaption", min_remaining=1.0)
    assert "Insufficient budget headroom" in str(exc_info.value)


def test_check_budget_headroom_unlisted_provider(tmp_path: Path) -> None:
    ledger_path = tmp_path / "provider_spend.json"
    ledger_content = {
        "schema": 1,
        "providers": {
            "other_provider": {
                "cap": 50.0,
                "spent": 5.0,
                "unit": "usd",
            }
        },
    }
    ledger_path.write_text(json.dumps(ledger_content), encoding="utf-8")

    headroom = check_budget_headroom(ledger_path, provider="adaption", min_remaining=1.0)
    assert headroom == float("inf")


def test_campaign_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "config.yaml"
    outdir = tmp_path / "results"
    state_file = tmp_path / "state.json"

    executed_commands: list[list[str]] = []

    def mock_runner(cmd: list[str]) -> int:
        executed_commands.append(cmd)
        return 0

    exit_code = run_campaign(
        config=config,
        outdir=outdir,
        max_concurrency=2,
        dry_run=True,
        state_file=state_file,
        runner=mock_runner,
    )

    assert exit_code == 0
    assert len(executed_commands) == 0
    assert not state_file.exists()

    captured = capsys.readouterr()
    for step in CAMPAIGN_STEPS:
        assert step in captured.out


def test_campaign_dry_run_subset_steps(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "config.yaml"
    outdir = tmp_path / "results"
    state_file = tmp_path / "state.json"

    exit_code = run_campaign(
        config=config,
        outdir=outdir,
        steps=["train_clean_ring", "train_detectors"],
        dry_run=True,
        state_file=state_file,
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "train_clean_ring" in captured.out
    assert "train_detectors" in captured.out
    assert "a0_ring" not in captured.out
    assert "analyze" not in captured.out


def test_campaign_execution_and_resumption(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    outdir = tmp_path / "results"
    state_file = tmp_path / "state.json"

    executed_steps: list[str] = []

    def tracking_runner(cmd: list[str]) -> int:
        # Determine which step was called by matching command line
        for step in CAMPAIGN_STEPS:
            step_args = build_step_args(step, config=config, outdir=outdir, max_concurrency=2)
            if cmd[-len(step_args):] == step_args:
                executed_steps.append(step)
                break
        return 0

    # First run: run first 3 steps
    exit_code = run_campaign(
        config=config,
        outdir=outdir,
        steps=["train_clean_ring", "train_clean_complete", "train_infected_ring"],
        state_file=state_file,
        runner=tracking_runner,
    )
    assert exit_code == 0
    assert executed_steps == [
        "train_clean_ring",
        "train_clean_complete",
        "train_infected_ring",
    ]
    assert state_file.exists()

    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["completed_steps"] == [
        "train_clean_ring",
        "train_clean_complete",
        "train_infected_ring",
    ]

    # Second run with --resume: run first 4 steps
    executed_steps.clear()
    exit_code = run_campaign(
        config=config,
        outdir=outdir,
        steps=[
            "train_clean_ring",
            "train_clean_complete",
            "train_infected_ring",
            "train_infected_complete",
        ],
        resume=True,
        state_file=state_file,
        runner=tracking_runner,
    )
    assert exit_code == 0
    # Only step 4 should have executed
    assert executed_steps == ["train_infected_complete"]

    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["completed_steps"] == [
        "train_clean_ring",
        "train_clean_complete",
        "train_infected_ring",
        "train_infected_complete",
    ]


def test_campaign_execution_failure_aborts_and_does_not_record_step(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    outdir = tmp_path / "results"
    state_file = tmp_path / "state.json"

    call_count = 0

    def failing_runner(cmd: list[str]) -> int:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            return 1
        return 0

    exit_code = run_campaign(
        config=config,
        outdir=outdir,
        steps=["train_clean_ring", "train_clean_complete", "train_infected_ring"],
        state_file=state_file,
        runner=failing_runner,
    )

    assert exit_code == 1
    assert call_count == 2
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["completed_steps"] == ["train_clean_ring"]


def test_campaign_cli_parser_defaults() -> None:
    parser = parse_args([])
    assert parser.config == Path("experiments/configs/free_flow.yaml")
    assert parser.outdir == Path("results")
    assert parser.max_concurrency == 2
    assert parser.steps is None
    assert parser.dry_run is False
    assert parser.state_file == Path("results/campaign_state.json")
    assert parser.resume is False


def test_campaign_cli_parser_overrides() -> None:
    argv = [
        "--config",
        "custom/config.yaml",
        "--outdir",
        "custom_out",
        "--max-concurrency",
        "5",
        "--steps",
        "a0_ring,a0_complete",
        "--dry-run",
        "--resume",
        "--state-file",
        "custom_state.json",
    ]
    parser = parse_args(argv)
    assert parser.config == Path("custom/config.yaml")
    assert parser.outdir == Path("custom_out")
    assert parser.max_concurrency == 5
    assert parser.steps == ["a0_ring", "a0_complete"]
    assert parser.dry_run is True
    assert parser.resume is True
    assert parser.state_file == Path("custom_state.json")


def test_campaign_unknown_step_raises_value_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown campaign step"):
        run_campaign(
            config=tmp_path / "config.yaml",
            outdir=tmp_path / "out",
            steps=["non_existent_step"],
        )


def test_main_entry_point_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "config.yaml"
    outdir = tmp_path / "results"
    state_file = tmp_path / "state.json"
    argv = [
        "--config",
        str(config),
        "--outdir",
        str(outdir),
        "--state-file",
        str(state_file),
        "--dry-run",
        "--steps",
        "train_clean_ring",
    ]
    code = main(argv)
    assert code == 0
    captured = capsys.readouterr()
    assert "[dry-run] train_clean_ring:" in captured.out

