"""Unit tests for repository hygiene and context validator."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_repo_hygiene import (
    check_context_files,
    check_render_sync,
    check_typography_and_forbidden_words,
    main,
)

FORBIDDEN_PIECE_1: str = "hon"
FORBIDDEN_PIECE_2: str = "est"
FORBIDDEN_WORD_1: str = f"{FORBIDDEN_PIECE_1}{FORBIDDEN_PIECE_2}"
FORBIDDEN_WORD_2: str = f"{FORBIDDEN_PIECE_1}{FORBIDDEN_PIECE_2}ly"
FORBIDDEN_WORD_3: str = f"{FORBIDDEN_PIECE_1}{FORBIDDEN_PIECE_2}y"
EM_DASH_CHAR: str = chr(0x2014)


def create_context_fixtures(
    root: Path, pending_text: str | None, context_text: str | None
) -> tuple[Path, Path]:
    """Helper to create PENDING.md and LASTCONTEXT.md files."""
    pending_path = root / "PENDING.md"
    context_path = root / "LASTCONTEXT.md"
    if pending_text is not None:
        pending_path.write_text(pending_text, encoding="utf-8")
    if context_text is not None:
        context_path.write_text(context_text, encoding="utf-8")
    return pending_path, context_path


def test_check_context_files_valid(tmp_path: Path) -> None:
    """Verify check_context_files passes when files exist and have required headings."""
    pending_content = (
        "# PENDING\n\n"
        "## Open tasks\n"
        "- T01: Task 1\n\n"
        "## Done\n"
        "- T00: Task 0\n"
    )
    context_content = (
        "# LASTCONTEXT\n\n"
        "## Session state\n"
        "State summary.\n"
    )
    create_context_fixtures(tmp_path, pending_content, context_content)

    errors = check_context_files(tmp_path)
    assert errors == []


def test_check_context_files_missing_both(tmp_path: Path) -> None:
    """Verify check_context_files reports missing files."""
    errors = check_context_files(tmp_path)
    assert len(errors) == 2
    assert any("PENDING.md" in err for err in errors)
    assert any("LASTCONTEXT.md" in err for err in errors)


def test_check_context_files_empty(tmp_path: Path) -> None:
    """Verify check_context_files reports empty files."""
    create_context_fixtures(tmp_path, "   \n  ", "")
    errors = check_context_files(tmp_path)
    assert len(errors) >= 2
    assert any("PENDING.md" in err and "empty" in err for err in errors)
    assert any("LASTCONTEXT.md" in err and "empty" in err for err in errors)


def test_check_context_files_missing_headings(tmp_path: Path) -> None:
    """Verify check_context_files detects missing headings."""
    pending_content = (
        "# PENDING\n\n"
        "## Some other heading\n"
        "- Item\n"
    )
    context_content = (
        "# LASTCONTEXT\n\n"
        "## Other heading\n"
        "Content\n"
    )
    create_context_fixtures(tmp_path, pending_content, context_content)
    errors = check_context_files(tmp_path)

    expected_missing = ["## Open tasks", "## Done", "## Session state"]
    for heading in expected_missing:
        assert any(heading in err for err in errors)


def test_check_context_files_current_repo() -> None:
    """Verify check_context_files passes on the actual repository root."""
    repo_root = Path(__file__).resolve().parents[1]
    errors = check_context_files(repo_root)
    assert errors == []


def test_check_typography_clean_files(tmp_path: Path) -> None:
    """Verify clean text passes typography checks without errors."""
    clean_file = tmp_path / "doc.txt"
    clean_file.write_text("Standard clean text: commas, colons, parentheses.\n", encoding="utf-8")
    errors = check_typography_and_forbidden_words([clean_file])
    assert errors == []


def test_check_typography_em_dash_detected(tmp_path: Path) -> None:
    """Verify em dash character is detected with filename and line number."""
    bad_file = tmp_path / "notes.md"
    bad_file.write_text(f"Line 1\nPrefix {EM_DASH_CHAR} suffix\nLine 3\n", encoding="utf-8")
    errors = check_typography_and_forbidden_words([bad_file])
    assert len(errors) == 1
    assert "notes.md:2" in errors[0]
    assert "em dash" in errors[0]


def test_check_typography_forbidden_words_detected(tmp_path: Path) -> None:
    """Verify forbidden words are detected across cases."""
    bad_file = tmp_path / "statement.txt"
    lines = [
        f"This is an {FORBIDDEN_WORD_1} agent.",
        f"She spoke {FORBIDDEN_WORD_2.upper()}.",
        f"Promoting {FORBIDDEN_WORD_3.capitalize()} in testing.",
    ]
    bad_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    errors = check_typography_and_forbidden_words([bad_file])
    assert len(errors) == len(lines)
    for idx, _line in enumerate(lines, start=1):
        assert any(f"statement.txt:{idx}" in err for err in errors)


def test_check_typography_whole_word_matching(tmp_path: Path) -> None:
    """Verify whole word matching does not trigger on substrings."""
    valid_file = tmp_path / "valid.txt"
    dis_1 = "dis" + FORBIDDEN_WORD_1
    dis_3 = "dis" + FORBIDDEN_WORD_3
    valid_file.write_text(f"{dis_1} agent and {dis_3}.\n", encoding="utf-8")
    errors = check_typography_and_forbidden_words([valid_file])
    assert errors == []


def test_check_typography_exclusions(tmp_path: Path) -> None:
    """Verify excluded paths and fixtures are ignored."""
    excluded_files: list[Path] = [
        tmp_path / "AGENTS.md",
        tmp_path / "CLAUDE.md",
        tmp_path / ".github" / "workflows" / "ci.yml",
        tmp_path / "scripts" / "check_repo_hygiene.py",
        tmp_path / "fixtures" / "data.txt",
        tmp_path / "fixture_sample.json",
    ]
    for p in excluded_files:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"Forbidden {FORBIDDEN_WORD_1} and em dash {EM_DASH_CHAR}\n", encoding="utf-8")

    errors = check_typography_and_forbidden_words(excluded_files)
    assert errors == []


def test_check_typography_binary_and_missing(tmp_path: Path) -> None:
    """Verify non-existent paths and binary files are skipped safely."""
    missing = tmp_path / "does_not_exist.txt"
    bin_file = tmp_path / "image.png"
    bin_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + bytes([0x20, 0x14]))

    errors = check_typography_and_forbidden_words([missing, bin_file])
    assert errors == []


def test_check_render_sync_no_manifest(tmp_path: Path) -> None:
    """Verify check_render_sync returns no errors when manifest is absent."""
    errors = check_render_sync(tmp_path)
    assert errors == []


def test_check_render_sync_missing_sources_pre_campaign(tmp_path: Path) -> None:
    """Verify check_render_sync returns no error when source files do not exist yet."""
    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "blocks": [
            {
                "name": "tab_summary",
                "file": "report/DRAFT_REPORT.md",
                "kind": "table",
                "source": "results/summary.csv",
            }
        ]
    }
    (results_dir / "render_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    errors = check_render_sync(tmp_path)
    assert errors == []


def test_check_render_sync_all_sources_exist_and_synchronized(tmp_path: Path) -> None:
    """Verify check_render_sync succeeds when rendered blocks match source files."""
    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    source_csv = results_dir / "metrics.csv"
    source_csv.write_text("model,score\nalpha,0.95\n", encoding="utf-8")

    doc_dir = tmp_path / "docs"
    doc_dir.mkdir(parents=True, exist_ok=True)
    target_doc = doc_dir / "summary.md"

    # Compute expected table block as render_results produces it
    import hashlib
    sha = hashlib.sha256(source_csv.read_bytes()).hexdigest()
    rendered_table = (
        "| model | score |\n"
        "| --- | --- |\n"
        "| alpha | 0.95 |\n\n"
        f"Source: `results/metrics.csv` (SHA-256 `{sha}`)."
    )
    doc_content = (
        "# Summary\n\n"
        "<!-- RESULTS:BEGIN tab_metrics -->\n"
        f"{rendered_table}\n"
        "<!-- RESULTS:END tab_metrics -->\n"
    )
    target_doc.write_text(doc_content, encoding="utf-8")

    manifest = {
        "blocks": [
            {
                "name": "tab_metrics",
                "file": "docs/summary.md",
                "kind": "table",
                "source": "results/metrics.csv",
            }
        ]
    }
    (results_dir / "render_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    errors = check_render_sync(tmp_path)
    assert errors == []


def test_check_render_sync_outdated_blocks(tmp_path: Path) -> None:
    """Verify check_render_sync reports errors when rendered blocks are outdated."""
    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    source_csv = results_dir / "metrics.csv"
    source_csv.write_text("model,score\nalpha,0.95\n", encoding="utf-8")

    doc_dir = tmp_path / "docs"
    doc_dir.mkdir(parents=True, exist_ok=True)
    target_doc = doc_dir / "summary.md"
    doc_content = (
        "# Summary\n\n"
        "<!-- RESULTS:BEGIN tab_metrics -->\n"
        "outdated content\n"
        "<!-- RESULTS:END tab_metrics -->\n"
    )
    target_doc.write_text(doc_content, encoding="utf-8")

    manifest = {
        "blocks": [
            {
                "name": "tab_metrics",
                "file": "docs/summary.md",
                "kind": "table",
                "source": "results/metrics.csv",
            }
        ]
    }
    (results_dir / "render_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    errors = check_render_sync(tmp_path)
    assert len(errors) >= 1
    assert any("tab_metrics" in err for err in errors)


def test_main_cli_success(tmp_path: Path) -> None:
    """Verify main returns 0 on a clean workspace."""
    pending_content = (
        "# PENDING\n\n"
        "## Open tasks\n"
        "- T01\n\n"
        "## Done\n"
        "- T00\n"
    )
    context_content = (
        "# LASTCONTEXT\n\n"
        "## Session state\n"
        "State.\n"
    )
    create_context_fixtures(tmp_path, pending_content, context_content)

    exit_code = main(["--root", str(tmp_path)])
    assert exit_code == 0


def test_main_cli_failure(tmp_path: Path) -> None:
    """Verify main returns non-zero when hygiene checks fail."""
    # tmp_path has no context files
    exit_code = main(["--root", str(tmp_path)])
    assert exit_code != 0
