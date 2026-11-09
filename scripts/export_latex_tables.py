"""Export analysis CSV results to LaTeX booktabs tables."""

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Mapping of standard analysis CSV filenames to default LaTeX caption and label
STANDARD_TABLE_SPECS: dict[str, tuple[str, str]] = {
    "summary.csv": ("Summary of experimental results.", "tab:summary"),
    "gating.csv": ("Detector gating performance.", "tab:gating"),
    "kinetics_a1.csv": ("Infection kinetics for arm A1.", "tab:kinetics_a1"),
}

# LaTeX special characters to escape outside TODO markers
LATEX_SPECIAL_CHARS: dict[str, str] = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}

TODO_PATTERN = re.compile(r"(TODO\([^)]*\))")


def escape_latex(text: str) -> str:
    """Escape LaTeX special characters while preserving TODO(...) markers without alteration."""
    parts = TODO_PATTERN.split(text)
    escaped_parts: list[str] = []
    for part in parts:
        if TODO_PATTERN.fullmatch(part):
            escaped_parts.append(part)
        else:
            escaped_parts.append("".join(LATEX_SPECIAL_CHARS.get(ch, ch) for ch in part))
    return "".join(escaped_parts)


def format_cell(val: Any, float_format: str) -> str:
    """Format a cell value for LaTeX table display."""
    if val is None or pd.isna(val):
        return "--"
    if isinstance(val, str):
        if not val.strip() or val == "--":
            return "--"
        return escape_latex(val)
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, (int, np.integer)):
        return str(val)
    if isinstance(val, (float, np.floating)):
        try:
            if "%" in float_format:
                return float_format % val
            return float_format.format(val)
        except (ValueError, TypeError):
            return str(val)
    return escape_latex(str(val))


def dataframe_to_latex_table(
    df: pd.DataFrame,
    caption: str,
    label: str,
    float_format: str = "{:.3f}",
    col_align: str | None = None,
) -> str:
    """Convert a DataFrame into a complete publication-ready LaTeX table environment.

    Generates a table environment with booktabs rules (toprule, midrule, bottomrule),
    escapes special characters in text and column headers, formats nulls as '--',
    and preserves TODO(...) markers without alteration.
    """
    if col_align is not None:
        align = col_align
    else:
        align = "".join(
            "r" if pd.api.types.is_numeric_dtype(df[col]) else "l"
            for col in df.columns
        )

    escaped_headers = [escape_latex(str(c)) for c in df.columns]
    header_line = " & ".join(escaped_headers) + r" \\" if escaped_headers else ""

    data_lines: list[str] = []
    for row in df.itertuples(index=False):
        row_cells = [format_cell(v, float_format) for v in row]
        data_lines.append(" & ".join(row_cells) + r" \\")

    lines = [
        r"\begin{table}",
        r"\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{align}}}",
        r"\toprule",
    ]
    if header_line:
        lines.append(header_line)
    lines.append(r"\midrule")
    lines.extend(data_lines)
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def export_analysis_tables(analysis_dir: Path, output_dir: Path) -> list[Path]:
    """Scan analysis directory for standard CSVs and generate LaTeX tables."""
    if not analysis_dir.is_dir():
        raise FileNotFoundError(f"Analysis directory not found: {analysis_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files: list[Path] = []

    for filename, (caption, label) in STANDARD_TABLE_SPECS.items():
        csv_path = analysis_dir / filename
        if csv_path.is_file():
            df = pd.read_csv(csv_path)
            table_latex = dataframe_to_latex_table(df, caption=caption, label=label)
            out_path = output_dir / f"{csv_path.stem}.tex"
            out_path.write_text(table_latex, encoding="utf-8")
            generated_files.append(out_path)

    return generated_files


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert analysis CSV files into publication-ready LaTeX tables."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing analysis CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to write exported LaTeX table files.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for exporting LaTeX tables."""
    args = parse_args(argv)
    if not args.input_dir.is_dir():
        print(f"Input directory does not exist: {args.input_dir}", file=sys.stderr)
        return 1

    export_analysis_tables(args.input_dir, args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
