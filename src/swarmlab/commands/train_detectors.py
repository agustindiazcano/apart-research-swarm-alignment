"""TRAIN command registration; runtime creates the guarded production client."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any

from swarmlab.training import rubric_scorer_factory, scorer_identity, train_detectors


async def run(args: argparse.Namespace, *, scoring: bool = False) -> int:
    # Runtime is supplied by the execution lane; no second provider factory is defined here.
    from swarmlab.config import load_config
    from swarmlab.execution import RuntimeFactory
    from swarmlab.llm.guarded import GuardedClient

    loaded = load_config(args.config)
    config = loaded.get("guardrail", loaded)
    factory = RuntimeFactory(config, purpose="guardrail")
    scorer_id = scorer_identity(config)
    client = factory.create_client()
    if not isinstance(client, GuardedClient):
        raise TypeError("Guardrail scoring requires GuardedClient")

    def scorer_factory(lexical: Any) -> Any:
        return rubric_scorer_factory(
            client,
            args.artifacts
            / ("score_parser_calls.jsonl" if scoring else "train_parser_calls.jsonl"),
        )(lexical)

    try:
        if scoring:
            from swarmlab.scoring import score_corpus

            await score_corpus(
                args.root,
                args.artifacts,
                scorer_factory=scorer_factory,
                scorer_id=scorer_id,
                allow_mock=args.allow_mock,
                output_path=args.output,
            )
        else:
            await train_detectors(
                args.root,
                args.artifacts,
                scorer_factory=scorer_factory,
                scorer_id=scorer_id,
                allow_mock=args.allow_mock,
                lam_grid=config.get("lam_grid", [0.0, 0.5, 1.0, 2.0]),
                tau_floor_grid=config.get("tau_floor_grid", [0.1, 0.25, 0.5]),
                seed=int(config.get("calibration_seed", 0)),
            )
    finally:
        await factory.aclose()
    return 0


def handler(args: argparse.Namespace) -> int:
    return asyncio.run(run(args))


def register_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser("train-detectors", help="Fit frozen TRAIN detector artifacts")
    parser.add_argument("root", type=Path)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path, required=True, help="Guardrail provider configuration"
    )
    parser.add_argument("--allow-mock", action="store_true")
    parser.set_defaults(handler=handler)
