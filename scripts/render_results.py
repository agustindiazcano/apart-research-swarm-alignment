"""Render results into Markdown files from result files."""

import argparse
import csv
import hashlib
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

BEGIN_PATTERN = re.compile(r"^<!--\s*RESULTS:BEGIN\s+(\S+)\s*-->$")
END_PATTERN = re.compile(r"^<!--\s*RESULTS:END\s+(\S+)\s*-->$")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Rewrite marked results blocks in Markdown files from result files."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory (default: current directory)",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Manifest path (default: results/render_manifest.json)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether files are up to date without writing",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def _format_cell(value: str, precision: int | None) -> str:
    """Round a numeric-looking cell to ``precision`` decimals; leave other text unchanged."""
    if precision is None:
        return value
    if value == "":
        return "n/a"
    if "." not in value:
        return value
    try:
        number = float(value)
    except ValueError:
        return value
    return f"{number:.{precision}f}"


def render_table_block(
    source_path: Path,
    source_rel: str,
    columns: list[str] | None,
    precision: int | None = None,
    row_filter: dict[str, list[str]] | None = None,
) -> str:
    """Render a CSV file as a Markdown table with source attribution.

    ``columns`` selects and orders columns. ``row_filter`` keeps only rows whose
    value in a column is in the allowed list. ``precision`` rounds float-looking
    cells for display only; the SHA-256 is always of the unmodified source file.
    """
    source_bytes = source_path.read_bytes()
    sha256_hex = hashlib.sha256(source_bytes).hexdigest()

    with open(source_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    cols = list(columns) if columns else list(fieldnames)
    if row_filter:
        rows = [
            r for r in rows
            if all((r.get(k) or "") in allowed for k, allowed in row_filter.items())
        ]

    lines: list[str] = [
        f"| {' | '.join(cols)} |",
        f"| {' | '.join(['---'] * len(cols))} |",
    ]

    for row in rows:
        # A pipe inside a cell would split the Markdown cell; escape it, change nothing else.
        row_cells = [_format_cell(row.get(col) or "", precision).replace("|", "\\|") for col in cols]
        lines.append(f"| {' | '.join(row_cells)} |")

    lines.append("")
    lines.append(f"Source: `{source_rel}` (SHA-256 `{sha256_hex}`).")
    return "\n".join(lines)


def render_value_block(
    source_path: Path,
    source_rel: str,
    key: str,
) -> str:
    """Render a single value from a JSON file with source attribution."""
    source_bytes = source_path.read_bytes()
    sha256_hex = hashlib.sha256(source_bytes).hexdigest()
    short_hex = sha256_hex[:12]

    data = json.loads(source_bytes.decode("utf-8"))
    parts = key.split(".")
    cur: Any = data
    for part in parts:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(
                f"key '{key}' not found in '{source_rel}'"
            )

    # JSON literals (true, null, numbers as written) rather than Python repr.
    text = cur if isinstance(cur, str) else json.dumps(cur, ensure_ascii=False)
    return f"{text} (source: {source_rel}, SHA-256 {short_hex})"


def render_block(
    root: Path,
    block: dict[str, Any],
) -> tuple[str, bool]:
    """Render content for a manifest block. Returns content and source_exists flag."""
    source_rel = str(block.get("source", ""))
    source_path = Path(source_rel)
    if not source_path.is_absolute():
        source_path = root / source_path

    if not source_path.is_file():
        return f"TODO(result): source file missing: {source_rel}", False

    kind = block.get("kind")
    if kind == "table":
        columns = block.get("columns")
        if columns is not None and not isinstance(columns, list):
            raise ValueError(f"columns must be a list in block '{block.get('name')}'")
        precision = block.get("precision")
        row_filter = block.get("row_filter")
        content = render_table_block(source_path, source_rel, columns, precision, row_filter)
        return content, True
    elif kind == "value":
        key = block.get("key")
        if not key or not isinstance(key, str):
            raise KeyError(
                f"block '{block.get('name')}' of kind 'value' requires a string key"
            )
        content = render_value_block(source_path, source_rel, key)
        return content, True
    else:
        raise ValueError(f"unsupported block kind '{kind}' in block '{block.get('name')}'")


def process_markdown_file(
    root: Path,
    file_rel: str,
    blocks: list[dict[str, Any]],
    check_mode: bool,
) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]]]:
    """Process a single markdown file.

    Returns:
        (exit_code_for_file, updated_blocks, outdated_blocks)
        exit_code_for_file is 2 on error, 0 if valid.
    """
    target_path = Path(file_rel)
    if not target_path.is_absolute():
        target_path = root / target_path

    if not target_path.is_file():
        sys.stderr.write(f"error: file not found: {file_rel}\n")
        return 2, [], []

    with open(target_path, encoding="utf-8", newline="") as f:
        original_text = f.read()

    newline_char = "\r\n" if "\r\n" in original_text else "\n"
    lines = original_text.splitlines(keepends=True)

    begin_positions: dict[str, list[int]] = {}
    end_positions: dict[str, list[int]] = {}

    for idx, line in enumerate(lines):
        line_stripped = line.strip()
        m_begin = BEGIN_PATTERN.match(line_stripped)
        if m_begin:
            name = m_begin.group(1)
            begin_positions.setdefault(name, []).append(idx)
            continue
        m_end = END_PATTERN.match(line_stripped)
        if m_end:
            name = m_end.group(1)
            end_positions.setdefault(name, []).append(idx)

    # Check for unlisted markers
    manifest_names = {b["name"] for b in blocks}
    found_names = set(begin_positions.keys()) | set(end_positions.keys())
    for unlisted in sorted(found_names - manifest_names):
        sys.stderr.write(
            f"warning: marker '{unlisted}' in '{file_rel}' not listed in manifest\n"
        )

    # Validate markers and render blocks
    block_records: list[tuple[int, int, dict[str, Any], str, bool]] = []
    has_error = False

    for block in blocks:
        name = block.get("name", "")
        begins = begin_positions.get(name, [])
        ends = end_positions.get(name, [])

        if len(begins) == 0 or len(ends) == 0:
            sys.stderr.write(
                f"error: missing marker for block '{name}' in '{file_rel}'\n"
            )
            has_error = True
            continue

        if len(begins) > 1 or len(ends) > 1:
            sys.stderr.write(
                f"error: duplicated marker for block '{name}' in '{file_rel}'\n"
            )
            has_error = True
            continue

        begin_idx = begins[0]
        end_idx = ends[0]
        if end_idx < begin_idx:
            sys.stderr.write(
                f"error: END marker precedes BEGIN marker for block '{name}' in '{file_rel}'\n"
            )
            has_error = True
            continue

        try:
            content, source_exists = render_block(root, block)
        except Exception as exc:
            sys.stderr.write(
                f"error: failed to render block '{name}' in '{file_rel}': {exc}\n"
            )
            has_error = True
            continue

        block_records.append((begin_idx, end_idx, block, content, source_exists))

    if has_error:
        return 2, [], []

    # Check for overlapping blocks
    block_records.sort(key=lambda item: item[0])
    for i in range(len(block_records) - 1):
        if block_records[i][1] >= block_records[i + 1][0]:
            sys.stderr.write(
                f"error: overlapping markers in '{file_rel}'\n"
            )
            return 2, [], []

    outdated_blocks: list[dict[str, Any]] = []
    for begin_idx, end_idx, block, content, source_exists in block_records:
        current_inner = "".join(lines[begin_idx + 1 : end_idx])
        expected_inner_lines = [f"{line}{newline_char}" for line in content.split("\n")]
        expected_inner = "".join(expected_inner_lines)

        if not source_exists or current_inner != expected_inner:
            outdated_blocks.append(block)

    if check_mode:
        return 0, [], outdated_blocks

    # Apply replacements from bottom to top
    for begin_idx, end_idx, _block, content, _exists in reversed(block_records):
        new_inner_lines = [f"{line}{newline_char}" for line in content.split("\n")]
        lines[begin_idx + 1 : end_idx] = new_inner_lines

    new_text = "".join(lines)
    if new_text != original_text:
        with open(target_path, "w", encoding="utf-8", newline="") as f:
            f.write(new_text)

    rendered_blocks = [item[2] for item in block_records]
    missing_sources = any(not item[4] for item in block_records)
    exit_code = 2 if missing_sources else 0

    return exit_code, rendered_blocks, []


