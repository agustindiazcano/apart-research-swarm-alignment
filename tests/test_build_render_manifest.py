"""Unit tests for results render manifest builder and validator."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.render_results as render_results  # noqa: E402
from scripts.build_render_manifest import (  # noqa: E402
    CANONICAL_BLOCK_NAMES,
    build_manifest,
    main,
    verify_manifest_coverage,
)


def test_build_manifest_default_structure() -> None:
    """Verify that build_manifest returns canonical 6-block schema."""
    manifest = build_manifest()
    assert "blocks" in manifest
    blocks = manifest["blocks"]
    assert len(blocks) == 6

    names = [block["name"] for block in blocks]
    assert names == list(CANONICAL_BLOCK_NAMES)

    readme_blocks = [b for b in blocks if b["file"] == "README.md"]
    report_blocks = [b for b in blocks if b["file"] == "report/DRAFT_REPORT.md"]
    assert len(readme_blocks) == 1
    assert len(report_blocks) == 5

    assert readme_blocks[0]["name"] == "summary"
    assert readme_blocks[0]["kind"] == "table"
    assert readme_blocks[0]["source"] == "results/campaign/analysis/arm_summary.csv"

    h2_block = next(b for b in blocks if b["name"] == "h2_regression_summary")
    assert h2_block["kind"] == "value"
    assert h2_block["key"] == "status"
    assert h2_block["source"] == "results/campaign/analysis/h2.json"

    kinetics_block = next(b for b in blocks if b["name"] == "table_1_kinetics")
    assert kinetics_block["kind"] == "table"
    assert kinetics_block["source"] == "results/campaign/analysis/kinetics_a1.csv"

    detection_block = next(b for b in blocks if b["name"] == "table_2_offline_detection")
    assert detection_block["kind"] == "table"
    assert detection_block["source"] == "results/campaign/analysis/panel_a.csv"

    gating_block = next(b for b in blocks if b["name"] == "table_3_online_gating")
    assert gating_block["kind"] == "table"
    assert gating_block["source"] == "results/campaign/analysis/paired_comparisons.csv"

    cost_block = next(b for b in blocks if b["name"] == "table_4_cost_accounting")
    assert cost_block["kind"] == "table"
    assert cost_block["source"] == "results/campaign/analysis/billing_totals.csv"


def test_build_manifest_custom_parameters() -> None:
    """Verify customizable analysis directory and kinetics source file."""
    custom_dir = "custom/analysis/output"
    custom_kinetics = "kinetics.csv"
    manifest = build_manifest(analysis_dir=custom_dir, kinetics_file=custom_kinetics)
    blocks = manifest["blocks"]

    for block in blocks:
        assert block["source"].startswith(custom_dir)

    kinetics_block = next(b for b in blocks if b["name"] == "table_1_kinetics")
    assert kinetics_block["source"] == f"{custom_dir}/{custom_kinetics}"


def test_canonical_manifest_file_matches_build_manifest() -> None:
    """Verify that results/render_manifest.json on disk matches build_manifest()."""
    manifest_path = Path(__file__).resolve().parents[1] / "results" / "render_manifest.json"
    assert manifest_path.is_file(), f"Missing canonical manifest at {manifest_path}"

    with open(manifest_path, encoding="utf-8") as stream:
        disk_manifest = json.load(stream)

    expected_manifest = build_manifest()
    assert disk_manifest == expected_manifest


def test_all_markers_covered_in_repo() -> None:
    """Verify every RESULTS marker in README.md and report/DRAFT_REPORT.md is covered."""
    root = Path(__file__).resolve().parents[1]
    manifest = build_manifest()

    errors = verify_manifest_coverage(manifest, root=root)
    assert not errors, f"Manifest coverage errors: {errors}"


def test_verify_manifest_coverage_detects_unmapped_and_missing(tmp_path: Path) -> None:
    """Verify that verify_manifest_coverage reports missing markers and unmapped blocks."""
    doc_path = tmp_path / "README.md"
    doc_path.write_text(
        "# Doc\n<!-- RESULTS:BEGIN extra_marker -->\ncontent\n<!-- RESULTS:END extra_marker -->\n",
        encoding="utf-8",
    )

    manifest = {
        "blocks": [
            {
                "name": "summary",
                "file": "README.md",
                "source": "analysis/summary.csv",
                "kind": "table",
            }
        ]
    }

    errors = verify_manifest_coverage(manifest, root=tmp_path)
    assert any("extra_marker" in err for err in errors)
    assert any("summary" in err for err in errors)


def test_cli_build_manifest(tmp_path: Path) -> None:
    """Verify CLI writing manifest to specified output path."""
    out_file = tmp_path / "custom_manifest.json"
    exit_code = main(["--analysis-dir", "test/analysis", "--output", str(out_file)])
    assert exit_code == 0
    assert out_file.is_file()

    with open(out_file, encoding="utf-8") as stream:
        loaded = json.load(stream)

    expected = build_manifest(analysis_dir="test/analysis")
    assert loaded == expected


def test_render_results_end_to_end_with_synthetic_fixtures(tmp_path: Path) -> None:
    """Verify render_results.py populates all 6 blocks and passes --check."""
    repo_root = Path(__file__).resolve().parents[1]

    # Setup directories
    results_dir = tmp_path / "results"
    analysis_dir = results_dir / "campaign" / "analysis"
    report_dir = tmp_path / "report"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    # Copy template markdown files
    readme_src = repo_root / "README.md"
    report_src = repo_root / "report" / "DRAFT_REPORT.md"
    (tmp_path / "README.md").write_text(readme_src.read_text(encoding="utf-8"), encoding="utf-8")
    (report_dir / "DRAFT_REPORT.md").write_text(
        report_src.read_text(encoding="utf-8"), encoding="utf-8"
    )

    # Write manifest
    manifest_data = build_manifest()
    manifest_file = results_dir / "render_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as stream:
        json.dump(manifest_data, stream, indent=2)

    # Create synthetic analysis fixture files
    # 1. arm_summary.csv
    arm_summary_path = analysis_dir / "arm_summary.csv"
    with open(arm_summary_path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["arm", "topology", "harm", "episodes", "observed_exfiltrations"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "arm": "A1",
                "topology": "ring",
                "harm": "split",
                "episodes": "15",
                "observed_exfiltrations": "8",
            }
        )

    # 2. kinetics_a1.csv
    kinetics_path = analysis_dir / "kinetics_a1.csv"
    with open(kinetics_path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["round", "topology", "harm", "infected_mean", "ci_lo", "ci_hi"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "round": "0",
                "topology": "ring",
                "harm": "split",
                "infected_mean": "1.0",
                "ci_lo": "1.0",
                "ci_hi": "1.0",
            }
        )

    # 3. h2.json
    h2_path = analysis_dir / "h2.json"
    with open(h2_path, "w", encoding="utf-8") as stream:
        json.dump({"status": "estimated", "features": ["intercept"]}, stream)

    # 4. panel_a.csv
    panel_a_path = analysis_dir / "panel_a.csv"
    with open(panel_a_path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["detector", "playbook", "tpr", "ci_lo", "ci_hi"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "detector": "D1",
                "playbook": "seen",
                "tpr": "0.850",
                "ci_lo": "0.720",
                "ci_hi": "0.940",
            }
        )

    # 5. paired_comparisons.csv
    comparisons_path = analysis_dir / "paired_comparisons.csv"
    with open(comparisons_path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["defense", "pairs_complete", "exfiltration_reduction", "mcnemar_p"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "defense": "D1",
                "pairs_complete": "15",
                "exfiltration_reduction": "0.400",
                "mcnemar_p": "0.031",
            }
        )

    # 6. billing_totals.csv
    billing_path = analysis_dir / "billing_totals.csv"
    with open(billing_path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["provider", "billing_unit", "known_cost", "attempts"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "provider": "adaption",
                "billing_unit": "credits",
                "known_cost": "125.5",
                "attempts": "30",
            }
        )

    # Execute render_results in update mode
    exit_code = render_results.main(["--root", str(tmp_path)])
    assert exit_code == 0

    # Verify that content was written to README.md
    readme_rendered = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "arm | topology | harm | episodes | observed_exfiltrations" in readme_rendered
    assert "A1 | ring | split | 15 | 8" in readme_rendered

    # Verify that content was written to report/DRAFT_REPORT.md
    report_rendered = (report_dir / "DRAFT_REPORT.md").read_text(encoding="utf-8")
    assert "round | topology | harm | infected_mean | ci_lo | ci_hi" in report_rendered
    assert "estimated" in report_rendered
    assert "D1 | seen | 0.850 | 0.720 | 0.940" in report_rendered
    assert "D1 | n/a | n/a | 15 | 0.400 |" in report_rendered
    assert "adaption | credits | 30 | n/a | 125.500 |" in report_rendered

    # Execute render_results in check mode; should pass with exit code 0
    check_exit_code = render_results.main(["--root", str(tmp_path), "--check"])
    assert check_exit_code == 0
