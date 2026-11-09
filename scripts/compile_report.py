"""Compile research report markdown and LaTeX skeleton for submission."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# LaTeX special character escaping
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
MATH_INLINE_PATTERN = re.compile(r"(\$[^\$]+\$)")
RESULTS_BEGIN_PATTERN = re.compile(r"^<!--\s*RESULTS:BEGIN\s+(\S+)\s*-->$")
RESULTS_END_PATTERN = re.compile(r"^<!--\s*RESULTS:END\s+(\S+)\s*-->$")
TABLE_ROW_PATTERN = re.compile(r"^\s*\|.*\|\s*$")
TABLE_SEP_PATTERN = re.compile(r"^\s*\|[\s\-\:\.\_\|\$\\]+\|\s*$")


@dataclass
class PageBudgetAuditResult:
    """Result of auditing report page budget and required sections."""

    main_body_word_count: int
    main_body_char_count: int
    estimated_pages: float
    min_pages: float = 4.0
    max_pages: float = 8.0
    is_within_budget: bool = False
    has_ethics_appendix: bool = False
    passed: bool = False
    section_breakdown: dict[str, dict[str, Any]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def escape_latex_text(text: str) -> str:
    """Escape LaTeX special characters while preserving math blocks and TODO markers."""
    # Split text by inline math expressions first
    math_parts = MATH_INLINE_PATTERN.split(text)
    escaped_parts: list[str] = []

    for math_part in math_parts:
        if MATH_INLINE_PATTERN.fullmatch(math_part):
            # Inside math formula: preserve intact
            escaped_parts.append(math_part)
        else:
            # Outside math formula: split by TODO markers
            todo_parts = TODO_PATTERN.split(math_part)
            for todo_part in todo_parts:
                if TODO_PATTERN.fullmatch(todo_part):
                    escaped_parts.append(todo_part)
                else:
                    escaped_parts.append(
                        "".join(LATEX_SPECIAL_CHARS.get(ch, ch) for ch in todo_part)
                    )

    return "".join(escaped_parts)


def clean_markdown_for_word_count(markdown_text: str) -> str:
    """Strip markup comments, table syntax, and formatting artifacts for word counting."""
    # Remove HTML and results comments
    text = re.sub(r"<!--.*?-->", " ", markdown_text, flags=re.DOTALL)
    # Remove markdown table separator lines
    text = re.sub(r"\|[\s\-\:\.\_\|\$\\]+\|\s*", " ", text)
    # Replace markdown table pipe boundaries with spaces
    text = re.sub(r"\|", " ", text)
    # Remove markdown link URLs keeping text: [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove image links: ![alt](url) -> ""
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    # Remove headers marker symbols #
    text = re.sub(r"^#+\s*", " ", text, flags=re.MULTILINE)
    # Remove bold and italic markers
    text = re.sub(r"[*_]{1,3}", "", text)
    return text


def extract_main_body(draft_text: str) -> str:
    """Extract report content up to References or first Appendix."""
    # References header or first Appendix header demarcates end of main body
    match = re.search(r"^(?:##\s+References|##\s+Appendix)", draft_text, flags=re.MULTILINE)
    if match:
        return draft_text[: match.start()].strip()
    return draft_text.strip()


def extract_references_section(draft_text: str) -> str:
    """Extract References section from draft text if present."""
    ref_match = re.search(
        r"^##\s+References\b.*?(?=^##\s+Appendix|\Z)",
        draft_text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if ref_match:
        return ref_match.group(0).strip()
    return ""


def extract_appendix_b_from_draft(draft_text: str) -> str:
    """Extract pre-existing work declaration appendix if present in draft."""
    app_b_match = re.search(
        r"^##\s+Appendix\s+B[.:]\s+Pre-existing Work.*?\Z",
        draft_text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if app_b_match:
        return app_b_match.group(0).strip()
    return ""


def format_appendix(title: str, content: str, letter: str) -> str:
    """Format markdown appendix with standard top header and adjusted subsection levels."""
    lines = content.strip().splitlines()
    body_lines: list[str] = []

    # Skip first level-1 header if present
    start_idx = 0
    if lines and lines[0].startswith("# "):
        start_idx = 1

    for line in lines[start_idx:]:
        # Adjust section headers inside appendix
        if line.startswith("### "):
            # Sub-subsection: ### 1.1 Title -> #### <letter>.1.1 Title or #### Title
            sub_title = line[4:].strip()
            # If starts with digits, prefix with letter
            if re.match(r"^\d+\.", sub_title):
                body_lines.append(f"#### {letter}.{sub_title}")
            else:
                body_lines.append(f"#### {sub_title}")
        elif line.startswith("## "):
            # Subsection: ## 1. Title -> ### <letter>.1 Title or ### Title
            sub_title = line[3:].strip()
            if re.match(r"^\d+\.", sub_title):
                body_lines.append(f"### {letter}.{sub_title}")
            else:
                body_lines.append(f"### {sub_title}")
        else:
            body_lines.append(line)

    header = f"## Appendix {letter}: {title}"
    formatted_body = "\n".join(body_lines).strip()
    return f"{header}\n\n{formatted_body}"


def merge_report_sections(
    draft_text: str,
    ethics_text: str,
    repro_text: str,
) -> str:
    """Merge draft sections 1 to 6 with ethics, reproduction guide, and declarations."""
    main_body = extract_main_body(draft_text)
    references = extract_references_section(draft_text)
    appendix_b_draft = extract_appendix_b_from_draft(draft_text)

    # Format ethics appendix as Appendix A
    appendix_a = format_appendix(
        title="Limitations and Dual-Use / Ethical Considerations",
        content=ethics_text,
        letter="A",
    )

    # Format reproduction guide as Appendix B
    appendix_b = format_appendix(
        title="Technical Reproduction Guide",
        content=repro_text,
        letter="B",
    )

    sections: list[str] = [main_body]

    if references:
        sections.append(references)

    sections.append(appendix_a)
    sections.append(appendix_b)

    # If draft contained pre-existing work declaration, retain as Appendix C
    if appendix_b_draft:
        # Re-letter from Appendix B to Appendix C
        relettered = re.sub(
            r"^##\s+Appendix\s+B[.:]\s*",
            "## Appendix C: ",
            appendix_b_draft,
            flags=re.MULTILINE,
        )
        sections.append(relettered)

    return "\n\n---\n\n".join(sections) + "\n"


def audit_page_budget(
    markdown_text: str,
    words_per_page: float = 550.0,
    chars_per_page: float = 3300.0,
) -> PageBudgetAuditResult:
    """Audit report text for page budget constraints and required sections."""
    main_body = extract_main_body(markdown_text)
    clean_main = clean_markdown_for_word_count(main_body)

    words = len(clean_main.split())
    chars = len(clean_main)
    estimated_pages = round(words / words_per_page, 2)

    min_pages = 4.0
    max_pages = 8.0
    is_within_budget = min_pages <= estimated_pages <= max_pages

    # Check for presence of required ethics appendix
    ethics_regex = re.compile(
        r"##\s+Appendix\s+[A-Z]?[:.]?\s*Limitations\s+and\s+Dual-Use",
        re.IGNORECASE,
    )
    has_ethics_appendix = bool(ethics_regex.search(markdown_text))

    errors: list[str] = []
    warnings: list[str] = []

    if estimated_pages < min_pages:
        errors.append(
            f"Main body estimated page count ({estimated_pages:.2f} pages) "
            f"is under minimum limit of {min_pages} pages."
        )
    elif estimated_pages > max_pages:
        errors.append(
            f"Main body estimated page count ({estimated_pages:.2f} pages) "
            f"exceeds hard cap of {max_pages} pages."
        )

    if not has_ethics_appendix:
        errors.append(
            "Required ethics appendix "
            "('Limitations and Dual-Use / Ethical Considerations') is missing."
        )

    passed = is_within_budget and has_ethics_appendix

    # Compute section breakdown
    section_breakdown: dict[str, dict[str, Any]] = {}
    pattern = re.compile(r"^(##\s+[^#\n]+)", re.MULTILINE)
    splits = pattern.split(markdown_text)

    # First block is preamble / title
    if splits and splits[0].strip():
        pre_text = clean_markdown_for_word_count(splits[0])
        pre_words = len(pre_text.split())
        section_breakdown["Title and Preamble"] = {
            "words": pre_words,
            "chars": len(pre_text),
            "estimated_pages": round(pre_words / words_per_page, 2),
        }

    for i in range(1, len(splits), 2):
        sec_header = splits[i].replace("##", "").strip()
        sec_content = splits[i + 1] if i + 1 < len(splits) else ""
        sec_clean = clean_markdown_for_word_count(sec_content)
        sec_words = len(sec_clean.split())
        section_breakdown[sec_header] = {
            "words": sec_words,
            "chars": len(sec_clean),
            "estimated_pages": round(sec_words / words_per_page, 2),
        }

    return PageBudgetAuditResult(
        main_body_word_count=words,
        main_body_char_count=chars,
        estimated_pages=estimated_pages,
        min_pages=min_pages,
        max_pages=max_pages,
        is_within_budget=is_within_budget,
        has_ethics_appendix=has_ethics_appendix,
        passed=passed,
        section_breakdown=section_breakdown,
        warnings=warnings,
        errors=errors,
    )


def update_results_blocks(
    markdown_text: str,
    rendered_blocks: dict[str, str],
) -> str:
    """Update marked results blocks in markdown text with rendered content."""
    lines = markdown_text.splitlines()
    output_lines: list[str] = []
    in_block = False
    current_block_name = ""

    for line in lines:
        begin_match = RESULTS_BEGIN_PATTERN.match(line.strip())
        if begin_match:
            current_block_name = begin_match.group(1)
            in_block = True
            output_lines.append(line)
            if current_block_name in rendered_blocks:
                output_lines.append(rendered_blocks[current_block_name].strip())
            continue

        end_match = RESULTS_END_PATTERN.match(line.strip())
        if end_match:
            end_name = end_match.group(1)
            if in_block and end_name == current_block_name:
                in_block = False
                output_lines.append(line)
                continue

        if not in_block:
            output_lines.append(line)
        elif current_block_name not in rendered_blocks:
            # Preserve existing block content if no replacement provided
            output_lines.append(line)

    return "\n".join(output_lines)


def markdown_table_to_latex(
    table_markdown: str,
    caption: str = "",
    label: str = "",
) -> str:
    """Convert a markdown table string into a LaTeX booktabs table environment."""
    raw_lines = [line.strip() for line in table_markdown.strip().splitlines() if line.strip()]
    table_lines = [line for line in raw_lines if line.startswith("|") and line.endswith("|")]

    if len(table_lines) < 2:
        return table_markdown

    # First row is header
    header_cells = [c.strip() for c in table_lines[0].strip("|").split("|")]
    # Second row is delimiter
    # Data rows follow
    data_rows: list[list[str]] = []
    for line in table_lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        # Pad row with empty cells if necessary
        if len(cells) < len(header_cells):
            cells.extend([""] * (len(header_cells) - len(cells)))
        data_rows.append(cells[: len(header_cells)])

    # Determine column alignment: numeric values right-aligned, otherwise left
    col_aligns: list[str] = []
    for col_idx in range(len(header_cells)):
        col_is_numeric = True
        has_any_val = False
        for row in data_rows:
            val = row[col_idx]
            if val and val != "--" and not val.startswith("TODO"):
                has_any_val = True
                try:
                    float(val.replace("%", "").replace(",", ""))
                except ValueError:
                    col_is_numeric = False
                    break
        col_aligns.append("r" if (has_any_val and col_is_numeric) else "l")

    align_str = "".join(col_aligns)
    escaped_headers = [escape_latex_text(h) for h in header_cells]
    header_line = " & ".join(escaped_headers) + r" \\"

    latex_lines: list[str] = [
        r"\begin{table}[htbp]",
        r"\centering",
    ]
    if caption:
        latex_lines.append(f"\\caption{{{caption}}}")
    if label:
        latex_lines.append(f"\\label{{{label}}}")

    latex_lines.extend([
        f"\\begin{{tabular}}{{{align_str}}}",
        r"\toprule",
        header_line,
        r"\midrule",
    ])

    for row in data_rows:
        escaped_cells = [escape_latex_text(cell) if cell else "--" for cell in row]
        latex_lines.append(" & ".join(escaped_cells) + r" \\")

    latex_lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(latex_lines)


def load_latex_tables_from_dir(tables_dir: Path) -> dict[str, str]:
    """Load all .tex table files from a directory into a dictionary keyed by filename stem."""
    tables: dict[str, str] = {}
    if not tables_dir.is_dir():
        return tables
    for tex_file in tables_dir.glob("*.tex"):
        tables[tex_file.stem] = tex_file.read_text(encoding="utf-8")
    return tables


def _make_replacer(content: str) -> Callable[[re.Match[str]], str]:
    """Return replacement callback for re.sub preserving literal backslashes."""
    cleaned = content.strip()

    def _repl(_m: re.Match[str]) -> str:
        return cleaned

    return _repl


def insert_latex_tables(
    latex_text: str,
    tables: dict[str, str] | Path,
) -> str:
    """Insert rendered LaTeX tables into template placeholders."""
    tables_map: dict[str, str] = (
        load_latex_tables_from_dir(tables) if isinstance(tables, Path) else tables
    )

    result = latex_text
    for name, table_content in tables_map.items():
        replacer = _make_replacer(table_content)
        # Match % TABLE:BEGIN <name> ... % TABLE:END <name>
        pattern_percent = re.compile(
            rf"%\s*TABLE:BEGIN\s+{re.escape(name)}\b.*?%\s*TABLE:END\s+{re.escape(name)}",
            re.DOTALL,
        )
        if pattern_percent.search(result):
            result = pattern_percent.sub(replacer, result)

        # Match <!-- RESULTS:BEGIN <name> --> ... <!-- RESULTS:END <name> -->
        pattern_comment = re.compile(
            rf"<!--\s*RESULTS:BEGIN\s+{re.escape(name)}\s*-->.*?<!--\s*RESULTS:END\s+{re.escape(name)}\s*-->",
            re.DOTALL,
        )
        if pattern_comment.search(result):
            result = pattern_comment.sub(replacer, result)

    return result


def convert_markdown_elements_to_latex(text: str) -> str:
    """Convert common inline and block markdown elements to LaTeX syntax."""
    # Convert bold: **text** -> \textbf{text}
    text = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", text)
    # Convert italic: *text* -> \textit{text}
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\\textit{\1}", text)
    # Convert inline code: `code` -> \texttt{code}
    text = re.sub(r"`([^`]+)`", r"\\texttt{\1}", text)
    return text


def compile_markdown_to_latex(
    markdown_text: str,
    latex_tables: dict[str, str] | Path | None = None,
) -> str:
    """Compile markdown report into a structured LaTeX document skeleton."""
    tables_map: dict[str, str] = {}
    if isinstance(latex_tables, Path):
        tables_map = load_latex_tables_from_dir(latex_tables)
    elif isinstance(latex_tables, dict):
        tables_map = latex_tables

    lines = markdown_text.splitlines()

    title = "Infection Chains in LLM Swarms: Spread, Detection and Layered Gating"
    author = "Author Redacted for Review"
    abstract_lines: list[str] = []
    body_lines: list[str] = []

    in_abstract = False
    in_code_block = False
    in_table_block = False
    in_references = False
    appendix_started = False

    table_block_name = ""
    current_table_lines: list[str] = []
    current_table_caption = ""
    current_table_label = ""
    references_lines: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check for title
        if stripped.startswith("# ") and not stripped.startswith("# Appendix"):
            title = stripped[2:].strip()
            i += 1
            continue

        # Check code blocks
        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                body_lines.append(r"\begin{verbatim}")
            else:
                in_code_block = False
                body_lines.append(r"\end{verbatim}")
            i += 1
            continue

        if in_code_block:
            body_lines.append(line)
            i += 1
            continue

        # Check marked results blocks
        begin_match = RESULTS_BEGIN_PATTERN.match(stripped)
        if begin_match:
            table_block_name = begin_match.group(1)
            in_table_block = True
            current_table_lines = []
            i += 1
            continue

        end_match = RESULTS_END_PATTERN.match(stripped)
        if end_match:
            if in_table_block:
                in_table_block = False
                # If pre-rendered table exists in tables_map, insert it
                if table_block_name in tables_map:
                    body_lines.append(tables_map[table_block_name].strip())
                elif current_table_lines:
                    table_md = "\n".join(current_table_lines)
                    tex_table = markdown_table_to_latex(
                        table_md,
                        caption=current_table_caption,
                        label=current_table_label or f"tab:{table_block_name}",
                    )
                    body_lines.append(tex_table)
                table_block_name = ""
                current_table_lines = []
                current_table_caption = ""
                current_table_label = ""
            i += 1
            continue

        if in_table_block:
            current_table_lines.append(line)
            i += 1
            continue

        # Check Table headings: #### Table <N>: <Caption>
        table_head_match = re.match(r"^####\s+(Table\s+([A-Za-z0-9]+)[:.]?\s*(.*))$", stripped)
        if table_head_match:
            current_table_caption = table_head_match.group(3).strip()
            table_num = table_head_match.group(2).lower()
            current_table_label = f"tab:table_{table_num}"
            i += 1
            continue

        # Abstract section
        if stripped == "## Abstract":
            in_abstract = True
            i += 1
            continue

        if in_abstract:
            if stripped.startswith("## "):
                in_abstract = False
            else:
                if stripped:
                    abstract_lines.append(convert_markdown_elements_to_latex(escape_latex_text(stripped)))
                i += 1
                continue

        # References section
        if stripped.startswith("## References"):
            in_references = True
            i += 1
            continue

        if in_references:
            if stripped.startswith("## Appendix") or stripped.startswith("---"):
                in_references = False
            else:
                if stripped and not stripped.startswith("---"):
                    references_lines.append(stripped)
                i += 1
                continue

        # Appendix headers
        if stripped.startswith("## Appendix"):
            if not appendix_started:
                body_lines.append(r"\appendix")
                appendix_started = True

            app_title_match = re.match(
                r"^##\s+Appendix\s+[A-Za-z0-9]+[.:]?\s*(.*)$", stripped
            )
            app_title = (
                app_title_match.group(1).strip()
                if app_title_match
                else stripped[11:].strip()
            )
            body_lines.append(f"\\section{{{escape_latex_text(app_title)}}}")
            i += 1
            continue

        # Subsections inside appendix or main text
        if stripped.startswith("### "):
            sub_title_raw = stripped[4:].strip()
            # Clean numbered prefix e.g. 1.1 Title -> Title
            sub_title = re.sub(r"^[A-Za-z0-9.]+[:\s]+", "", sub_title_raw)
            body_lines.append(f"\\subsection{{{escape_latex_text(sub_title)}}}")
            i += 1
            continue

        if stripped.startswith("#### "):
            subsub_title_raw = stripped[5:].strip()
            subsub_title = re.sub(r"^[A-Za-z0-9.]+[:\s]+", "", subsub_title_raw)
            body_lines.append(f"\\subsubsection{{{escape_latex_text(subsub_title)}}}")
            i += 1
            continue

        # Section headers in main text: ## 1. Introduction -> \section{Introduction}
        if stripped.startswith("## "):
            sec_title_raw = stripped[3:].strip()
            sec_title = re.sub(r"^\d+[\.\s]+", "", sec_title_raw)
            body_lines.append(f"\\section{{{escape_latex_text(sec_title)}}}")
            i += 1
            continue

        # Skip horizontal rules
        if stripped == "---":
            i += 1
            continue

        # Standard paragraph text
        if stripped:
            converted_line = convert_markdown_elements_to_latex(escape_latex_text(line))
            body_lines.append(converted_line)
        else:
            body_lines.append("")

        i += 1

    # Format bibliography
    bib_entries: list[str] = []
    if references_lines:
        bib_entries.append(r"\begin{thebibliography}{99}")
        for ref_idx, ref_line in enumerate(references_lines, start=1):
            ref_clean = re.sub(r"^\d+[\.\s]+", "", ref_line.strip())
            if ref_clean:
                converted_ref = convert_markdown_elements_to_latex(escape_latex_text(ref_clean))
                bib_entries.append(f"\\bibitem{{ref{ref_idx}}} {converted_ref}")
        bib_entries.append(r"\end{thebibliography}")

    latex_doc: list[str] = [
        r"\documentclass[11pt,a4paper]{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage{amsmath,amssymb,amsfonts}",
        r"\usepackage{booktabs}",
        r"\usepackage{hyperref}",
        r"\usepackage{graphicx}",
        r"\usepackage{geometry}",
        r"\geometry{margin=1in}",
        r"\usepackage{cite}",
        "",
        f"\\title{{{escape_latex_text(title)}}}",
        f"\\author{{{escape_latex_text(author)}}}",
        r"\date{\today}",
        "",
        r"\begin{document}",
        r"\maketitle",
        "",
    ]

    if abstract_lines:
        latex_doc.extend([
            r"\begin{abstract}",
            "\n".join(abstract_lines),
            r"\end{abstract}",
            "",
        ])

    latex_doc.extend(body_lines)

    if bib_entries:
        latex_doc.append("")
        latex_doc.extend(bib_entries)

    latex_doc.extend([
        "",
        r"\end{document}",
        "",
    ])

    return "\n".join(latex_doc)


def compile_report(
    draft_path: Path,
    ethics_path: Path,
    repro_path: Path,
    output_markdown_path: Path | None = None,
    output_latex_path: Path | None = None,
    latex_tables: dict[str, str] | Path | None = None,
    rendered_blocks: dict[str, str] | None = None,
    words_per_page: float = 550.0,
) -> tuple[str, str, PageBudgetAuditResult]:
    """Compile final markdown report and LaTeX skeleton from component documents."""
    draft_text = draft_path.read_text(encoding="utf-8")
    ethics_text = ethics_path.read_text(encoding="utf-8")
    repro_text = repro_path.read_text(encoding="utf-8")

    # Step 1: Merge sections
    merged_markdown = merge_report_sections(
        draft_text=draft_text,
        ethics_text=ethics_text,
        repro_text=repro_text,
    )

    # Step 2: Update marked results blocks if provided
    if rendered_blocks:
        merged_markdown = update_results_blocks(merged_markdown, rendered_blocks)

    # Step 3: Run page budget and required section audit
    audit = audit_page_budget(merged_markdown, words_per_page=words_per_page)

    # Step 4: Write compiled markdown output
    if output_markdown_path is not None:
        output_markdown_path.parent.mkdir(parents=True, exist_ok=True)
        output_markdown_path.write_text(merged_markdown, encoding="utf-8")

    # Step 5: Compile LaTeX skeleton
    latex_skeleton = compile_markdown_to_latex(
        merged_markdown,
        latex_tables=latex_tables,
    )

    if output_latex_path is not None:
        output_latex_path.parent.mkdir(parents=True, exist_ok=True)
        output_latex_path.write_text(latex_skeleton, encoding="utf-8")

    return merged_markdown, latex_skeleton, audit


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Compile research report and LaTeX skeleton from component documents."
    )
    parser.add_argument(
        "--draft",
        type=Path,
        default=Path("report/DRAFT_REPORT.md"),
        help="Path to draft report markdown.",
    )
    parser.add_argument(
        "--ethics",
        type=Path,
        default=Path("report/LIMITATIONS_AND_ETHICS.md"),
        help="Path to limitations and ethics appendix markdown.",
    )
    parser.add_argument(
        "--repro",
        type=Path,
        default=Path("report/REPRODUCTION_GUIDE.md"),
        help="Path to reproduction guide appendix markdown.",
    )
    parser.add_argument(
        "--output-markdown",
        type=Path,
        default=Path("report/FINAL_REPORT.md"),
        help="Output path for compiled final markdown report.",
    )
    parser.add_argument(
        "--output-latex",
        type=Path,
        default=Path("report/paper.tex"),
        help="Output path for compiled LaTeX skeleton.",
    )
    parser.add_argument(
        "--tables-dir",
        type=Path,
        default=None,
        help="Directory containing rendered .tex table files to insert.",
    )
    parser.add_argument(
        "--words-per-page",
        type=float,
        default=550.0,
        help="Words per page for page budget calculation (default: 550.0).",
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Run page budget audit without writing compiled files.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify page budget within 4-8 pages and ethics appendix present.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for compiling report."""
    args = parse_args(argv)

    if not args.draft.is_file():
        print(f"Draft file not found: {args.draft}", file=sys.stderr)
        return 1
    if not args.ethics.is_file():
        print(f"Ethics appendix file not found: {args.ethics}", file=sys.stderr)
        return 1
    if not args.repro.is_file():
        print(f"Reproduction guide file not found: {args.repro}", file=sys.stderr)
        return 1

    if args.audit_only:
        draft_text = args.draft.read_text(encoding="utf-8")
        ethics_text = args.ethics.read_text(encoding="utf-8")
        repro_text = args.repro.read_text(encoding="utf-8")
        merged = merge_report_sections(draft_text, ethics_text, repro_text)
        audit = audit_page_budget(merged, words_per_page=args.words_per_page)
    else:
        _, _, audit = compile_report(
            draft_path=args.draft,
            ethics_path=args.ethics,
            repro_path=args.repro,
            output_markdown_path=args.output_markdown,
            output_latex_path=args.output_latex,
            latex_tables=args.tables_dir,
            words_per_page=args.words_per_page,
        )

    # Print audit summary
    print("Page Budget Audit Summary:")
    print(f"- Main body words: {audit.main_body_word_count}")
    print(f"- Main body characters: {audit.main_body_char_count}")
    print(
        f"- Estimated pages: {audit.estimated_pages:.2f} "
        f"(budget: {audit.min_pages} to {audit.max_pages})"
    )
    print(f"- Within page budget: {audit.is_within_budget}")
    print(f"- Ethics appendix included: {audit.has_ethics_appendix}")
    print(f"- Overall status: {'PASSED' if audit.passed else 'FAILED'}")

    if audit.errors:
        print("\nAudit Errors:")
        for err in audit.errors:
            print(f"  * {err}")

    if not args.audit_only:
        print(f"\nCompiled markdown written to: {args.output_markdown}")
        print(f"Compiled LaTeX skeleton written to: {args.output_latex}")

    if args.check and not audit.passed:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
