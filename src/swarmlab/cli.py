"""Command line entry point. Subcommands are added by later tasks, one module each."""
from __future__ import annotations

import argparse
from collections.abc import Sequence

from swarmlab import __version__
from swarmlab.commands import batch, prereg, run_episode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swarmlab",
        description="Testbed for infection chains in LLM swarms.",
    )
    parser.add_argument("--version", action="version", version=f"swarmlab {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="<command>")
    for register in (run_episode.register_parser, batch.register_parser, prereg.register_parser):
        register(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
