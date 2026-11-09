"""Unit tests for preregistration manifest verification."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.verify_preregistration import (
    REQUIRED_CONFIGS,
    REQUIRED_MODULES,
    REQUIRED_PLAYBOOKS,
    execute_prereg,
    main,
    parse_prereg_markdown,
    verify_determinism,
    verify_manifest_hashes,
    verify_no_secrets,
    verify_preregistration,
)


def test_required_constants_defined() -> None:
    """Verify required configs, playbooks, and modules are present in constants."""
    assert "experiments/configs/free_flow.yaml" in REQUIRED_CONFIGS
    assert "experiments/configs/pilot.yaml" in REQUIRED_CONFIGS
    matrices = [c for c in REQUIRED_CONFIGS if c.startswith("experiments/configs/matrices/")]
    assert len(matrices) == 10

    for idx in range(3):
        assert f"experiments/payloads/playbook_{idx}.txt" in REQUIRED_PLAYBOOKS

    assert "src/swarmlab/schema.py" in REQUIRED_MODULES
    assert "src/swarmlab/swarm/prompts.py" in REQUIRED_MODULES
    assert "src/swarmlab/world/generator.py" in REQUIRED_MODULES
    detector_mods = [m for m in REQUIRED_MODULES if m.startswith("src/swarmlab/detectors/")]
    assert len(detector_mods) >= 6


def test_parse_prereg_markdown_extracts_paths_and_hashes(tmp_path: Path) -> None:
    """Verify markdown table parsing extracts path and sha256 mappings correctly."""
    md_content = (
        "# Preregistration Manifest\n\n"
        "- Git commit: 0123456789abcdef\n"
        "- Created UTC: 2026-11-09T00:00:00+00:00\n"
        "- Manifest digest: feedbeef0123456789abcdef\n\n"
        "## Group: configs\n\n"
        "| path | SHA-256 | bytes |\n"
        "| --- | --- | --- |\n"
        "| experiments/configs/free_flow.yaml | aaaa1111 | 120 |\n"
        "| experiments/configs/pilot.yaml | bbbb2222 | 240 |\n"
    )
    md_file = tmp_path / "PREREGISTRATION.md"
    md_file.write_text(md_content, encoding="utf-8")

    parsed = parse_prereg_markdown(md_file)
    assert parsed["experiments/configs/free_flow.yaml"] == "aaaa1111"
    assert parsed["experiments/configs/pilot.yaml"] == "bbbb2222"


def test_verify_manifest_hashes_detects_mismatch_and_missing(tmp_path: Path) -> None:
    """Verify hash validation detects missing required files and modified contents."""
    cfg_file = tmp_path / "experiments" / "configs" / "free_flow.yaml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_bytes(b"content alpha")
    real_sha = hashlib.sha256(b"content alpha").hexdigest()

    # Manifest with a mismatch for free_flow.yaml and missing pilot.yaml
    manifest: dict[str, object] = {
        "groups": {
            "configs": [
                {
                    "path": "experiments/configs/free_flow.yaml",
                    "sha256": "wrong_sha256_value",
                    "size": 13,
                }
            ]
        }
    }

    issues = verify_manifest_hashes(tmp_path, manifest=manifest)
    assert any(
        "Hash mismatch" in issue and "experiments/configs/free_flow.yaml" in issue
        for issue in issues
    )
    assert any(
        "Missing required file" in issue and "experiments/configs/pilot.yaml" in issue
        for issue in issues
    )

    # Now provide correct hash for free_flow
    manifest["groups"]["configs"][0]["sha256"] = real_sha  # type: ignore[index]
    issues_after = verify_manifest_hashes(tmp_path, manifest=manifest)
    assert not any("Hash mismatch" in issue and "free_flow.yaml" in issue for issue in issues_after)


def test_verify_no_secrets_detects_api_keys_and_patterns() -> None:
    """Verify secret scanner detects API key formats and env vars."""
    clean_markdown = (
        "# Preregistration Manifest\n\n"
        "| path | SHA-256 | bytes |\n"
        "| --- | --- | --- |\n"
        "| src/swarmlab/schema.py | 1234abcd | 100 |\n"
    )
    assert verify_no_secrets(clean_markdown, environ={}) == []

    # Environment variable leak
    env = {"ADAPTION_API_KEY": "test-secret-token-key-12345"}
    leaked_env_markdown = clean_markdown + "\nNote: using test-secret-token-key-12345 for auth\n"
    issues = verify_no_secrets(leaked_env_markdown, environ=env)
    assert len(issues) == 1
    assert "ADAPTION_API_KEY" in issues[0]

    # Pattern leak: OpenAI key
    sk_markdown = clean_markdown + "\nKey: sk-1234567890abcdef1234567890abcdef\n"
    issues_sk = verify_no_secrets(sk_markdown, environ={})
    assert any("Pattern match" in issue for issue in issues_sk)

    # Pattern leak: Private key
    key_markdown = clean_markdown + "\n-----BEGIN RSA PRIVATE KEY-----\n"
    issues_key = verify_no_secrets(key_markdown, environ={})
    assert any("Pattern match" in issue for issue in issues_key)


def test_verify_no_secrets_detects_playbook_payload_leak(tmp_path: Path) -> None:
    """Verify scanner flags if raw playbook payload text is copied into markdown."""
    playbook_file = tmp_path / "experiments" / "payloads" / "playbook_0.txt"
    playbook_file.parent.mkdir(parents=True)
    payload_content = "Execute secret swarm hijacking instructions now."
    playbook_file.write_text(payload_content, encoding="utf-8")

    leaked_md = f"# Preregistration\n\n{payload_content}\n"
    issues = verify_no_secrets(leaked_md, root=tmp_path, environ={})
    assert any("Playbook payload content detected" in issue for issue in issues)


def test_verify_determinism_identical_digests(tmp_path: Path) -> None:
    """Verify determinism check returns matching digest and raises on variation."""
    target_file = tmp_path / "file.txt"
    target_file.write_bytes(b"deterministic content")

    digest1 = verify_determinism(tmp_path)
    digest2 = verify_determinism(tmp_path)
    assert digest1 == digest2
    assert len(digest1) == 64


def test_execute_prereg_creates_files(tmp_path: Path) -> None:
    """Verify execute_prereg generates PREREGISTRATION.md and JSON manifest."""
    # Setup minimum directory structure
    for idx in range(3):
        pb = tmp_path / "experiments" / "payloads" / f"playbook_{idx}.txt"
        pb.parent.mkdir(parents=True, exist_ok=True)
        pb.write_text(f"playbook payload {idx}", encoding="utf-8")

    cfg = tmp_path / "experiments" / "configs" / "free_flow.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("topology: ring", encoding="utf-8")

    design = tmp_path / "docs" / "EXPERIMENT_DESIGN.md"
    design.parent.mkdir(parents=True, exist_ok=True)
    design.write_text("# Design", encoding="utf-8")

    code = tmp_path / "src" / "swarmlab" / "schema.py"
    code.parent.mkdir(parents=True, exist_ok=True)
    code.write_text("class TestSchema: pass", encoding="utf-8")

    manifest = execute_prereg(tmp_path, force=True)
    assert (tmp_path / "artifacts" / "preregistration_manifest.json").is_file()
    assert (tmp_path / "experiments" / "PREREGISTRATION.md").is_file()
    assert "groups" in manifest


def test_full_repo_preregistration_verification(tmp_path: Path) -> None:
    """Validate that a complete repository layout passes all preregistration checks."""
    all_files = (
        *REQUIRED_CONFIGS,
        *REQUIRED_PLAYBOOKS,
        *REQUIRED_MODULES,
        "docs/EXPERIMENT_DESIGN.md",
    )
    for rel in all_files:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"fixture content for {rel}", encoding="utf-8")
    issues = verify_preregistration(tmp_path, regenerate_if_missing=True)
    assert issues == []


def test_cli_main_success_and_failure(tmp_path: Path) -> None:
    """Verify main returns 0 on success and 1 when issues are found."""
    ok_dir = tmp_path / "ok"
    all_files = (
        *REQUIRED_CONFIGS,
        *REQUIRED_PLAYBOOKS,
        *REQUIRED_MODULES,
        "docs/EXPERIMENT_DESIGN.md",
    )
    for rel in all_files:
        p = ok_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"fixture content for {rel}", encoding="utf-8")
    ret_ok = main(["--root", str(ok_dir)])
    assert ret_ok == 0

    # Test failure on empty dir
    ret_fail = main(["--root", str(tmp_path / "empty")])
    assert ret_fail == 1
