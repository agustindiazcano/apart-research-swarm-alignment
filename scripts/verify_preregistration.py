"""Verification script for preregistration freeze and manifest validation."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from swarmlab import prereg

REQUIRED_CONFIGS: tuple[str, ...] = (
    "experiments/configs/free_flow.yaml",
    "experiments/configs/pilot.yaml",
    "experiments/configs/matrices/control_complete.yaml",
    "experiments/configs/matrices/control_ring.yaml",
    "experiments/configs/matrices/free_flow.yaml",
    "experiments/configs/matrices/gate_cost.yaml",
    "experiments/configs/matrices/gating.yaml",
    "experiments/configs/matrices/pilot.yaml",
    "experiments/configs/matrices/train_clean_complete.yaml",
    "experiments/configs/matrices/train_clean_ring.yaml",
    "experiments/configs/matrices/train_infected_complete.yaml",
    "experiments/configs/matrices/train_infected_ring.yaml",
)

REQUIRED_PLAYBOOKS: tuple[str, ...] = (
    "experiments/payloads/playbook_0.txt",
    "experiments/payloads/playbook_1.txt",
    "experiments/payloads/playbook_2.txt",
)

REQUIRED_MODULES: tuple[str, ...] = (
    "src/swarmlab/schema.py",
    "src/swarmlab/swarm/prompts.py",
    "src/swarmlab/world/generator.py",
    "src/swarmlab/detectors/lexical.py",
    "src/swarmlab/detectors/guardrail.py",
    "src/swarmlab/detectors/graph.py",
    "src/swarmlab/detectors/verifiers.py",
    "src/swarmlab/detectors/layered.py",
    "src/swarmlab/detectors/immunity.py",
    "src/swarmlab/detectors/thresholds.py",
    "src/swarmlab/detectors/graph_detector.py",
)

SECRET_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"sk-[a-zA-Z0-9_\-]{20,}", "OpenAI API key format"),
    (r"AIza[0-9A-Za-z\-_]{35}", "Google API key format"),
    (r"sk-ant-[a-zA-Z0-9_\-]{20,}", "Anthropic API key format"),
    (r"-----BEGIN [A-Z ]+KEY-----", "Private key header"),
    (r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", "Bearer token format"),
)


def execute_prereg(
    root: Path,
    force: bool = False,
    git_commit: str | None = None,
) -> dict[str, Any]:
    """Execute preregistration and write manifest files."""
    json_path = root / "artifacts" / "preregistration_manifest.json"
    md_path = root / "experiments" / "PREREGISTRATION.md"
    if force:
        if json_path.is_file():
            json_path.unlink()
        if md_path.is_file():
            md_path.unlink()

    if git_commit is None:
        try:
            git_commit = prereg.current_git_commit(root)
        except RuntimeError:
            git_commit = "0" * 40

    return prereg.run(root, git_commit=git_commit)


def parse_prereg_markdown(md_path: Path) -> dict[str, str]:
    """Extract path to SHA-256 mapping from preregistration markdown table."""
    result: dict[str, str] = {}
    if not md_path.is_file():
        return result
    for line in md_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 4:
            path_str = parts[1]
            sha = parts[2]
            if path_str and path_str != "path" and not path_str.startswith("---"):
                result[path_str] = sha.lower()
    return result


def verify_manifest_hashes(
    root: Path,
    manifest: Mapping[str, Any] | None = None,
    md_path: Path | None = None,
) -> list[str]:
    """Verify SHA-256 digests for all required and manifest-tracked files."""
    issues: list[str] = []

    # Map of path -> sha from manifest or markdown
    manifest_map: dict[str, str] = {}

    if manifest is not None:
        groups = manifest.get("groups", {})
        if isinstance(groups, dict):
            for group_entries in groups.values():
                if isinstance(group_entries, list):
                    for entry in group_entries:
                        if isinstance(entry, dict) and "path" in entry and "sha256" in entry:
                            manifest_map[str(entry["path"])] = str(entry["sha256"]).lower()
    else:
        target_md = md_path if md_path is not None else root / "experiments" / "PREREGISTRATION.md"
        manifest_map = parse_prereg_markdown(target_md)

    # 1. Verify required configs
    for cfg in REQUIRED_CONFIGS:
        if cfg not in manifest_map:
            issues.append(f"Missing required file in manifest: {cfg}")
            continue
        disk_file = root / cfg
        if not disk_file.is_file():
            issues.append(f"Missing required file on disk: {cfg}")
            continue
        actual_sha = prereg.hash_file(disk_file)
        if actual_sha != manifest_map[cfg]:
            issues.append(
                f"Hash mismatch for {cfg}: expected {manifest_map[cfg]}, got {actual_sha}"
            )

    # 2. Verify required playbooks
    for pb in REQUIRED_PLAYBOOKS:
        if pb not in manifest_map:
            issues.append(f"Missing required file in manifest: {pb}")
            continue
        disk_file = root / pb
        if not disk_file.is_file():
            issues.append(f"Missing required file on disk: {pb}")
            continue
        actual_sha = prereg.hash_file(disk_file)
        if actual_sha != manifest_map[pb]:
            issues.append(
                f"Hash mismatch for {pb}: expected {manifest_map[pb]}, got {actual_sha}"
            )

    # 3. Verify required modules
    for mod in REQUIRED_MODULES:
        if mod not in manifest_map:
            issues.append(f"Missing required file in manifest: {mod}")
            continue
        disk_file = root / mod
        if not disk_file.is_file():
            issues.append(f"Missing required file on disk: {mod}")
            continue
        actual_sha = prereg.hash_file(disk_file)
        if actual_sha != manifest_map[mod]:
            issues.append(
                f"Hash mismatch for {mod}: expected {manifest_map[mod]}, got {actual_sha}"
            )

    # 4. Verify all files tracked in manifest match disk bytes
    for rel_path, expected_sha in manifest_map.items():
        disk_file = root / rel_path
        if not disk_file.is_file():
            issues.append(f"Manifest file missing on disk: {rel_path}")
            continue
        actual_sha = prereg.hash_file(disk_file)
        if actual_sha != expected_sha:
            issues.append(
                f"Hash mismatch for {rel_path}: expected {expected_sha}, got {actual_sha}"
            )

    return issues


def verify_no_secrets(
    content: str,
    root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> list[str]:
    """Check content for leaked API keys, tokens, or environment values."""
    issues: list[str] = []

    # Check environment variables
    env = os.environ if environ is None else environ
    sensitive_keywords = ("KEY", "SECRET", "TOKEN", "CREDENTIAL", "PASSWORD", "AUTH")
    for key, val in env.items():
        if any(kw in key.upper() for kw in sensitive_keywords):
            cleaned_val = val.strip()
            # Ignore empty strings or short default values
            if len(cleaned_val) >= 6 and cleaned_val in content:
                issues.append(f"Environment secret leaked for {key}")

    # Check known secret regex patterns
    for pattern, desc in SECRET_PATTERNS:
        if re.search(pattern, content):
            issues.append(f"Pattern match found: {desc}")

    # Check playbook payloads if root is supplied
    if root is not None:
        payloads_dir = root / "experiments" / "payloads"
        if payloads_dir.is_dir():
            for pb_file in payloads_dir.glob("playbook_*.txt"):
                if pb_file.is_file():
                    pb_text = pb_file.read_text(encoding="utf-8")
                    for line in pb_text.splitlines():
                        line_stripped = line.strip()
                        if len(line_stripped) >= 20 and line_stripped in content:
                            issues.append(
                                f"Playbook payload content detected from {pb_file.name}"
                            )
                            break

        # Check local .env file if present
        local_env = root / ".env"
        if local_env.is_file():
            for line in local_env.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    _, val = line.split("=", 1)
                    val = val.strip().strip("'\"")
                    if len(val) >= 6 and val in content:
                        issues.append("Local .env secret value leaked in markdown")

    return issues


def verify_determinism(root: Path) -> str:
    """Check hash calculation determinism and return canonical manifest digest."""
    entries1 = prereg.collect_entries(root, prereg.DEFAULT_GROUPS)
    entries2 = prereg.collect_entries(root, prereg.DEFAULT_GROUPS)

    for group in entries1:
        list1 = entries1[group]
        list2 = entries2.get(group, [])
        if len(list1) != len(list2):
            raise ValueError(f"Determinism check failed: group {group} size mismatch")
        for e1, e2 in zip(list1, list2, strict=True):
            if e1.path != e2.path or e1.sha256 != e2.sha256 or e1.size != e2.size:
                raise ValueError(f"Determinism check failed on path {e1.path}")

    # Calculate canonical digest with fixed timestamp and commit for verification test
    dummy_manifest = prereg.build_manifest(
        root,
        prereg.DEFAULT_GROUPS,
        git_commit="0" * 40,
        created_utc="2026-11-09T00:00:00+00:00",
    )
    return prereg.manifest_digest(dummy_manifest)


def verify_preregistration(
    root: Path,
    regenerate_if_missing: bool = True,
) -> list[str]:
    """Execute end-to-end preregistration verification and return issues."""
    issues: list[str] = []
    root = root.resolve()

    json_path = root / "artifacts" / "preregistration_manifest.json"
    md_path = root / "experiments" / "PREREGISTRATION.md"

    if (not json_path.is_file() or not md_path.is_file()) and regenerate_if_missing:
        try:
            execute_prereg(root, force=False)
        except Exception as exc:
            issues.append(f"Failed to execute preregistration: {exc}")
            return issues

    if not json_path.is_file():
        issues.append(f"Manifest JSON missing at {json_path}")
    if not md_path.is_file():
        issues.append(f"Preregistration markdown missing at {md_path}")
    if issues:
        return issues

    manifest_data: dict[str, Any] = {}
    try:
        manifest_data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        issues.append(f"Failed to parse manifest JSON: {exc}")

    # Hash verification
    hash_issues = verify_manifest_hashes(root, manifest=manifest_data, md_path=md_path)
    issues.extend(hash_issues)

    # Secret leak verification
    md_text = md_path.read_text(encoding="utf-8")
    secret_issues = verify_no_secrets(md_text, root=root)
    issues.extend(secret_issues)

    # Determinism check
    try:
        verify_determinism(root)
    except ValueError as exc:
        issues.append(str(exc))

    return issues


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Verify preregistration manifest hashes and secret hygiene."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Root directory of the repository",
    )
    parser.add_argument(
        "--force",
        "--generate",
        dest="force",
        action="store_true",
        help="Regenerate manifest before verification",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for preregistration validation."""
    args = parse_args(argv)
    root = args.root.resolve()

    if args.force:
        execute_prereg(root, force=True)

    issues = verify_preregistration(root, regenerate_if_missing=True)
    if issues:
        print(f"FAILED: {len(issues)} preregistration issues found:", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    print("SUCCESS: Preregistration manifest verified cleanly with zero issues.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
