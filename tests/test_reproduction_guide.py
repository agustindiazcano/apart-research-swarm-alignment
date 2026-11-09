"""Unit tests for the reproduction guide specification and verification."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from swarmlab.cli import build_parser

GUIDE_PATH = Path(__file__).resolve().parents[1] / "report" / "REPRODUCTION_GUIDE.md"


def read_guide() -> str:
    """Read the content of the reproduction guide."""
    return GUIDE_PATH.read_text(encoding="utf-8")


def extract_code_blocks(markdown_text: str) -> list[str]:
    """Extract code block contents delimited by triple backticks."""
    pattern = re.compile(r"```(?:[a-zA-Z0-9_-]+)?\n(.*?)```", re.DOTALL)
    return pattern.findall(markdown_text)


def extract_swarmlab_subcommands(markdown_text: str) -> list[str]:
    """Extract swarmlab subcommands from code blocks in the markdown document."""
    subcommands: list[str] = []
    blocks = extract_code_blocks(markdown_text)
    for block in blocks:
        for line in block.splitlines():
            stripped = line.strip()
            match = re.search(r"\bswarmlab\s+([a-zA-Z0-9_-]+)", stripped)
            if match:
                subcommands.append(match.group(1))
    return subcommands


def get_registered_subcommands() -> set[str]:
    """Retrieve the set of registered subcommands from the swarmlab CLI parser."""
    parser = build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices.keys())
    return set()


def test_guide_file_exists() -> None:
    """Verify that report/REPRODUCTION_GUIDE.md exists."""
    assert GUIDE_PATH.is_file(), f"Expected guide at {GUIDE_PATH}"


def test_guide_no_em_dash() -> None:
    """Verify that report/REPRODUCTION_GUIDE.md contains no em dash character."""
    content = read_guide()
    em_dash = "\u2014"
    assert em_dash not in content, "Em dash character found in reproduction guide"


def test_guide_no_forbidden_words() -> None:
    """Verify that report/REPRODUCTION_GUIDE.md contains no forbidden words."""
    content = read_guide()
    forbidden_terms = ["hon" + "est", "hon" + "estly", "hon" + "esty"]
    for term in forbidden_terms:
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        match = pattern.search(content)
        assert match is None, f"Forbidden word '{term}' found in reproduction guide"


def test_swarmlab_subcommands_are_valid() -> None:
    """Verify that every swarmlab subcommand in code blocks is valid in swarmlab.cli."""
    content = read_guide()
    subcommands = extract_swarmlab_subcommands(content)
    assert len(subcommands) > 0, "No swarmlab commands found in code blocks"

    registered = get_registered_subcommands()
    assert len(registered) > 0, "No subcommands registered in CLI"

    for subcmd in subcommands:
        assert subcmd in registered, f"Unknown subcommand '{subcmd}' referenced in guide"

    expected_subcommands = {
        "run-episode",
        "batch",
        "prereg",
        "analyze",
        "train-detectors",
        "score",
    }
    assert expected_subcommands.issubset(set(subcommands)), (
        f"Missing expected subcommands in guide: {expected_subcommands - set(subcommands)}"
    )


def test_required_cli_commands_present() -> None:
    """Verify that the exact required CLI command sequences are present in the guide."""
    content = read_guide()
    required_commands = [
        (
            "swarmlab run-episode --config experiments/configs/pilot.yaml "
            "--seed 901 --outdir results/pilot"
        ),
        (
            "swarmlab batch --config experiments/configs/matrices/pilot.yaml "
            "--outdir results/pilot --concurrency 5"
        ),
        (
            "swarmlab train-detectors results/train --artifacts results/train/artifacts "
            "--config experiments/configs/pilot.yaml"
        ),
        (
            "swarmlab score results/test --artifacts results/train/artifacts "
            "--config experiments/configs/pilot.yaml"
        ),
        "swarmlab analyze results/free_flow --outdir results/analysis",
        "swarmlab prereg",
        "python scripts/render_results.py",
    ]
    for cmd in required_commands:
        assert cmd in content, f"Required command missing from guide: '{cmd}'"


def test_required_sections_and_topics() -> None:
    """Verify that all required sections and topics are documented in the guide."""
    content = read_guide()

    # System requirements
    assert "Python 3.12" in content
    assert "Operating System" in content or "operating systems" in content.lower()

    # Environment variables and spend cap configurations
    assert "ADAPTION_BUDGET_CREDITS" in content
    assert "META_MUSE_BUDGET_USD" in content
    assert "VERTEX_BUDGET_USD" in content

    # Playbook placement protocol
    assert "experiments/payloads" in content
    assert "playbook_0.txt" in content
    assert "playbook_1.txt" in content
    assert "playbook_2.txt" in content
    assert "git-ignored" in content or ".gitignore" in content or "ignored" in content.lower()

    # Data integrity and verification protocol
    assert "Data Integrity" in content or "data integrity" in content.lower()
    assert "SHA-256" in content or "sha256" in content.lower() or "hash" in content.lower()
