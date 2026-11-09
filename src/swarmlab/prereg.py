import hashlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FileEntry:
    path: str  # POSIX path relative to root
    sha256: str  # hex digest of the file bytes
    size: int  # bytes


DEFAULT_GROUPS: dict[str, list[str]] = {
    "design": ["docs/EXPERIMENT_DESIGN.md"],
    "playbooks": ["experiments/payloads/*"],
    "configs": ["experiments/configs/**/*.yaml"],
    "analysis_code": [
        "src/swarmlab/metrics/*.py", "src/swarmlab/detectors/*.py",
        "src/swarmlab/training.py", "src/swarmlab/scoring.py",
    ],
    "runtime_code": ["src/swarmlab/**/*.py"],
    "prompts": ["src/swarmlab/swarm/prompts.py"],
}


def hash_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def collect_entries(
    root: Path,
    groups: Mapping[str, Sequence[str]],
) -> dict[str, list[FileEntry]]:
    result: dict[str, list[FileEntry]] = {}
    for group_name, patterns in groups.items():
        seen_paths: set[str] = set()
        entries: list[FileEntry] = []
        for pattern in patterns:
            clean_pattern = pattern.lstrip("/\\")
            for matched_path in root.glob(clean_pattern):
                if matched_path.is_file():
                    rel_posix = matched_path.relative_to(root).as_posix()
                    if rel_posix not in seen_paths:
                        seen_paths.add(rel_posix)
                        sha = hash_file(matched_path)
                        size = matched_path.stat().st_size
                        entries.append(
                            FileEntry(path=rel_posix, sha256=sha, size=size)
                        )
        entries.sort(key=lambda entry: entry.path)
        result[group_name] = entries
    return result


def build_manifest(
    root: Path,
    groups: Mapping[str, Sequence[str]],
    *,
    git_commit: str,
    created_utc: str,
    extra: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    collected = collect_entries(root, groups)
    groups_data = {
        group_name: [
            {"path": entry.path, "sha256": entry.sha256, "size": entry.size}
            for entry in entries
        ]
        for group_name, entries in collected.items()
    }
    return {
        "schema_version": 1,
        "git_commit": git_commit,
        "created_utc": created_utc,
        "groups": groups_data,
        "extra": dict(extra) if extra is not None else {},
    }


def manifest_digest(manifest: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_manifest(manifest: Mapping[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    canonical = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    # Bytes, not text mode: the files must be identical on every platform (LF only).
    json_path.write_bytes((canonical + "\n").encode("utf-8"))

    digest = manifest_digest(manifest)
    lines: list[str] = [
        "# Preregistration Manifest",
        "",
        f"- Git commit: {manifest.get('git_commit', '')}",
        f"- Created UTC: {manifest.get('created_utc', '')}",
        f"- Manifest digest: {digest}",
        "",
    ]

    groups: Mapping[str, Sequence[Mapping[str, Any]]] = manifest.get("groups", {})
    for group_name, entries in groups.items():
        lines.append(f"## Group: {group_name}")
        lines.append("")
        lines.append("| path | SHA-256 | bytes |")
        lines.append("| --- | --- | --- |")
        for entry in entries:
            lines.append(f"| {entry['path']} | {entry['sha256']} | {entry['size']} |")
        lines.append("")

    lines.append(
        "This manifest is created before any TEST episode runs. "
        "The tag prereg-v1 is created by the human."
    )
    lines.append("")

    md_path.write_bytes("\n".join(lines).encode("utf-8"))


def verify_manifest(
    manifest: Mapping[str, Any],
    root: Path,
    groups: Mapping[str, Sequence[str]] | None = None,
) -> list[str]:
    issues: list[str] = []
    manifest_groups: Mapping[str, Sequence[Mapping[str, Any]]] = manifest.get("groups", {})

    checked_paths: set[str] = set()
    manifest_paths: set[str] = set()
    for entries in manifest_groups.values():
        for entry in entries:
            rel_path = entry["path"]
            manifest_paths.add(rel_path)
            if rel_path in checked_paths:
                continue
            checked_paths.add(rel_path)

            file_path = root / rel_path
            if not file_path.is_file():
                issues.append(f"Missing file: {rel_path}")
            else:
                actual_sha = hash_file(file_path)
                if actual_sha != entry["sha256"]:
                    issues.append(
                        f"Hash mismatch for {rel_path}: "
                        f"expected {entry['sha256']}, got {actual_sha}"
                    )

    active_groups = groups if groups is not None else DEFAULT_GROUPS
    added_paths: set[str] = set()
    for group_name, patterns in active_groups.items():
        if groups is None and group_name not in manifest_groups:
            continue
        for pattern in patterns:
            clean_pattern = pattern.lstrip("/\\")
            for candidate in root.glob(clean_pattern):
                if candidate.is_file():
                    rel_candidate = candidate.relative_to(root).as_posix()
                    if rel_candidate not in manifest_paths:
                        added_paths.add(rel_candidate)

    for added in sorted(added_paths):
        issues.append(f"Added file: {added}")

    return issues


def current_git_commit(root: Path) -> str:
    res = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        err = res.stderr.strip()
        raise RuntimeError(
            err if err else f"git rev-parse HEAD failed with exit code {res.returncode}"
        )
    return res.stdout.strip()


def run(
    root: Path,
    groups: Mapping[str, Sequence[str]] = DEFAULT_GROUPS,
    created_utc: str | None = None,
    git_commit: str | None = None,
) -> dict[str, Any]:
    if created_utc is None:
        created_utc = datetime.now(UTC).isoformat()
    if git_commit is None:
        git_commit = current_git_commit(root)
    manifest = build_manifest(root, groups, git_commit=git_commit, created_utc=created_utc)
    json_path = root / "artifacts" / "preregistration_manifest.json"
    md_path = root / "experiments" / "PREREGISTRATION.md"
    write_manifest(manifest, json_path, md_path)
    return manifest
