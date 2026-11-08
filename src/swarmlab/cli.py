"""Command line entry point. Subcommands are added by later tasks, one module each."""
from __future__ import annotations

import argparse
from collections.abc import Sequence

from swarmlab import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swarmlab",
        description="Testbed for infection chains in LLM swarms.",
    )
    parser.add_argument("--version", action="version", version=f"swarmlab {__version__}")
    parser.add_subparsers(dest="command", required=True, metavar="<command>")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
