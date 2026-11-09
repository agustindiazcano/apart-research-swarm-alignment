"""Command registration for analysis of committed episode artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from swarmlab.metrics.analysis import analyze


def register_parser(subparsers: argparse._SubParsersAction[Any]) -> None:
    parser = subparsers.add_parser("analyze", help="Generate tables from episode logs")
    parser.add_argument("root", type=Path)
    parser.add_argument("--outdir", type=Path)
    parser.add_argument("--allow-mock", action="store_true")
    parser.set_defaults(handler=handler)


def handler(args: argparse.Namespace) -> int:
    analyze(args.root, args.outdir or args.root / "analysis", allow_mock=args.allow_mock)
    return 0
