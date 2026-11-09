#!/usr/bin/env python3
"""Campaign Execution Orchestrator.

Orchestrates the experimental campaign end-to-end with step-by-step
resumption, state tracking, and budget headroom verification.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CAMPAIGN_STEPS: tuple[str, ...] = (
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

STEP_MATRICES: dict[str, str] = {
    "train_clean_ring": "experiments/configs/matrices/train_clean_ring.yaml",
    "train_clean_complete": "experiments/configs/matrices/train_clean_complete.yaml",
    "train_infected_ring": "experiments/configs/matrices/train_infected_ring.yaml",
    "train_infected_complete": "experiments/configs/matrices/train_infected_complete.yaml",
    "a0_ring": "experiments/configs/matrices/control_ring.yaml",
    "a0_complete": "experiments/configs/matrices/control_complete.yaml",
    "a1_free_flow": "experiments/configs/matrices/free_flow.yaml",
    "a3_gating": "experiments/configs/matrices/gating.yaml",
    "a3c_gate_cost": "experiments/configs/matrices/gate_cost.yaml",
}


class InsufficientBudgetError(RuntimeError, ValueError):
    """Raised when available budget headroom is below the required minimum."""


def load_env_file(env_path: Path) -> dict[str, str]:
    """Load key-value pairs from an env file into os.environ without logging values."""
    loaded: dict[str, str] = {}
    if not env_path.is_file():
        return loaded

    content = env_path.read_text(encoding="utf-8")
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, val = stripped.split("=", 1)
        k = key.strip()
        v = val.strip()
        if (
            len(v) >= 2
            and ((v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")))
        ):
            v = v[1:-1]
        if k:
            os.environ[k] = v
            loaded[k] = v

    logger.debug("Loaded %d environment variables from %s", len(loaded), env_path)
    return loaded


def check_budget_headroom(
    ledger_path: Path,
    provider: str = "adaption",
    min_remaining: float = 1.0,
) -> float:
    """Read provider spend ledger if present and verify remaining budget headroom."""
    if not ledger_path.is_file():
        return float("inf")

    try:
        data: dict[str, Any] = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Unable to read spend ledger at {ledger_path}") from exc

    providers: dict[str, Any] = data.get("providers", {})
    if provider not in providers:
        return float("inf")

    rec = providers[provider]
    cap = rec.get("cap")
    if cap is None:
        return float("inf")

    cap_val = float(cap)
    spent_val = float(rec.get("spent", 0.0))
    if not math.isfinite(cap_val) or not math.isfinite(spent_val):
        raise ValueError(f"Non-finite amounts in ledger for provider '{provider}'")

    remaining = cap_val - spent_val
    if remaining < min_remaining:
        raise InsufficientBudgetError(
            f"Insufficient budget headroom for provider '{provider}': "
            f"{remaining:.4f} remaining < {min_remaining:.4f} required"
        )
    return remaining


def build_step_args(
    step: str,
    *,
    config: Path,
    outdir: Path,
    max_concurrency: int,
    allow_mock: bool = False,
) -> list[str]:
    """Build the swarmlab CLI arguments for a specific campaign step."""
    if step not in CAMPAIGN_STEPS:
        raise ValueError(f"Unknown campaign step: {step}")

    if step in (
        "train_clean_ring",
        "train_clean_complete",
        "train_infected_ring",
        "train_infected_complete",
    ):
        matrix_path = STEP_MATRICES[step]
        return [
            "batch",
            "--config",
            str(config),
            "--matrix",
            matrix_path,
            "--outdir",
            str(outdir / "train"),
            "--resume",
            "--max-concurrency",
            str(max_concurrency),
        ]

    if step == "train_detectors":
        cmd = [
            "train-detectors",
            str(outdir / "train"),
            "--artifacts",
            str(outdir / "detectors"),
            "--config",
            str(config),
        ]
        if allow_mock:
            cmd.append("--allow-mock")
        return cmd

    if step in ("a0_ring", "a0_complete", "a1_free_flow", "a3_gating", "a3c_gate_cost"):
        matrix_path = STEP_MATRICES[step]
        return [
            "batch",
            "--config",
            str(config),
            "--matrix",
            matrix_path,
            "--outdir",
            str(outdir / "campaign"),
            "--resume",
            "--max-concurrency",
            str(max_concurrency),
        ]

    if step == "a2_score":
        cmd = [
            "score",
            str(outdir / "campaign"),
            "--artifacts",
            str(outdir / "detectors"),
            "--config",
            str(config),
            "--output",
            str(outdir / "campaign" / "scores.json"),
        ]
        if allow_mock:
            cmd.append("--allow-mock")
        return cmd

    if step == "analyze":
        cmd = [
            "analyze",
            str(outdir / "campaign"),
            "--outdir",
            str(outdir / "campaign" / "analysis"),
        ]
        if allow_mock:
            cmd.append("--allow-mock")
        return cmd

    raise ValueError(f"Unhandled campaign step: {step}")


def build_step_command(
    step: str,
    *,
    config: Path,
    outdir: Path,
    max_concurrency: int,
    python_bin: str = sys.executable,
    allow_mock: bool = False,
) -> list[str]:
    """Build the executable command list for a specific campaign step."""
    step_args = build_step_args(
        step,
        config=config,
        outdir=outdir,
        max_concurrency=max_concurrency,
        allow_mock=allow_mock,
    )
    return [python_bin, "-m", "swarmlab.cli", *step_args]


def _default_runner(cmd: list[str]) -> int:
    """Execute a command via subprocess and return exit code."""
    res = subprocess.run(cmd)
    return int(res.returncode)


def _clear_stale_run_manifest(step: str, outdir: Path) -> None:
    """Remove batch run_manifest.json before executing a matrix step into a shared folder."""
    if step in (
        "train_clean_ring",
        "train_clean_complete",
        "train_infected_ring",
        "train_infected_complete",
    ):
        manifest = outdir / "train" / "run_manifest.json"
    elif step in ("a0_ring", "a0_complete", "a1_free_flow", "a3_gating", "a3c_gate_cost"):
        manifest = outdir / "campaign" / "run_manifest.json"
    else:
        return
    if manifest.is_file():
        manifest.unlink()


def _run_gated_batch_step(
    *,
    config_path: Path,
    matrix_path: Path,
    batch_outdir: Path,
    artifact_dir: Path,
    max_concurrency: int,
    allow_mock: bool = False,
) -> int:
    """Run an online-gating batch (A3 or A3c) with a fitted detector gate_factory."""
    import asyncio
    from dataclasses import asdict

    from swarmlab.batch import load_matrix, run_batch
    from swarmlab.commands.batch import _history
    from swarmlab.config import load_config
    from swarmlab.execution import (
        RuntimeFactory,
        execute_episode,
        initial_infection,
        write_json,
    )
    from swarmlab.llm.guarded import GuardedClient
    from swarmlab.schema import EpisodeResult, EpisodeSpec
    from swarmlab.training import make_gate, scorer_identity

    config = load_config(config_path)
    specs = load_matrix(matrix_path)
    guardrail_cfg = dict(config.get("guardrail", config))
    if "max_retries" in config and int(guardrail_cfg.get("max_retries", 0)) < int(
        config["max_retries"]
    ):
        guardrail_cfg["max_retries"] = int(config["max_retries"])
    guardrail_factory = RuntimeFactory(guardrail_cfg, purpose="guardrail")
    guardrail_factory.audit_path = artifact_dir / "online_guardrail_provider_calls.jsonl"
    scorer_id = scorer_identity(guardrail_cfg)
    guardrail_client = guardrail_factory.create_client()
    if not isinstance(guardrail_client, GuardedClient) and not allow_mock:
        raise TypeError("Online gating requires GuardedClient for guardrail")

    def gate_factory(spec: EpisodeSpec) -> Any:
        assert spec.defense is not None
        return make_gate(
            spec.defense,
            artifact_dir,
            guardrail_client if isinstance(guardrail_client, GuardedClient) else None,
            scorer_id=scorer_id,
            audit_path=artifact_dir / f"online_parser_{spec.episode_id}.jsonl",
            allow_mock=allow_mock,
        )

    factory = RuntimeFactory(config, gate_factory=gate_factory)

    async def execute(spec: EpisodeSpec) -> EpisodeResult:
        return await execute_episode(spec, config, batch_outdir, factory=factory)

    async def run() -> list[EpisodeResult]:
        try:
            return await run_batch(
                specs,
                execute,
                out_dir=batch_outdir,
                max_concurrency=max_concurrency,
                max_retries=2,
            )
        finally:
            await factory.aclose()
            await guardrail_factory.aclose()

    results = asyncio.run(run())
    for spec, result in zip(specs, results, strict=True):
        history = _history(batch_outdir / spec.episode_id)
        payload = {
            **asdict(result),
            "attempts": len(history),
            "attempt_history": history,
            "arm": spec.arm,
            "seed": spec.seed,
            "topology": spec.topology,
            "harm": spec.harm,
            "defense": spec.defense,
            "initial_infection": initial_infection(spec, config),
            "provider": factory.provider,
            "model": factory.model,
            "mock": factory.mock,
            "billing_unit": factory.billing_unit,
        }
        write_json(batch_outdir / spec.episode_id / "result.json", payload)
    return 0 if all(result.status == "complete" for result in results) else 1


def run_campaign(
    *,
    config: Path = Path("experiments/configs/free_flow.yaml"),
    outdir: Path = Path("results"),
    max_concurrency: int = 2,
    steps: Sequence[str] | None = None,
    dry_run: bool = False,
    resume: bool = False,
    state_file: Path | None = None,
    env_file: Path | None = Path(".env"),
    ledger_path: Path = Path("artifacts/provider_spend.json"),
    min_headroom: float = 1.0,
    allow_mock: bool = False,
    runner: Callable[[list[str]], int] | None = None,
) -> int:
    """Execute campaign steps sequentially with state recording and budget checking."""
    if steps is not None:
        unknown_steps = [s for s in steps if s not in CAMPAIGN_STEPS]
        if unknown_steps:
            raise ValueError(f"Unknown campaign step: {', '.join(unknown_steps)}")
        active_steps = [s for s in CAMPAIGN_STEPS if s in steps]
    else:
        active_steps = list(CAMPAIGN_STEPS)

    if env_file is not None:
        load_env_file(env_file)

    check_budget_headroom(ledger_path=ledger_path, min_remaining=min_headroom)

    resolved_state_file = state_file or (outdir / "campaign_state.json")
    completed_steps: set[str] = set()
    if resume and resolved_state_file.is_file():
        try:
            state_data = json.loads(resolved_state_file.read_text(encoding="utf-8"))
            completed_steps = set(state_data.get("completed_steps", []))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to parse existing state file %s: %s", resolved_state_file, exc)

    cmd_runner = runner or _default_runner

    for step in active_steps:
        if resume and step in completed_steps:
            print(f"Step '{step}' already completed; skipping.")
            continue

        cmd = build_step_command(
            step,
            config=config,
            outdir=outdir,
            max_concurrency=max_concurrency,
            allow_mock=allow_mock,
        )

        if dry_run:
            print(f"[dry-run] {step}: {' '.join(cmd)}")
            continue

        print(f"Running campaign step '{step}'...")
        _clear_stale_run_manifest(step, outdir)
        if runner is None and step in ("a3_gating", "a3c_gate_cost"):
            returncode = _run_gated_batch_step(
                config_path=config,
                matrix_path=Path(STEP_MATRICES[step]),
                batch_outdir=outdir / "campaign",
                artifact_dir=outdir / "detectors",
                max_concurrency=max_concurrency,
                allow_mock=allow_mock,
            )
        else:
            returncode = cmd_runner(cmd)
        if returncode != 0:
            print(f"Step '{step}' failed with exit code {returncode}.")
            return returncode

        completed_steps.add(step)
        resolved_state_file.parent.mkdir(parents=True, exist_ok=True)
        new_state = {
            "completed_steps": [s for s in CAMPAIGN_STEPS if s in completed_steps],
            "last_completed_step": step,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        resolved_state_file.write_text(json.dumps(new_state, indent=2), encoding="utf-8")

    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for the campaign orchestrator."""
    parser = argparse.ArgumentParser(
        description="Orchestrate full experimental campaign execution.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("experiments/configs/free_flow.yaml"),
        help="Experiment configuration file path",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("results"),
        help="Output base directory",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=2,
        help="Maximum parallel episode concurrency",
    )
    parser.add_argument(
        "--steps",
        type=str,
        default=None,
        help="Optional comma-separated subset of steps to run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print planned commands without running them",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Skip steps already marked as completed in state file",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path("results/campaign_state.json"),
        help="Path to campaign state persistence file",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to local .env file",
    )
    parser.add_argument(
        "--ledger-path",
        type=Path,
        default=Path("artifacts/provider_spend.json"),
        help="Path to provider spend ledger JSON file",
    )
    parser.add_argument(
        "--min-headroom",
        type=float,
        default=1.0,
        help="Minimum required budget headroom",
    )
    parser.add_argument(
        "--allow-mock",
        action="store_true",
        default=False,
        help="Allow mock execution for offline steps",
    )

    args = parser.parse_args(argv)
    if args.steps is not None and isinstance(args.steps, str):
        parsed_steps = [s.strip() for s in args.steps.split(",") if s.strip()]
        args.steps = parsed_steps
    return args


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for campaign orchestrator."""
    args = parse_args(argv)
    return run_campaign(
        config=args.config,
        outdir=args.outdir,
        max_concurrency=args.max_concurrency,
        steps=args.steps,
        dry_run=args.dry_run,
        resume=args.resume,
        state_file=args.state_file,
        env_file=args.env_file,
        ledger_path=args.ledger_path,
        min_headroom=args.min_headroom,
        allow_mock=args.allow_mock,
    )


if __name__ == "__main__":
    raise SystemExit(main())