def main(argv: Sequence[str] | None = None) -> int:
    """Execute results rendering."""
    args = parse_args(argv)
    root = Path(args.root)

    if args.manifest is not None:
        manifest_path = Path(args.manifest)
        if not manifest_path.is_absolute():
            manifest_path = root / manifest_path
    else:
        manifest_path = root / "results" / "render_manifest.json"

    if not manifest_path.is_file():
        sys.stderr.write(f"error: manifest file not found: {manifest_path}\n")
        return 2

    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest_data = json.load(f)
    except Exception as exc:
        sys.stderr.write(f"error: failed to read manifest {manifest_path}: {exc}\n")
        return 2

    if not isinstance(manifest_data, dict) or "blocks" not in manifest_data:
        sys.stderr.write(f"error: manifest must contain 'blocks' list: {manifest_path}\n")
        return 2

    blocks_raw = manifest_data["blocks"]
    if not isinstance(blocks_raw, list):
        sys.stderr.write(f"error: manifest 'blocks' must be a list: {manifest_path}\n")
        return 2

    blocks: list[dict[str, Any]] = []
    seen_blocks: set[tuple[str, str]] = set()
    for block in blocks_raw:
        if not isinstance(block, dict):
            sys.stderr.write("error: each manifest block must be a JSON object\n")
            return 2
        name = block.get("name")
        file_name = block.get("file")
        if not name or not file_name:
            sys.stderr.write("error: block missing 'name' or 'file'\n")
            return 2
        key_pair = (file_name, name)
        if key_pair in seen_blocks:
            sys.stderr.write(
                f"error: duplicate block '{name}' for file '{file_name}' in manifest\n"
            )
            return 2
        seen_blocks.add(key_pair)
        blocks.append(block)

    # Group by file preserving manifest order
    files_order: list[str] = []
    blocks_by_file: dict[str, list[dict[str, Any]]] = {}
    for block in blocks:
        file_name = str(block["file"])
        if file_name not in blocks_by_file:
            files_order.append(file_name)
            blocks_by_file[file_name] = []
        blocks_by_file[file_name].append(block)

    overall_exit_code = 0
    all_outdated_blocks: list[dict[str, Any]] = []
    all_rendered_blocks: list[dict[str, Any]] = []

    for file_name in files_order:
        file_blocks = blocks_by_file[file_name]
        code, rendered, outdated = process_markdown_file(
            root, file_name, file_blocks, args.check
        )
        if code == 2:
            overall_exit_code = 2
        all_rendered_blocks.extend(rendered)
        all_outdated_blocks.extend(outdated)

    if args.check:
        if overall_exit_code == 2:
            return 2
        if all_outdated_blocks:
            for b in all_outdated_blocks:
                print(f"outdated: {b['name']} in {b['file']}")
            return 1
        return 0

    # Normal mode prints one line per block to stdout
    for block in all_rendered_blocks:
        print(f"rendered {block['name']} in {block['file']} from {block['source']}")

    return overall_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
