"""Run one configured episode and persist its events and outcome."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
from pathlib import Path

from swarmlab.commands.batch import _history
from swarmlab.config import load_config
from swarmlab.execution import RuntimeFactory, execute_episode, write_json
from swarmlab.schema import EpisodeSpec


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("run-episode", help="Run one episode with a guarded client")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--world-seed", type=int, required=True)
    parser.add_argument("--topology", choices=("ring", "complete"), required=True)
    parser.add_argument("--harm", choices=("split", "solo"))
    parser.add_argument("--arm")
    parser.add_argument("--defense", choices=("D1", "D2", "D3", "D5"))
    parser.add_argument("--episode-id")
    parser.add_argument("--outdir", "--out-dir", type=Path)
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    arm = args.arm or config.get("arm", "A1")
    harm = args.harm or config.get("harm", "split")
    defense = args.defense or config.get("defense")
    episode_id = (
        args.episode_id or f"{arm}-{args.topology}-{harm}-{defense or 'none'}-s{args.world_seed}"
    )
    spec = EpisodeSpec(episode_id, args.world_seed, args.topology, harm, arm, defense)
    factory = RuntimeFactory(config)
    outdir = args.outdir or Path(config.get("output_dir", "results"))

    async def run() -> int:
        try:
            result = await execute_episode(spec, config, outdir, factory=factory)
            history = _history(outdir / episode_id)
            write_json(
                outdir / episode_id / "result.json",
                {
                    **asdict(result),
                    "attempts": len(history),
                    "attempt_history": history,
                    "arm": spec.arm,
                    "seed": spec.seed,
                    "topology": spec.topology,
                    "harm": spec.harm,
                    "defense": spec.defense,
                    "mock": factory.mock,
                    "provider": factory.provider,
                    "model": factory.model,
                    "billing_unit": factory.billing_unit,
                },
            )
            return 0 if result.status == "complete" else 1
        finally:
            await factory.aclose()

    return asyncio.run(run())
