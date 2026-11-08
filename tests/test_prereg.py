import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Mapping, Sequence

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swarmlab.prereg import (
    DEFAULT_GROUPS,
    FileEntry,
    build_manifest,
    collect_entries,
    current_git_commit,
    hash_file,
    manifest_digest,
    run,
    verify_manifest,
    write_manifest,
)


def test_hash_file_equals_sha256(tmp_path: Path) -> None:
    test_bytes = b"swarm contagion protocol test bytes\nline 2"
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(test_bytes)

    expected_hash = hashlib.sha256(test_bytes).hexdigest()
    assert hash_file(file_path) == expected_hash

    empty_path = tmp_path / "empty.txt"
    empty_path.write_bytes(b"")
    expected_empty_hash = hashlib.sha256(b"").hexdigest()
    assert hash_file(empty_path) == expected_empty_hash


def test_collect_entries_expansion_sorting_and_deduplication(tmp_path: Path) -> None:
    group_a_dir = tmp_path / "group_a"
    group_a_dir.mkdir(parents=True)

    file_z = group_a_dir / "z.txt"
    file_a = group_a_dir / "a.txt"
    data_z = b"content z"
    data_a = b"content a"
    file_z.write_bytes(data_z)
    file_a.write_bytes(data_a)

    sub_dir = group_a_dir / "sub_directory"
    sub_dir.mkdir()

    empty_group_dir = tmp_path / "group_b"
    empty_group_dir.mkdir(parents=True)

    groups: Mapping[str, Sequence[str]] = {
        "a": ["group_a/*", "group_a/a.txt"],
        "empty_group": ["group_b/*.yaml"],
        "nonexistent": ["nonexistent_path/*"],
    }

    entries = collect_entries(tmp_path, groups)

    assert "a" in entries
    assert "empty_group" in entries
    assert "nonexistent" in entries

    assert entries["empty_group"] == []
    assert entries["nonexistent"] == []

    entries_a = entries["a"]
    expected_paths = ["group_a/a.txt", "group_a/z.txt"]
    actual_paths = [e.path for e in entries_a]
    assert actual_paths == expected_paths

    expected_entry_a = FileEntry(
        path="group_a/a.txt",
        sha256=hashlib.sha256(data_a).hexdigest(),
        size=len(data_a),
    )
    expected_entry_z = FileEntry(
        path="group_a/z.txt",
        sha256=hashlib.sha256(data_z).hexdigest(),
        size=len(data_z),
    )
    assert entries_a == [expected_entry_a, expected_entry_z]


