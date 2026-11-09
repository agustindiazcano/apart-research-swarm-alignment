"""Run or resume a matrix with a shared guarded provider client."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from swarmlab.batch import load_matrix, run_batch
from swarmlab.config import load_config
from swarmlab.execution import RuntimeFactory, execute_episode, initial_infection, write_json
from swarmlab.schema import EpisodeResult, EpisodeSpec


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("batch", help="Run or resume an episode matrix")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--outdir", "--out-dir", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-concurrency", type=int, default=10)
    parser.set_defaults(handler=handle)


def _history(base: Path) -> list[dict[str, Any]]:
    paths = [base / "manifest.json", *sorted((base / "attempts").glob("*/manifest.json"))]
    history = []
    for number, path in enumerate((path for path in paths if path.is_file()), start=1):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        history.append(
            {
                "attempt": number,
                "status": manifest["status"],
                "manifest_path": path.relative_to(base).as_posix(),
                "log_path": (path.parent / "events.jsonl").relative_to(base).as_posix(),
            }
        )
    return history


def handle(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    specs = load_matrix(args.matrix)
    outdir = args.outdir or Path(config.get("output_dir", "results"))
    if args.max_concurrency < 1:
        raise ValueError("max-concurrency must be positive")
    if not args.resume and any((outdir / spec.episode_id).exists() for spec in specs):
        raise FileExistsError("Batch output exists; use --resume")
    factory = RuntimeFactory(config)
    run_manifest = outdir / "run_manifest.json"
    input_hashes = {
        "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
        "matrix_sha256": hashlib.sha256(args.matrix.read_bytes()).hexdigest(),
    }
    if run_manifest.exists():
        recorded = json.loads(run_manifest.read_text(encoding="utf-8"))
        if recorded != input_hashes:
            raise ValueError("Batch configuration or matrix differs from the recorded run")
    else:
        write_json(run_manifest, input_hashes, exclusive=True)

    async def execute(spec: EpisodeSpec) -> EpisodeResult:
        return await execute_episode(spec, config, outdir, factory=factory)

    async def run() -> list[EpisodeResult]:
        try:
            return await run_batch(
                specs, execute, out_dir=outdir, max_concurrency=args.max_concurrency, max_retries=2
            )
        finally:
            await factory.aclose()

    results = asyncio.run(run())
    for spec, result in zip(specs, results, strict=True):
        history = _history(outdir / spec.episode_id)
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
        write_json(outdir / spec.episode_id / "result.json", payload)
    return 0 if all(result.status == "complete" for result in results) else 1
