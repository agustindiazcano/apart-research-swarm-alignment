"""Pre-submission package verifier and repository invariant auditor.

Verifies repository deliverables, provenance records, spend ledgers, and document
hygiene against the hackathon guidelines and project hard invariants.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

AUTHORIZED_CAPS: dict[str, float] = {
    "adaption": 500.0,
    "muse": 20.0,
    "vertex": 20.0,
}


@dataclass
class CheckResult:
    """Outcome and diagnostics for an individual verification check."""

    name: str
    passed: bool
    details: str
    errors: list[str] = field(default_factory=list)


@dataclass
class SubmissionVerificationReport:
    """Aggregated verification report containing check outcomes and summary statistics."""

    passed: bool
    checks: list[CheckResult]
    summary: dict[str, Any]


def check_no_todo_results(
    root: Path,
    files: Sequence[str] = ("README.md", "report/FINAL_REPORT.md"),
) -> CheckResult:
    """Verify that target markdown files exist and contain zero TODO(result) markers."""
    errors: list[str] = []
    pattern = re.compile(r"TODO\(result", re.IGNORECASE)

    for rel_path in files:
        target = Path(rel_path)
        if not target.is_absolute():
            target = root / target

        if not target.is_file():
            errors.append(f"Target file does not exist: {rel_path}")
            continue

        try:
            content = target.read_text(encoding="utf-8")
        except Exception as exc:
            errors.append(f"Failed to read file {rel_path}: {exc}")
            continue

        for line_no, line in enumerate(content.splitlines(), start=1):
            if pattern.search(line):
                errors.append(f"{rel_path}:{line_no}: Found TODO(result) marker: {line.strip()}")

    if errors:
        return CheckResult(
            name="no_todo_results",
            passed=False,
            details=f"Found {len(errors)} TODO(result) error(s) across target files.",
            errors=errors,
        )

    return CheckResult(
        name="no_todo_results",
        passed=True,
        details=f"Verified zero TODO(result) markers across {len(files)} target file(s).",
        errors=[],
    )


def check_rendered_blocks_provenance(
    root: Path,
    manifest_rel: str = "results/render_manifest.json",
) -> CheckResult:
    """Verify that all manifest blocks match their sources with exact SHA-256 provenance."""
    manifest_path = Path(manifest_rel)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path

    if not manifest_path.is_file():
        return CheckResult(
            name="rendered_blocks_provenance",
            passed=False,
            details=f"Manifest file not found: {manifest_rel}",
            errors=[f"Manifest file not found: {manifest_rel}"],
        )

    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return CheckResult(
            name="rendered_blocks_provenance",
            passed=False,
            details=f"Failed to parse manifest JSON at {manifest_rel}: {exc}",
            errors=[f"Failed to parse manifest JSON at {manifest_rel}: {exc}"],
        )

    if not isinstance(manifest_data, dict) or "blocks" not in manifest_data:
        return CheckResult(
            name="rendered_blocks_provenance",
            passed=False,
            details=f"Render manifest missing 'blocks' key: {manifest_rel}",
            errors=[f"Render manifest missing 'blocks' key: {manifest_rel}"],
        )

    blocks = manifest_data.get("blocks", [])
    if not isinstance(blocks, list):
        return CheckResult(
            name="rendered_blocks_provenance",
            passed=False,
            details=f"Render manifest 'blocks' must be a list: {manifest_rel}",
            errors=[f"Render manifest 'blocks' must be a list: {manifest_rel}"],
        )

    errors: list[str] = []
    file_cache: dict[Path, str] = {}

    for block in blocks:
        if not isinstance(block, dict):
            errors.append(f"Manifest block entry is not a dictionary: {block}")
            continue

        name = block.get("name")
        source_rel = block.get("source")
        target_rel = block.get("file")
        kind = block.get("kind", "table")

        if not name or not source_rel or not target_rel:
            errors.append(f"Block missing required fields (name, source, or file): {block}")
            continue

        source_path = Path(source_rel)
        if not source_path.is_absolute():
            source_path = root / source_path

        if not source_path.is_file():
            errors.append(f"Block '{name}': source file does not exist: {source_rel}")
            continue

        target_path = Path(target_rel)
        if not target_path.is_absolute():
            target_path = root / target_path

        if not target_path.is_file():
            errors.append(f"Block '{name}': target markdown file does not exist: {target_rel}")
            continue

        try:
            source_bytes = source_path.read_bytes()
            sha256_hex = hashlib.sha256(source_bytes).hexdigest()
        except Exception as exc:
            errors.append(f"Block '{name}': failed to read source file {source_rel}: {exc}")
            continue

        expected_hash = sha256_hex[:12] if kind == "value" else sha256_hex

        if target_path not in file_cache:
            try:
                file_cache[target_path] = target_path.read_text(encoding="utf-8")
            except Exception as exc:
                errors.append(f"Block '{name}': failed to read target file {target_rel}: {exc}")
                continue

        target_text = file_cache[target_path]

        marker_pattern = re.compile(
            r"<!--\s*RESULTS:BEGIN\s+"
            + re.escape(str(name))
            + r"\s*-->([\s\S]*?)<!--\s*RESULTS:END\s+"
            + re.escape(str(name))
            + r"\s*-->"
        )
        match = marker_pattern.search(target_text)
        if not match:
            errors.append(f"Block '{name}': markers not found in {target_rel}")
            continue

        block_content = match.group(1)
        if expected_hash not in block_content:
            errors.append(
                f"Block '{name}': target '{target_rel}' does not contain expected SHA-256 "
                f"'{expected_hash}' for source '{source_rel}'"
            )

    if errors:
        return CheckResult(
            name="rendered_blocks_provenance",
            passed=False,
            details=f"Rendered blocks provenance failed with {len(errors)} error(s).",
            errors=errors,
        )

    return CheckResult(
        name="rendered_blocks_provenance",
        passed=True,
        details=f"All {len(blocks)} rendered blocks verified with matching SHA-256 hashes.",
        errors=[],
    )


def check_intent_audit(
    root: Path,
    audit_json_rel: str = "results/campaign/analysis/intent_agreement.json",
) -> CheckResult:
    """Verify that intent agreement audit metrics adhere to Hard Invariant 2 requirements."""
    audit_path = Path(audit_json_rel)
    if not audit_path.is_absolute():
        audit_path = root / audit_path

    if not audit_path.is_file():
        return CheckResult(
            name="intent_audit",
            passed=False,
            details=f"Intent audit file not found: {audit_json_rel}",
            errors=[f"Intent audit file not found: {audit_json_rel}"],
        )

    try:
        data = json.loads(audit_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return CheckResult(
            name="intent_audit",
            passed=False,
            details=f"Failed to read or parse intent audit JSON at {audit_json_rel}: {exc}",
            errors=[f"Failed to read or parse intent audit JSON at {audit_json_rel}: {exc}"],
        )

    if not isinstance(data, dict):
        return CheckResult(
            name="intent_audit",
            passed=False,
            details=f"Intent audit JSON root must be an object: {audit_json_rel}",
            errors=[f"Intent audit JSON root must be an object: {audit_json_rel}"],
        )

    errors: list[str] = []

    sample_size = data.get("sample_size")
    if not isinstance(sample_size, int) or isinstance(sample_size, bool) or sample_size <= 0:
        errors.append(f"Invalid sample_size: {sample_size} (must be integer > 0)")

    agreement_rate = data.get("agreement_rate")
    if (
        not isinstance(agreement_rate, (int, float))
        or isinstance(agreement_rate, bool)
        or not (0.0 <= float(agreement_rate) <= 1.0)
    ):
        errors.append(f"Invalid agreement_rate: {agreement_rate} (must be in range [0.0, 1.0])")

    ci_lo = data.get("wilson_ci_lo")
    ci_hi = data.get("wilson_ci_hi")

    if not isinstance(ci_lo, (int, float)) or isinstance(ci_lo, bool):
        errors.append(f"Invalid wilson_ci_lo: {ci_lo} (must be numeric)")
    if not isinstance(ci_hi, (int, float)) or isinstance(ci_hi, bool):
        errors.append(f"Invalid wilson_ci_hi: {ci_hi} (must be numeric)")

    if (
        isinstance(agreement_rate, (int, float))
        and not isinstance(agreement_rate, bool)
        and isinstance(ci_lo, (int, float))
        and not isinstance(ci_lo, bool)
        and isinstance(ci_hi, (int, float))
        and not isinstance(ci_hi, bool)
    ):
        rate_val = float(agreement_rate)
        lo_val = float(ci_lo)
        hi_val = float(ci_hi)
        eps = 1e-9
        if not (lo_val - eps <= rate_val <= hi_val + eps):
            errors.append(
                f"Wilson CI [{ci_lo}, {ci_hi}] does not enclose agreement_rate {agreement_rate}"
            )

    source_sha256 = data.get("source_sha256")
    if (
        not isinstance(source_sha256, str)
        or len(source_sha256) != 64
        or not re.fullmatch(r"[0-9a-fA-F]{64}", source_sha256)
    ):
        errors.append(f"Invalid source_sha256: {source_sha256} (must be a 64-character hex string)")

    if errors:
        return CheckResult(
            name="intent_audit",
            passed=False,
            details=f"Intent audit validation failed with {len(errors)} error(s).",
            errors=errors,
        )

    return CheckResult(
        name="intent_audit",
        passed=True,
        details=(
            f"Intent audit verified: sample_size={sample_size}, "
            f"agreement_rate={float(agreement_rate):.4f}, "
            f"CI=[{float(ci_lo):.4f}, {float(ci_hi):.4f}]."
        ),
        errors=[],
    )


def check_spend_caps_and_secrets(
    root: Path,
    ledger_rel: str = "artifacts/provider_spend.json",
) -> CheckResult:
    """Verify provider spend limits and confirm payload secrecy in repository tracking."""
    errors: list[str] = []

    try:
        proc = subprocess.run(
            ["git", "ls-files", "experiments/payloads"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        tracked_payloads = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        for tracked in tracked_payloads:
            norm_path = tracked.replace("\\", "/")
            file_name = Path(norm_path).name
            if file_name != "README.md":
                errors.append(f"Forbidden tracked file in experiments/payloads: {tracked}")
    except Exception:
        payload_dir = root / "experiments" / "payloads"
        if payload_dir.is_dir():
            for p in payload_dir.iterdir():
                if p.is_file() and p.name != "README.md" and p.name.startswith("playbook_"):
                    errors.append(f"Forbidden file found in experiments/payloads: {p.name}")

    ledger_path = Path(ledger_rel)
    if not ledger_path.is_absolute():
        ledger_path = root / ledger_path

    if ledger_path.is_file():
        try:
            spend_data = json.loads(ledger_path.read_text(encoding="utf-8"))
            if not isinstance(spend_data, dict):
                errors.append(f"Spend ledger root must be an object: {ledger_rel}")
            else:
                providers = spend_data.get("providers")
                if not isinstance(providers, dict):
                    errors.append(f"Spend ledger missing 'providers' dictionary: {ledger_rel}")
                else:
                    for prov_name, prov_info in providers.items():
                        if not isinstance(prov_info, dict):
                            errors.append(
                                f"Provider '{prov_name}' entry must be a dictionary in {ledger_rel}"
                            )
                            continue

                        cap = prov_info.get("cap")
                        spent = prov_info.get("spent")

                        if cap is None:
                            errors.append(f"Provider '{prov_name}' cap is missing or null")
                        elif not isinstance(cap, (int, float)) or isinstance(cap, bool):
                            errors.append(f"Provider '{prov_name}' cap is not a number: {cap}")
                        else:
                            cap_val = float(cap)
                            max_allowed = AUTHORIZED_CAPS.get(prov_name)
                            if max_allowed is not None and cap_val > max_allowed:
                                errors.append(
                                    f"Provider '{prov_name}' cap {cap_val} "
                                    f"exceeds authorized limit {max_allowed}"
                                )
                            elif max_allowed is None:
                                errors.append(
                                    f"Provider '{prov_name}' is not an authorized provider "
                                    f"({list(AUTHORIZED_CAPS.keys())})"
                                )

                        if (
                            spent is None
                            or not isinstance(spent, (int, float))
                            or isinstance(spent, bool)
                        ):
                            errors.append(
                                f"Provider '{prov_name}' spent is not a valid number: {spent}"
                            )
                        else:
                            spent_val = float(spent)
                            if spent_val < 0.0:
                                errors.append(
                                    f"Provider '{prov_name}' spent {spent_val} is negative"
                                )
                            if isinstance(cap, (int, float)) and not isinstance(cap, bool):
                                if spent_val > float(cap):
                                    errors.append(
                                        f"Provider '{prov_name}' spent {spent_val} "
                                        f"exceeds cap {float(cap)}"
                                    )
        except Exception as exc:
            errors.append(f"Failed to read spend ledger at {ledger_rel}: {exc}")

    if errors:
        return CheckResult(
            name="spend_caps_and_secrets",
            passed=False,
            details=f"Spend caps and secrets check failed with {len(errors)} error(s).",
            errors=errors,
        )

    ledger_status = (
        f"ledger verified ({ledger_rel})" if ledger_path.is_file() else "no ledger present"
    )
    return CheckResult(
        name="spend_caps_and_secrets",
        passed=True,
        details=f"Payload git tracking clean; {ledger_status}.",
        errors=[],
    )


def check_pdf_deliverable(
    root: Path,
    pdf_rel: str = "report/SWARM_CONTAGION_REPORT.pdf",
    audit_rel: str = "report/page_audit.json",
) -> CheckResult:
    """Verify that PDF deliverable is valid and satisfies the 4 to 8 page hard cap."""
    errors: list[str] = []

    pdf_path = Path(pdf_rel)
    if not pdf_path.is_absolute():
        pdf_path = root / pdf_path

    if not pdf_path.is_file():
        errors.append(f"PDF deliverable not found: {pdf_rel}")
    else:
        try:
            size = pdf_path.stat().st_size
            if size <= 1024:
                errors.append(f"PDF deliverable too small ({size} <= 1024 bytes): {pdf_rel}")

            with open(pdf_path, "rb") as f:
                header = f.read(1024)
            if not header.startswith(b"%PDF-"):
                errors.append(f"PDF deliverable does not start with '%PDF-': {pdf_rel}")
        except Exception as exc:
            errors.append(f"Failed to read PDF deliverable at {pdf_rel}: {exc}")

    audit_path = Path(audit_rel)
    if not audit_path.is_absolute():
        audit_path = root / audit_path

    if not audit_path.is_file() and audit_rel == "report/page_audit.json":
        fallback_path = root / "report" / "pdf_audit.json"
        if fallback_path.is_file():
            audit_path = fallback_path

    if audit_path.is_file():
        try:
            audit_data = json.loads(audit_path.read_text(encoding="utf-8"))
            if not isinstance(audit_data, dict):
                errors.append(f"Page audit JSON root must be an object: {audit_path}")
            else:
                main_body_pages = audit_data.get("main_body_pages")
                within_cap = audit_data.get("within_4_to_8_page_cap")

                if (
                    not isinstance(main_body_pages, int)
                    or isinstance(main_body_pages, bool)
                    or not (4 <= main_body_pages <= 8)
                ):
                    errors.append(
                        f"Main body pages ({main_body_pages}) violates 4 to 8 page hard cap"
                    )

                if within_cap is not True:
                    errors.append(f"within_4_to_8_page_cap is {within_cap}, expected True")
        except Exception as exc:
            errors.append(f"Failed to parse page audit JSON at {audit_path}: {exc}")

    if errors:
        return CheckResult(
            name="pdf_deliverable",
            passed=False,
            details=f"PDF deliverable check failed with {len(errors)} error(s).",
            errors=errors,
        )

    file_size_str = f"{pdf_path.stat().st_size} bytes" if pdf_path.is_file() else "0 bytes"
    return CheckResult(
        name="pdf_deliverable",
        passed=True,
        details=f"PDF deliverable verified ({pdf_rel}, {file_size_str}).",
        errors=[],
    )


def check_typography_and_hygiene(root: Path) -> CheckResult:
    """Verify repository context files, typography standards, and forbidden words."""
    errors: list[str] = []

    try:
        from scripts.check_repo_hygiene import (
            check_context_files,
            check_typography_and_forbidden_words,
            get_tracked_files,
        )
    except ImportError:
        sys.path.insert(0, str(root))
        from scripts.check_repo_hygiene import (
            check_context_files,
            check_typography_and_forbidden_words,
            get_tracked_files,
        )

    errors.extend(check_context_files(root))
    tracked_files = get_tracked_files(root)
    errors.extend(check_typography_and_forbidden_words(tracked_files))

    if errors:
        return CheckResult(
            name="typography_and_hygiene",
            passed=False,
            details=f"Repository hygiene failed with {len(errors)} error(s).",
            errors=errors,
        )

    return CheckResult(
        name="typography_and_hygiene",
        passed=True,
        details="Repository context files, typography, and forbidden word checks passed.",
        errors=[],
    )


def verify_submission_package(
    root: Path,
    strict_campaign: bool = True,
) -> SubmissionVerificationReport:
    """Audit repository against submission requirements in strict or pre-campaign mode."""
    checks: list[CheckResult] = []

    # 1. No TODO(result) markers check
    final_report_path = root / "report" / "FINAL_REPORT.md"
    if not strict_campaign and not final_report_path.is_file():
        checks.append(
            CheckResult(
                name="no_todo_results",
                passed=True,
                details="Skipped in pre-campaign mode: report/FINAL_REPORT.md not yet generated.",
                errors=[],
            )
        )
    else:
        checks.append(check_no_todo_results(root))

    # 2. Rendered blocks provenance check
    manifest_path = root / "results" / "render_manifest.json"
    if not strict_campaign:
        if not manifest_path.is_file():
            checks.append(
                CheckResult(
                    name="rendered_blocks_provenance",
                    passed=True,
                    details=(
                        "Skipped in pre-campaign mode: "
                        "results/render_manifest.json not yet generated."
                    ),
                    errors=[],
                )
            )
        else:
            sources_ready = True
            try:
                m_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                for b in m_data.get("blocks", []):
                    s_rel = b.get("source")
                    if s_rel and not (root / s_rel).is_file():
                        sources_ready = False
                        break
            except Exception:
                sources_ready = False

            if not sources_ready:
                checks.append(
                    CheckResult(
                        name="rendered_blocks_provenance",
                        passed=True,
                        details=(
                            "Skipped in pre-campaign mode: "
                            "manifest source files not yet generated."
                        ),
                        errors=[],
                    )
                )
            else:
                checks.append(check_rendered_blocks_provenance(root))
    else:
        checks.append(check_rendered_blocks_provenance(root))

    # 3. Intent agreement audit check
    intent_json_path = root / "results" / "campaign" / "analysis" / "intent_agreement.json"
    if not strict_campaign and not intent_json_path.is_file():
        checks.append(
            CheckResult(
                name="intent_audit",
                passed=True,
                details="Skipped in pre-campaign mode: intent_agreement.json not yet generated.",
                errors=[],
            )
        )
    else:
        checks.append(check_intent_audit(root))

    # 4. Spend caps and secrets check
    checks.append(check_spend_caps_and_secrets(root))

    # 5. PDF deliverable check
    pdf_path = root / "report" / "SWARM_CONTAGION_REPORT.pdf"
    if not strict_campaign and not pdf_path.is_file():
        checks.append(
            CheckResult(
                name="pdf_deliverable",
                passed=True,
                details=(
                    "Skipped in pre-campaign mode: "
                    "SWARM_CONTAGION_REPORT.pdf not yet generated."
                ),
                errors=[],
            )
        )
    else:
        checks.append(check_pdf_deliverable(root))

    # 6. Repository typography and hygiene check
    checks.append(check_typography_and_hygiene(root))

    all_passed = all(c.passed for c in checks)
    summary: dict[str, Any] = {
        "total_checks": len(checks),
        "passed_checks": sum(1 for c in checks if c.passed),
        "failed_checks": sum(1 for c in checks if not c.passed),
        "strict_campaign": strict_campaign,
        "root": str(root),
    }

    return SubmissionVerificationReport(
        passed=all_passed,
        checks=checks,
        summary=summary,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for pre-submission verification."""
    parser = argparse.ArgumentParser(
        description="Verify submission package against repository invariants and deliverables."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory of the repository (default: current directory)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Path to export verification report in JSON format",
    )
    parser.add_argument(
        "--pre-campaign",
        action="store_true",
        help="Run in pre-campaign mode (skips ungenerated experiment deliverables)",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    """Execute pre-submission verification CLI."""
    args = parse_args(argv)
    root = args.root.resolve()
    strict_campaign = not args.pre_campaign
    report = verify_submission_package(root=root, strict_campaign=strict_campaign)

    if args.output_json:
        out_path = args.output_json.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report_data = {
            "passed": report.passed,
            "summary": report.summary,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "details": c.details,
                    "errors": list(c.errors),
                }
                for c in report.checks
            ],
        }
        out_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    status_label = "PASSED" if report.passed else "FAILED"
    mode_label = "strict campaign" if strict_campaign else "pre-campaign"

    sys.stdout.write(f"Submission Package Verification: {status_label} ({mode_label})\n")
    sys.stdout.write(f"Root: {root}\n")
    sys.stdout.write("-" * 64 + "\n")
    for check in report.checks:
        symbol = "[PASS]" if check.passed else "[FAIL]"
        sys.stdout.write(f"  {symbol} {check.name}: {check.details}\n")
        if check.errors:
            for err in check.errors:
                sys.stdout.write(f"         ERROR: {err}\n")
    sys.stdout.write("-" * 64 + "\n")
    passed_count = report.summary["passed_checks"]
    total_count = report.summary["total_checks"]
    sys.stdout.write(f"Summary: {passed_count}/{total_count} checks passed.\n")

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