def test_build_manifest_and_digest_determinism(tmp_path: Path) -> None:
    doc_file = tmp_path / "docs" / "test.md"
    doc_file.parent.mkdir(parents=True)
    initial_content = b"manifest test content"
    doc_file.write_bytes(initial_content)

    groups = {"docs": ["docs/*.md"]}
    commit = "a" * 40
    created_utc = "2026-11-08T12:00:00+00:00"

    manifest_1 = build_manifest(
        tmp_path,
        groups,
        git_commit=commit,
        created_utc=created_utc,
    )
    manifest_2 = build_manifest(
        tmp_path,
        groups,
        git_commit=commit,
        created_utc=created_utc,
    )

    assert manifest_1 == manifest_2

    canonical_1 = json.dumps(manifest_1, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    expected_digest = hashlib.sha256(canonical_1.encode("utf-8")).hexdigest()
    assert manifest_digest(manifest_1) == expected_digest
    assert manifest_digest(manifest_1) == manifest_digest(manifest_2)

    doc_file.write_bytes(initial_content + b" modified byte")
    manifest_3 = build_manifest(
        tmp_path,
        groups,
        git_commit=commit,
        created_utc=created_utc,
    )
    assert manifest_digest(manifest_3) != manifest_digest(manifest_1)


def test_verify_manifest_conditions(tmp_path: Path) -> None:
    doc_dir = tmp_path / "docs"
    doc_dir.mkdir(parents=True)
    doc_file = doc_dir / "target.txt"
    doc_file.write_bytes(b"original content")

    groups = {"docs": ["docs/*.txt"]}
    commit = "b" * 40
    created_utc = "2026-11-08T12:00:00+00:00"

    manifest = build_manifest(
        tmp_path,
        groups,
        git_commit=commit,
        created_utc=created_utc,
    )

    unchanged_issues = verify_manifest(manifest, tmp_path, groups=groups)
    assert unchanged_issues == []

    doc_file.write_bytes(b"modified content")
    changed_issues = verify_manifest(manifest, tmp_path, groups=groups)
    assert len(changed_issues) == 1
    assert "Hash mismatch" in changed_issues[0]
    assert "docs/target.txt" in changed_issues[0]

    doc_file.unlink()
    missing_issues = verify_manifest(manifest, tmp_path, groups=groups)
    assert len(missing_issues) == 1
    assert "Missing file" in missing_issues[0]
    assert "docs/target.txt" in missing_issues[0]

    doc_file.write_bytes(b"original content")
    new_file = doc_dir / "added.txt"
    new_file.write_bytes(b"new content")
    added_issues = verify_manifest(manifest, tmp_path, groups=groups)
    assert len(added_issues) == 1
    assert "Added file" in added_issues[0]
    assert "docs/added.txt" in added_issues[0]


def test_verify_manifest_default_groups(tmp_path: Path) -> None:
    design_doc = tmp_path / "docs" / "EXPERIMENT_DESIGN.md"
    design_doc.parent.mkdir(parents=True)
    design_doc.write_bytes(b"experiment design content")

    commit = "c" * 40
    created_utc = "2026-11-08T12:00:00+00:00"

    manifest = build_manifest(
        tmp_path,
        DEFAULT_GROUPS,
        git_commit=commit,
        created_utc=created_utc,
    )

    assert verify_manifest(manifest, tmp_path) == []

    new_config = tmp_path / "experiments" / "configs" / "baseline.yaml"
    new_config.parent.mkdir(parents=True)
    new_config.write_bytes(b"config: true")

    issues = verify_manifest(manifest, tmp_path)
    assert len(issues) == 1
    assert "Added file" in issues[0]
    assert "experiments/configs/baseline.yaml" in issues[0]


def test_write_manifest_creates_files_and_contents(tmp_path: Path) -> None:
    doc_dir = tmp_path / "docs"
    doc_dir.mkdir(parents=True)
    doc_1 = doc_dir / "file1.txt"
    doc_2 = doc_dir / "file2.txt"
    doc_1.write_bytes(b"content 1")
    doc_2.write_bytes(b"content 2")

    groups = {"docs": ["docs/*.txt"]}
    commit = "d" * 40
    created_utc = "2026-11-08T12:00:00+00:00"

    manifest = build_manifest(
        tmp_path,
        groups,
        git_commit=commit,
        created_utc=created_utc,
    )
    digest = manifest_digest(manifest)

    json_path = tmp_path / "nested" / "artifacts" / "manifest.json"
    md_path = tmp_path / "nested" / "experiments" / "MANIFEST.md"

    write_manifest(manifest, json_path, md_path)

    assert json_path.is_file()
    assert md_path.is_file()

    json_text = json_path.read_text(encoding="utf-8")
    assert json_text.endswith("\n")
    loaded = json.loads(json_text)
    assert loaded == manifest

    md_text = md_path.read_text(encoding="utf-8")
    assert digest in md_text
    assert "docs/file1.txt" in md_text
    assert "docs/file2.txt" in md_text
    assert "This manifest is created before any TEST episode runs." in md_text
    assert "The tag prereg-v1 is created by the human." in md_text


def test_run_injected_parameters(tmp_path: Path) -> None:
    design_doc = tmp_path / "docs" / "EXPERIMENT_DESIGN.md"
    design_doc.parent.mkdir(parents=True)
    design_doc.write_bytes(b"design document")

    commit = "e" * 40
    created_utc = "2026-11-08T16:00:00+00:00"

    manifest = run(
        tmp_path,
        groups=DEFAULT_GROUPS,
        created_utc=created_utc,
        git_commit=commit,
    )

    json_file = tmp_path / "artifacts" / "preregistration_manifest.json"
    md_file = tmp_path / "experiments" / "PREREGISTRATION.md"

    assert json_file.is_file()
    assert md_file.is_file()

    loaded = json.loads(json_file.read_text(encoding="utf-8"))
    assert loaded == manifest
    assert manifest["git_commit"] == commit
    assert manifest["created_utc"] == created_utc


def test_current_git_commit(tmp_path: Path) -> None:
    repo_dir = tmp_path / "git_repo"
    repo_dir.mkdir(parents=True)

    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test Runner"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "runner@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    test_file = repo_dir / "tracked.txt"
    test_file.write_bytes(b"tracked bytes")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial test commit"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    git_rev = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    commit = current_git_commit(repo_dir)
    assert commit == git_rev
    assert len(commit) == len(git_rev)
    int(commit, 16)

    not_a_repo = tmp_path / "non_repo_dir"
    not_a_repo.mkdir(parents=True)
    with pytest.raises(RuntimeError):
        current_git_commit(not_a_repo)
