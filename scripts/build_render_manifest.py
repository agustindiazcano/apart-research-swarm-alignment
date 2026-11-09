"""Build and validate results render manifest for experiment documentation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

BEGIN_PATTERN = re.compile(r"^<!--\s*RESULTS:BEGIN\s+(\S+)\s*-->$")
END_PATTERN = re.compile(r"^<!--\s*RESULTS:END\s+(\S+)\s*-->$")

CANONICAL_BLOCK_NAMES: tuple[str, ...] = (
    "summary",
    "table_1_kinetics",
    "h2_regression_summary",
    "table_2_offline_detection",
    "table_3_online_gating",
    "table_4_cost_accounting",
)


def build_manifest(
    analysis_dir: str = "results/campaign/analysis",
    kinetics_file: str = "kinetics_a1.csv",
) -> dict[str, Any]:
    """Build canonical render manifest mapping marked document blocks to analysis files.

    Parameters
    ----------
    analysis_dir : str
        Base directory containing campaign analysis CSV and JSON outputs.
    kinetics_file : str
        Filename for kinetics analysis table (kinetics_a1.csv or kinetics.csv).

    Returns
    -------
    dict[str, Any]
        Dictionary matching the render manifest schema with 'blocks' key.
    """
    clean_dir = analysis_dir.rstrip("/\\")
    return {
        "blocks": [
            {
                "name": "summary",
                "file": "README.md",
                "source": f"{clean_dir}/arm_summary.csv",
                "kind": "table",
                "columns": ["arm", "topology", "harm", "episodes", "observed_exfiltrations",
                            "defense", "observed_rate_wilson_lo", "observed_rate_wilson_hi"],
                "precision": 3,
            },
            {
                "name": "table_1_kinetics",
                "file": "report/DRAFT_REPORT.md",
                "source": f"{clean_dir}/{kinetics_file}",
                "kind": "table",
                "columns": ["round", "topology", "harm", "infected_mean", "ci_lo", "ci_hi",
                            "episodes_observed"],
                "row_filter": {"round": ["0", "3", "6", "9"]},
                "precision": 2,
            },
            {
                "name": "h2_regression_summary",
                "file": "report/DRAFT_REPORT.md",
                "source": f"{clean_dir}/h2.json",
                "kind": "value",
                "key": "status",
            },
            {
                "name": "table_2_offline_detection",
                "file": "report/DRAFT_REPORT.md",
                "source": f"{clean_dir}/panel_a.csv",
                "kind": "table",
                "columns": ["detector", "playbook", "tpr", "ci_lo", "ci_hi", "auroc", "fpr",
                            "negative_messages", "positive_episodes", "positive_messages"],
                "precision": 3,
            },
            {
                "name": "table_3_online_gating",
                "file": "report/DRAFT_REPORT.md",
                "source": f"{clean_dir}/paired_comparisons.csv",
                "kind": "table",
                "columns": ["defense", "topology", "harm", "pairs_complete",
                            "exfiltration_reduction", "effect_ci_lo", "effect_ci_hi",
                            "holm_p", "utility_loss"],
                "precision": 3,
            },
            {
                "name": "table_4_cost_accounting",
                "file": "report/DRAFT_REPORT.md",
                "source": f"{clean_dir}/billing_totals.csv",
                "kind": "table",
                "columns": ["provider", "billing_unit", "attempts", "provider_returns",
                            "known_cost", "attempts_with_unknown_usage"],
                "precision": 3,
            },
        ]
    }


def verify_manifest_coverage(
    manifest: dict[str, Any],
    root: Path | str = ".",
) -> list[str]:
    """Verify bidirectional coverage between document markers and manifest blocks.

    Parameters
    ----------
    manifest : dict[str, Any]
        Render manifest dictionary containing 'blocks' entries.
    root : Path | str
        Root repository directory containing the target markdown files.

    Returns
    -------
    list[str]
        List of validation error messages, or an empty list if coverage is complete.
    """
    root_path = Path(root)
    errors: list[str] = []

    blocks = manifest.get("blocks", [])
    if not isinstance(blocks, list):
        return ["Manifest missing 'blocks' list"]

    manifest_by_file: dict[str, set[str]] = {}
    for block in blocks:
        if isinstance(block, dict) and "file" in block and "name" in block:
            manifest_by_file.setdefault(str(block["file"]), set()).add(str(block["name"]))

    for file_rel, manifest_names in manifest_by_file.items():
        target_path = root_path / file_rel
        if not target_path.is_file():
            errors.append(f"Target markdown file not found: {file_rel}")
            continue

        text = target_path.read_text(encoding="utf-8")
        found_begins: set[str] = set()
        found_ends: set[str] = set()

        for line in text.splitlines():
            stripped = line.strip()
            match_begin = BEGIN_PATTERN.match(stripped)
            if match_begin:
                found_begins.add(match_begin.group(1))
            match_end = END_PATTERN.match(stripped)
            if match_end:
                found_ends.add(match_end.group(1))

        # Check for unmapped markers in file
        for unmapped in sorted(found_begins - manifest_names):
            errors.append(f"Marker '{unmapped}' in '{file_rel}' is not mapped in manifest")

        # Check for missing markers declared in manifest
        for missing in sorted(manifest_names - found_begins):
            errors.append(f"Manifest block '{missing}' is missing from '{file_rel}'")

        # Check for mismatched begin/end markers
        for unbalanced in sorted(found_begins ^ found_ends):
            errors.append(f"Unbalanced BEGIN/END marker '{unbalanced}' in '{file_rel}'")

    return errors


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for render manifest builder."""
    parser = argparse.ArgumentParser(
        description="Build and validate results render manifest for experiment documentation."
    )
    parser.add_argument(
        "--analysis-dir",
        default="results/campaign/analysis",
        help="Directory containing analysis output files (default: results/campaign/analysis)",
    )
    parser.add_argument(
        "--kinetics-file",
        default="kinetics_a1.csv",
        choices=["kinetics_a1.csv", "kinetics.csv"],
        help="Kinetics CSV filename (default: kinetics_a1.csv)",
    )
    parser.add_argument(
        "--output",
        default="results/render_manifest.json",
        help="Output manifest JSON path (default: results/render_manifest.json)",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root repository directory (default: current directory)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify marker coverage in repository without writing output",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    """Execute render manifest generation or coverage verification."""
    args = parse_args(argv)
    manifest = build_manifest(
        analysis_dir=args.analysis_dir,
        kinetics_file=args.kinetics_file,
    )

    if args.check:
        errors = verify_manifest_coverage(manifest, root=args.root)
        if errors:
            for error in errors:
                sys.stderr.write(f"error: {error}\n")
            return 1
        print("Manifest coverage verified successfully.")
        return 0

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = Path(args.root) / out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")

    print(f"Wrote render manifest ({len(manifest['blocks'])} blocks) to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
