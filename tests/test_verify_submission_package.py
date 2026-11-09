"""Unit and integration tests for the submission package verifier."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.verify_submission_package import (
    CheckResult,
    SubmissionVerificationReport,
    check_intent_audit,
    check_no_todo_results,
    check_pdf_deliverable,
    check_rendered_blocks_provenance,
    check_spend_caps_and_secrets,
    check_typography_and_hygiene,
    main,
    parse_args,
    verify_submission_package,
)


def _init_git_repo(path: Path) -> None:
    """Initialize a git repository in path and track all files."""
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "ci@example.com"], cwd=path, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "CI Runner"], cwd=path, capture_output=True, check=True
    )
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)


def _create_mock_package(tmp_path: Path) -> dict[str, Any]:
    """Populate tmp_path with a valid submission package and return metadata."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "# Project Title\n\nVerified text without placeholders.\n", encoding="utf-8"
    )

    report_dir = tmp_path / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_md_path = report_dir / "FINAL_REPORT.md"

    # Context files
    pending_path = tmp_path / "PENDING.md"
    pending_path.write_text(
        "# PENDING\n\n## Open tasks\n- Task 1\n\n## Done\n- Task 0\n", encoding="utf-8"
    )
    lastcontext_path = tmp_path / "LASTCONTEXT.md"
    lastcontext_path.write_text(
        "# LASTCONTEXT\n\n## Session state\nReady for submission.\n", encoding="utf-8"
    )

    # Experiments payload hygiene
    payloads_dir = tmp_path / "experiments" / "payloads"
    payloads_dir.mkdir(parents=True, exist_ok=True)
    (payloads_dir / "README.md").write_text("# Payloads documentation\n", encoding="utf-8")

    # Analysis artifacts and render manifest
    analysis_dir = tmp_path / "results" / "campaign" / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    summary_csv = analysis_dir / "arm_summary.csv"
    summary_bytes = b"arm,rate\ncontrol,0.05\nattack,0.75\n"
    summary_csv.write_bytes(summary_bytes)
    summary_sha = hashlib.sha256(summary_bytes).hexdigest()

    h2_json = analysis_dir / "h2.json"
    h2_bytes = b'{"status": "supported"}'
    h2_json.write_bytes(h2_bytes)
    h2_sha = hashlib.sha256(h2_bytes).hexdigest()

    manifest_data = {
        "blocks": [
            {
                "name": "summary",
                "file": "README.md",
                "source": "results/campaign/analysis/arm_summary.csv",
                "kind": "table",
            },
            {
                "name": "h2_regression_summary",
                "file": "report/FINAL_REPORT.md",
                "source": "results/campaign/analysis/h2.json",
                "kind": "value",
                "key": "status",
            },
        ]
    }
    manifest_path = tmp_path / "results" / "render_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    # Rendered blocks in target markdown files
    readme_content = (
        "# Project Title\n\n"
        "<!-- RESULTS:BEGIN summary -->\n"
        "| arm | rate |\n"
        "| --- | --- |\n"
        "| control | 0.05 |\n"
        "| attack | 0.75 |\n\n"
        f"Source: `results/campaign/analysis/arm_summary.csv` (SHA-256 `{summary_sha}`).\n"
        "<!-- RESULTS:END summary -->\n"
    )
    readme_path.write_text(readme_content, encoding="utf-8")

    report_content = (
        "# Final Report\n\n"
        "<!-- RESULTS:BEGIN h2_regression_summary -->\n"
        f"supported (source: results/campaign/analysis/h2.json, SHA-256 {h2_sha[:12]})\n"
        "<!-- RESULTS:END h2_regression_summary -->\n"
    )
    report_md_path.write_text(report_content, encoding="utf-8")

    # Intent agreement audit
    intent_data = {
        "sample_size": 100,
        "agreed_count": 98,
        "agreement_rate": 0.98,
        "wilson_ci_lo": 0.925,
        "wilson_ci_hi": 0.996,
        "mislabeled_count": 2,
        "source_sha256": hashlib.sha256(b"message_samples").hexdigest(),
        "provenance": "deterministic_heuristic",
    }
    intent_json_path = analysis_dir / "intent_agreement.json"
    intent_json_path.write_text(json.dumps(intent_data, indent=2), encoding="utf-8")

    # Provider spend ledger
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    spend_data = {
        "schema": 1,
        "providers": {
            "adaption": {"cap": 500.0, "spent": 120.50, "unit": "credits"},
            "muse": {"cap": 20.0, "spent": 14.25, "unit": "usd"},
            "vertex": {"cap": 20.0, "spent": 5.00, "unit": "usd"},
        },
    }
    spend_json_path = artifacts_dir / "provider_spend.json"
    spend_json_path.write_text(json.dumps(spend_data, indent=2), encoding="utf-8")

    # PDF deliverable
    pdf_bytes = b"%PDF-1.4\n" + (b"X" * 2048)
    pdf_path = report_dir / "SWARM_CONTAGION_REPORT.pdf"
    pdf_path.write_bytes(pdf_bytes)

    # Page count audit
    page_audit_data = {
        "total_pages": 7,
        "main_body_pages": 6,
        "references_start_page": 7,
        "appendix_start_page": 8,
        "within_4_to_8_page_cap": True,
    }
    page_audit_path = report_dir / "page_audit.json"
    page_audit_path.write_text(json.dumps(page_audit_data, indent=2), encoding="utf-8")

    return {
        "summary_sha": summary_sha,
        "h2_sha": h2_sha,
        "intent_data": intent_data,
        "page_audit_data": page_audit_data,
    }


