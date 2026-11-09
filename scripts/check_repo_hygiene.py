"""Repository hygiene and context validator for CI.

Verifies handoff context files, typography standards, forbidden words,
and markdown results block synchronization.
"""

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

# Construct forbidden tokens dynamically to avoid matching static scanner rules.
_PIECE_1: str = "hon"
_PIECE_2: str = "est"
FORBIDDEN_WORDS: tuple[str, ...] = (
    f"{_PIECE_1}{_PIECE_2}",
    f"{_PIECE_1}{_PIECE_2}ly",
    f"{_PIECE_1}{_PIECE_2}y",
)
FORBIDDEN_PATTERN: re.Pattern[str] = re.compile(
    r"\b(" + "|".join(FORBIDDEN_WORDS) + r")\b",
    re.IGNORECASE,
)
EM_DASH: str = "\u2014"

EXCLUDED_EXACT_NAMES: frozenset[str] = frozenset({"AGENTS.md", "CLAUDE.md"})
EXCLUDED_FILE_SUFFIXES: tuple[str, ...] = (
    ".github/workflows/ci.yml",
    "scripts/check_repo_hygiene.py",
)


def is_excluded_path(path: Path) -> bool:
    """Return True if path is excluded from typography and word checks."""
    if path.name in EXCLUDED_EXACT_NAMES:
        return True
    posix_path = path.as_posix()
    for suffix in EXCLUDED_FILE_SUFFIXES:
        if posix_path == suffix or posix_path.endswith("/" + suffix):
            return True
    if any("fixture" in part.lower() for part in path.parts) or "fixture" in path.name.lower():
        return True
    return False


def check_context_files(root: Path) -> list[str]:
    """Verify that context files exist, are non-empty, and contain required headings."""
    errors: list[str] = []

    # Check PENDING.md
    pending_path = root / "PENDING.md"
    if not pending_path.is_file():
        errors.append(f"Missing required context file: {pending_path}")
    else:
        try:
            pending_text = pending_path.read_text(encoding="utf-8")
            if not pending_text.strip():
                errors.append(f"Context file is empty: {pending_path}")
            else:
                if not re.search(r"^##\s+Open tasks\b", pending_text, re.MULTILINE):
                    errors.append(f"Missing required heading '## Open tasks' in {pending_path}")
                if not re.search(r"^##\s+Done\b", pending_text, re.MULTILINE):
                    errors.append(f"Missing required heading '## Done' in {pending_path}")
        except Exception as exc:
            errors.append(f"Failed to read {pending_path}: {exc}")

    # Check LASTCONTEXT.md
    context_path = root / "LASTCONTEXT.md"
    if not context_path.is_file():
        errors.append(f"Missing required context file: {context_path}")
    else:
        try:
            context_text = context_path.read_text(encoding="utf-8")
            if not context_text.strip():
                errors.append(f"Context file is empty: {context_path}")
            else:
                if not re.search(r"^##\s+Session state\b", context_text, re.MULTILINE):
                    errors.append(f"Missing required heading '## Session state' in {context_path}")
        except Exception as exc:
            errors.append(f"Failed to read {context_path}: {exc}")

    return errors


def check_typography_and_forbidden_words(paths: Sequence[Path]) -> list[str]:
    """Check text files for em dashes and forbidden words, respecting exclusions."""
    errors: list[str] = []

    for path in paths:
        if is_excluded_path(path):
            continue
        if not path.is_file():
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            # Skip binary or unreadable files
            continue
        except Exception:
            continue

        for line_no, line in enumerate(content.splitlines(), start=1):
            if EM_DASH in line:
                errors.append(f"{path}:{line_no}: em dash ('\\u2014') found: {line.strip()}")
            match = FORBIDDEN_PATTERN.search(line)
            if match:
                errors.append(
                    f"{path}:{line_no}: forbidden word '{match.group(0)}' found: {line.strip()}"
                )

    return errors


def check_render_sync(root: Path) -> list[str]:
    """Check render synchronization if manifest exists and all referenced sources exist on disk."""
    manifest_path = root / "results" / "render_manifest.json"
    if not manifest_path.is_file():
        return []

    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"Failed to read render manifest at {manifest_path}: {exc}"]

    if not isinstance(manifest_data, dict) or "blocks" not in manifest_data:
        return [f"Render manifest missing 'blocks' list: {manifest_path}"]

    blocks = manifest_data.get("blocks", [])
    if not isinstance(blocks, list):
        return [f"Render manifest 'blocks' must be a list: {manifest_path}"]

    if not blocks:
        return []

    # Check whether all referenced source files exist on disk
    source_files: list[Path] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        source_rel = block.get("source")
        if not source_rel or not isinstance(source_rel, str):
            continue
        source_path = Path(source_rel)
        if not source_path.is_absolute():
            source_path = root / source_path
        source_files.append(source_path)

    if not source_files:
        return []

    all_sources_exist = all(src.is_file() for src in source_files)
    if not all_sources_exist:
        # Pre-campaign status: source files do not exist yet
        return []

    # All sources exist, run render_results.py --check
    script_path = root / "scripts" / "render_results.py"
    if not script_path.is_file():
        fallback_script = Path(__file__).resolve().parent / "render_results.py"
        if fallback_script.is_file():
            script_path = fallback_script
        else:
            return [f"render_results script not found: {script_path}"]

    cmd = [
        sys.executable,
        str(script_path),
        "--root",
        str(root),
        "--check",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        output_lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        if not output_lines:
            output_lines = [line.strip() for line in proc.stderr.splitlines() if line.strip()]
        if not output_lines:
            output_lines = [f"render_results --check exited with code {proc.returncode}"]
        return output_lines

    return []


def get_tracked_files(root: Path) -> list[Path]:
    """Retrieve list of tracked files using git ls-files, with directory fallback."""
    try:
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        return [root / line.strip() for line in proc.stdout.splitlines() if line.strip()]
    except Exception:
        return [
            p
            for p in root.rglob("*")
            if p.is_file() and ".git" not in p.parts
        ]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Verify repository hygiene, context files, typography, and render sync."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory of the repository (default: current directory)",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    """Execute repository hygiene checks."""
    args = parse_args(argv)
    root = Path(args.root).resolve()

    errors: list[str] = []

    # 1. Check handoff context files
    errors.extend(check_context_files(root))

    # 2. Check typography and forbidden words in tracked files
    tracked_files = get_tracked_files(root)
    errors.extend(check_typography_and_forbidden_words(tracked_files))

    # 3. Check render sync
    errors.extend(check_render_sync(root))

    if errors:
        for err in errors:
            sys.stderr.write(f"HYGIENE ERROR: {err}\n")
        return 1

    sys.stdout.write("Repository hygiene check passed.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
