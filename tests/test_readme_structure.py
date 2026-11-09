"""Tests for README.md structure, sections, integrity, and compliance."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

README_PATH = Path(__file__).resolve().parents[1] / "README.md"


def read_readme() -> str:
    """Read the full text of README.md."""
    return README_PATH.read_text(encoding="utf-8")


def test_readme_file_exists() -> None:
    """Verify that README.md exists in the repository root."""
    assert README_PATH.is_file(), f"Expected README at {README_PATH}"


def test_readme_no_em_dash() -> None:
    """Verify that README.md contains no em dash character (\\u2014)."""
    content = read_readme()
    assert "\u2014" not in content, "Em dash character (\\u2014) found in README.md"


def test_readme_no_forbidden_words() -> None:
    """Verify that README.md contains no forbidden words from the neutral language policy."""
    content = read_readme()
    forbidden_terms = ["hon" + "est", "hon" + "estly", "hon" + "esty"]
    for term in forbidden_terms:
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        match = pattern.search(content)
        assert match is None, f"Forbidden word '{term}' found in README.md"


def test_readme_results_markers_intact() -> None:
    """Verify that automated result markers remain intact."""
    content = read_readme()
    assert "<!-- RESULTS:BEGIN summary -->" in content, "Missing RESULTS:BEGIN summary marker"
    assert "<!-- RESULTS:END summary -->" in content, "Missing RESULTS:END summary marker"


def test_readme_preexisting_work_table() -> None:
    """Verify all 4 rows of the pre-existing work table with PRE-EXISTING origin."""
    content = read_readme()
    assert "Pre-existing work vs work done during the sprint" in content

    required_entries = [
        "AFAW",
        "AFAW Engine",
        "Waggle Hive",
        "software-ai-eval",
    ]
    for entry in required_entries:
        assert entry in content, f"Missing pre-existing entry: {entry}"

    # Verify that each entry is accompanied by PRE-EXISTING
    for line in content.splitlines():
        for entry in required_entries:
            if entry in line:
                assert "PRE-EXISTING" in line, (
                    f"Entry {entry} does not have origin PRE-EXISTING in line: {line}"
                )


def test_readme_required_sections() -> None:
    """Verify all required top-level or sub-level sections exist in README.md."""
    content = read_readme()
    required_sections = [
        "Overview and Threat Model",
        "Research Questions and Hypotheses",
        "Detector Ladder",
        "Experimental Matrix",
        "Architecture and Package Layout",
        "CLI Usage and Reproduction Commands",
        "Data Integrity and Automated Result Blocks",
        "Pre-existing Work vs Work Done During the Sprint",
        "Hackathon Context and Official Links",
        "Author",
        "License",
    ]
    for section in required_sections:
        assert section.lower() in content.lower(), f"Missing required section matching: '{section}'"


def test_readme_detectors_documented() -> None:
    """Verify all 5 detectors (D1 to D5) are documented with their specific mechanisms."""
    content = read_readme()
    detector_terms = [
        "D1",
        "D2",
        "D3",
        "D4",
        "D5",
        "lexical",
        "Platt",
        "guardrail",
        "rubric",
        "logprob",
        "graph-contextual",
        "micro-verifier",
        "veto",
        "layered filter",
    ]
    for term in detector_terms:
        assert term.lower() in content.lower(), f"Missing detector mechanism term: '{term}'"


def test_readme_cli_commands_present() -> None:
    """Verify all specified CLI commands and reproduction scripts are documented."""
    content = read_readme()
    required_commands = [
        "swarmlab prereg",
        "swarmlab run-episode",
        "swarmlab batch",
        "swarmlab train-detectors",
        "swarmlab score",
        "swarmlab analyze",
        "scripts/render_results.py",
        "scripts/export_latex_tables.py",
    ]
    for cmd in required_commands:
        assert cmd in content, f"Missing CLI command or script reference: '{cmd}'"


def test_readme_experimental_matrix_details() -> None:
    """Verify that the experimental matrix mentions the 155 TEST episodes, Pilot, and TRAIN."""
    content = read_readme()
    assert "155" in content, "Missing mention of 155 TEST episodes"
    assert "pilot" in content.lower(), "Missing mention of Pilot episodes"
    assert "train" in content.lower(), "Missing mention of TRAIN episodes"
    assert "ring" in content.lower(), "Missing mention of ring topology"
    assert "complete" in content.lower(), "Missing mention of complete topology"
    assert "split" in content.lower(), "Missing mention of split credential condition"