def test_dataclass_structures() -> None:
    """Verify dataclasses fields and serializations."""
    result = CheckResult(
        name="test_check",
        passed=True,
        details="Verification succeeded",
        errors=[],
    )
    assert result.name == "test_check"
    assert result.passed is True
    assert result.details == "Verification succeeded"
    assert result.errors == []

    report = SubmissionVerificationReport(
        passed=True,
        checks=[result],
        summary={"total_checks": 1, "passed_checks": 1, "failed_checks": 0},
    )
    assert report.passed is True
    assert len(report.checks) == 1
    assert report.summary["total_checks"] == 1


def test_check_no_todo_results_success(tmp_path: Path) -> None:
    """Verify check_no_todo_results passes on clean markdown files."""
    _create_mock_package(tmp_path)
    res = check_no_todo_results(tmp_path)
    assert res.passed is True
    assert res.errors == []


def test_check_no_todo_results_failure_missing_file(tmp_path: Path) -> None:
    """Verify check_no_todo_results fails when expected file does not exist."""
    res = check_no_todo_results(tmp_path)
    assert res.passed is False
    assert any("README.md" in err for err in res.errors)


def test_check_no_todo_results_failure_marker_found(tmp_path: Path) -> None:
    """Verify check_no_todo_results detects TODO(result) markers."""
    _create_mock_package(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n\nRate: TODO(result)\n", encoding="utf-8")
    res = check_no_todo_results(tmp_path)
    assert res.passed is False
    assert any("README.md:3" in err and "TODO(result)" in err for err in res.errors)


def test_check_rendered_blocks_provenance_success(tmp_path: Path) -> None:
    """Verify check_rendered_blocks_provenance passes when hashes match."""
    _create_mock_package(tmp_path)
    res = check_rendered_blocks_provenance(tmp_path)
    assert res.passed is True
    assert res.errors == []


def test_check_rendered_blocks_provenance_missing_manifest(tmp_path: Path) -> None:
    """Verify failure when render manifest is absent."""
    res = check_rendered_blocks_provenance(tmp_path)
    assert res.passed is False
    assert any("Manifest file not found" in err for err in res.errors)


def test_check_rendered_blocks_provenance_missing_source(tmp_path: Path) -> None:
    """Verify failure when block source file is absent."""
    _create_mock_package(tmp_path)
    source = tmp_path / "results" / "campaign" / "analysis" / "arm_summary.csv"
    source.unlink()
    res = check_rendered_blocks_provenance(tmp_path)
    assert res.passed is False
    assert any("source file does not exist" in err for err in res.errors)


def test_check_rendered_blocks_provenance_hash_mismatch(tmp_path: Path) -> None:
    """Verify failure when markdown contains an altered or outdated hash."""
    _create_mock_package(tmp_path)
    readme = tmp_path / "README.md"
    bad_sha = "0" * 64
    tampered_content = (
        "# Project Title\n\n"
        "<!-- RESULTS:BEGIN summary -->\n"
        "| arm | rate |\n"
        "| --- | --- |\n"
        "| control | 0.05 |\n\n"
        f"Source: `results/campaign/analysis/arm_summary.csv` (SHA-256 `{bad_sha}`).\n"
        "<!-- RESULTS:END summary -->\n"
    )
    readme.write_text(tampered_content, encoding="utf-8")
    res = check_rendered_blocks_provenance(tmp_path)
    assert res.passed is False
    assert any("does not contain expected SHA-256" in err for err in res.errors)


def test_check_intent_audit_success(tmp_path: Path) -> None:
    """Verify check_intent_audit passes on conforming audit file."""
    _create_mock_package(tmp_path)
    res = check_intent_audit(tmp_path)
    assert res.passed is True
    assert res.errors == []


def test_check_intent_audit_invalid_metrics(tmp_path: Path) -> None:
    """Verify check_intent_audit detects invalid bounds or missing fields."""
    _create_mock_package(tmp_path)
    audit_file = tmp_path / "results" / "campaign" / "analysis" / "intent_agreement.json"

    # Sample size 0
    audit_file.write_text(json.dumps({"sample_size": 0, "agreement_rate": 0.5}), encoding="utf-8")
    res = check_intent_audit(tmp_path)
    assert res.passed is False
    assert any("sample_size" in err for err in res.errors)

    # Inverted confidence intervals
    bad_ci = {
        "sample_size": 100,
        "agreement_rate": 0.95,
        "wilson_ci_lo": 0.98,
        "wilson_ci_hi": 0.90,
        "source_sha256": "a" * 64,
    }
    audit_file.write_text(json.dumps(bad_ci), encoding="utf-8")
    res = check_intent_audit(tmp_path)
    assert res.passed is False
    assert any("Wilson CI" in err for err in res.errors)


def test_check_spend_caps_and_secrets_success(tmp_path: Path) -> None:
    """Verify check_spend_caps_and_secrets passes with authorized caps."""
    _create_mock_package(tmp_path)
    _init_git_repo(tmp_path)
    res = check_spend_caps_and_secrets(tmp_path)
    assert res.passed is True
    assert res.errors == []


def test_check_spend_caps_and_secrets_tracked_playbook_failure(tmp_path: Path) -> None:
    """Verify failure when a playbook payload is tracked in git."""
    _create_mock_package(tmp_path)
    _init_git_repo(tmp_path)
    playbook_file = tmp_path / "experiments" / "payloads" / "playbook_01.txt"
    playbook_file.write_text("Confidential payload text\n", encoding="utf-8")
    subprocess.run(["git", "add", "experiments/payloads/playbook_01.txt"], cwd=tmp_path, check=True)

    res = check_spend_caps_and_secrets(tmp_path)
    assert res.passed is False
    assert any("Forbidden tracked file" in err for err in res.errors)


def test_check_spend_caps_and_secrets_exceeded_spend(tmp_path: Path) -> None:
    """Verify failure when spent exceeds cap in ledger."""
    _create_mock_package(tmp_path)
    _init_git_repo(tmp_path)
    spend_file = tmp_path / "artifacts" / "provider_spend.json"
    data = {
        "schema": 1,
        "providers": {
            "muse": {"cap": 20.0, "spent": 25.0, "unit": "usd"},
        },
    }
    spend_file.write_text(json.dumps(data), encoding="utf-8")
    res = check_spend_caps_and_secrets(tmp_path)
    assert res.passed is False
    assert any("spent 25.0 exceeds cap 20.0" in err for err in res.errors)


def test_check_spend_caps_and_secrets_exceeded_authorized_cap(tmp_path: Path) -> None:
    """Verify failure when configured cap exceeds authorized limits."""
    _create_mock_package(tmp_path)
    _init_git_repo(tmp_path)
    spend_file = tmp_path / "artifacts" / "provider_spend.json"
    data = {
        "schema": 1,
        "providers": {
            "muse": {"cap": 100.0, "spent": 10.0, "unit": "usd"},
        },
    }
    spend_file.write_text(json.dumps(data), encoding="utf-8")
    res = check_spend_caps_and_secrets(tmp_path)
    assert res.passed is False
    assert any("exceeds authorized limit" in err for err in res.errors)


def test_check_pdf_deliverable_success(tmp_path: Path) -> None:
    """Verify check_pdf_deliverable passes on conforming PDF and page audit."""
    _create_mock_package(tmp_path)
    res = check_pdf_deliverable(tmp_path)
    assert res.passed is True
    assert res.errors == []


def test_check_pdf_deliverable_missing_pdf(tmp_path: Path) -> None:
    """Verify check_pdf_deliverable detects missing PDF deliverable."""
    res = check_pdf_deliverable(tmp_path)
    assert res.passed is False
    assert any("PDF deliverable not found" in err for err in res.errors)


def test_check_pdf_deliverable_invalid_header_or_size(tmp_path: Path) -> None:
    """Verify check_pdf_deliverable validates PDF magic bytes and size."""
    _create_mock_package(tmp_path)
    pdf_path = tmp_path / "report" / "SWARM_CONTAGION_REPORT.pdf"

    # Too small
    pdf_path.write_bytes(b"%PDF-1.4\nshort")
    res = check_pdf_deliverable(tmp_path)
    assert res.passed is False
    assert any("too small" in err for err in res.errors)

    # Invalid header
    pdf_path.write_bytes(b"NOT_A_PDF\n" + (b"X" * 2048))
    res2 = check_pdf_deliverable(tmp_path)
    assert res2.passed is False
    assert any("does not start with '%PDF-'" in err for err in res2.errors)


def test_check_pdf_deliverable_page_audit_violation(tmp_path: Path) -> None:
    """Verify check_pdf_deliverable checks 4 to 8 page limits."""
    _create_mock_package(tmp_path)
    audit_path = tmp_path / "report" / "page_audit.json"

    # Exceeds 8 pages
    audit_path.write_text(
        json.dumps({"main_body_pages": 9, "within_4_to_8_page_cap": False}),
        encoding="utf-8",
    )
    res = check_pdf_deliverable(tmp_path)
    assert res.passed is False
    assert any("violates 4 to 8 page hard cap" in err for err in res.errors)


def test_check_typography_and_hygiene_success(tmp_path: Path) -> None:
    """Verify check_typography_and_hygiene passes on clean context and tracked files."""
    _create_mock_package(tmp_path)
    _init_git_repo(tmp_path)
    res = check_typography_and_hygiene(tmp_path)
    assert res.passed is True
    assert res.errors == []


def test_check_typography_and_hygiene_missing_context(tmp_path: Path) -> None:
    """Verify check_typography_and_hygiene detects missing context files."""
    res = check_typography_and_hygiene(tmp_path)
    assert res.passed is False
    assert any("PENDING.md" in err for err in res.errors)


def test_verify_submission_package_full_success(tmp_path: Path) -> None:
    """Verify full strict verification passes on completed package."""
    _create_mock_package(tmp_path)
    _init_git_repo(tmp_path)
    report = verify_submission_package(tmp_path, strict_campaign=True)
    assert report.passed is True
    assert report.summary["failed_checks"] == 0
    assert report.summary["passed_checks"] == 6


def test_verify_submission_package_pre_campaign_mode(tmp_path: Path) -> None:
    """Verify pre-campaign mode succeeds when deliverables are not yet generated."""
    # Only create hygiene files and valid payload directory
    pending_path = tmp_path / "PENDING.md"
    pending_path.write_text(
        "# PENDING\n\n## Open tasks\n- Task 1\n\n## Done\n- Task 0\n", encoding="utf-8"
    )
    lastcontext_path = tmp_path / "LASTCONTEXT.md"
    lastcontext_path.write_text(
        "# LASTCONTEXT\n\n## Session state\nPre-campaign work.\n", encoding="utf-8"
    )
    _init_git_repo(tmp_path)

    # In strict mode, it fails because deliverables are missing
    strict_report = verify_submission_package(tmp_path, strict_campaign=True)
    assert strict_report.passed is False

    # In pre-campaign mode, it passes with skipped deliverables
    pre_report = verify_submission_package(tmp_path, strict_campaign=False)
    assert pre_report.passed is True
    assert pre_report.summary["failed_checks"] == 0


def test_cli_execution_and_json_export(tmp_path: Path) -> None:
    """Verify CLI interface runs and outputs JSON report."""
    _create_mock_package(tmp_path)
    _init_git_repo(tmp_path)

    json_out = tmp_path / "report_out.json"
    argv = ["--root", str(tmp_path), "--output-json", str(json_out)]
    args = parse_args(argv)
    assert args.root == Path(str(tmp_path))
    assert args.output_json == json_out
    assert args.pre_campaign is False

    exit_code = main(argv)
    assert exit_code == 0
    assert json_out.is_file()

    report_dict = json.loads(json_out.read_text(encoding="utf-8"))
    assert report_dict["passed"] is True
    assert len(report_dict["checks"]) == 6
