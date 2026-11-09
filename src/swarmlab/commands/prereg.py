"""Generate the existing preregistration manifest after checking its inputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from swarmlab import prereg


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("prereg", help="Generate the preregistration manifest")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    for style in range(3):
        if not (root / "experiments" / "payloads" / f"playbook_{style}.txt").is_file():
            raise ValueError("Preregistration needs all private playbook files")
    entries = prereg.collect_entries(root, prereg.DEFAULT_GROUPS)
    if any(not group for group in entries.values()):
        raise ValueError("Preregistration input groups must not be empty")
    if (root / "artifacts" / "preregistration_manifest.json").exists():
        raise FileExistsError("Preregistration manifest already exists")
    prereg.run(root)
    return 0
