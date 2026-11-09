"""Offline scoring command registration."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any

from swarmlab.commands.train_detectors import run


def handler(args: argparse.Namespace) -> int:
    return asyncio.run(run(args, scoring=True))


def register_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser("score", help="Score fixed A0/A1 history with TRAIN thresholds")
    parser.add_argument("root", type=Path)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True, help="Frozen guardrail configuration")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-mock", action="store_true")
    parser.set_defaults(handler=handler)
