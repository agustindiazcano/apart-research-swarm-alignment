"""Standalone submission PDF exporter and page count verifier.

Renders research report markdown documents and figures into a publication formatted
PDF document using matplotlib.backends.backend_pdf.PdfPages and audits the 4 to 8 page
hard cap for the main body.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import matplotlib

# Set non-interactive Agg backend to support headless execution on all platforms
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# Mathematical symbol conversions from LaTeX markup to plain text unicode
LATEX_REPLACEMENTS: list[tuple[str, str]] = [
    (r"\\operatorname\{([^\}]+)\}", r"\1"),
    (r"\\mathbb\{I\}", "I"),
    (r"\\mathbb\{([^\}]+)\}", r"\1"),
    (r"\\mathbf\{([^\}]+)\}", r"\1"),
    (r"\\text\{([^\}]+)\}", r"\1"),
    (r"\\mathcal\{N\}", "N"),
    (r"\\tilde\{S\}", "S_tilde"),
    (r"\\ge\b", "≥"),
    (r"\\geq\b", "≥"),
    (r"\\le\b", "≤"),
    (r"\\leq\b", "≤"),
    (r"\\neq\b", "≠"),
    (r"\\in\b", "∈"),
    (r"\\to\b", "→"),
    (r"\\cdot\b", "·"),
    (r"\\sum\b", "∑"),
    (r"\\prod\b", "∏"),
    (r"\\dots\b", "…"),
    (r"\\quad\b", "  "),
    (r"\\lambda\b", "λ"),
    (r"\\beta\b", "β"),
    (r"\\tau\b", "τ"),
    (r"\\gamma\b", "γ"),
    (r"\\alpha\b", "α"),
    (r"\\mathbf", ""),
    (r"\\left\(", "("),
    (r"\\right\)", ")"),
    (r"\\{", "{"),
    (r"\\}", "}"),
    (r"\\_", "_"),
    (r"\^T", "ᵀ"),
    (r"_0", "₀"),
    (r"_1", "₁"),
    (r"_2", "₂"),
    (r"_3", "₃"),
    (r"_4", "₄"),
    (r"_5", "₅"),
]

HTML_COMMENT_PATTERN = re.compile(r"<!--[\s\S]*?-->")
MATH_INLINE_PATTERN = re.compile(r"\$([^$]+)\$")
FRAC_PATTERN = re.compile(r"\\frac\{([^\}]+)\}\{([^\}]+)\}")


SUB = str.maketrans("0123456789+-=()aehiklmnoprstuvx", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢₖₗₘₙₒₚᵣₛₜᵤᵥₓ")
DISPLAY_MATH_PATTERN = re.compile(r"\$\$([\s\S]+?)\$\$")


def _subscript(m: re.Match[str]) -> str:
    inner = m.group(1) if m.group(1) is not None else m.group(2)
    if all(ch in "0123456789+-=()aehiklmnoprstuvx" for ch in inner):
        return inner.translate(SUB)
    return "_" + inner


def _convert_math(s: str) -> str:
    s = FRAC_PATTERN.sub(lambda m: f"({m.group(1)}) / ({m.group(2)})", s)
    s = re.sub(r"\\tilde\{([^\}]+)\}", lambda m: m.group(1) + "\u0303", s)
    s = re.sub(r"\\pmod\s*(\w+)", r"mod \1", s)
    s = re.sub(r"\\(exp|max|log)\b", r"\1", s)
    for pat, repl in LATEX_REPLACEMENTS:
        s = re.sub(pat, repl, s)
    s = re.sub(r"_\{([^\}]*)\}|_([0-9a-z])", _subscript, s)
    s = re.sub(r"\^\{([^\}]*)\}", r"^\1", s)
    s = s.replace(r"\ ", " ").replace("\\", "")
    s = s.replace("{", "").replace("}", "")
    return s


def sanitize_markdown_text(text: str) -> str:
    """Sanitize LaTeX math markup, HTML comments and inline Markdown into plain typography."""
    cleaned = HTML_COMMENT_PATTERN.sub("", text)
    cleaned = DISPLAY_MATH_PATTERN.sub(lambda m: _convert_math(m.group(1)), cleaned)
    cleaned = MATH_INLINE_PATTERN.sub(lambda m: _convert_math(m.group(1)), cleaned)
    cleaned = cleaned.replace("**", "").replace("`", "")
    cleaned = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"\1", cleaned)
    return cleaned


def _strip_marker(item: str) -> str:
    """Drop a leading Markdown bullet or number; the renderer draws its own bullet."""
    return re.sub(r"^\s*([*\-]|\d+\.)\s+", "", item)


@dataclass
class LayoutBlock:
    """Structured representation of a document block for layout and pagination."""

    kind: str
    text: str = ""
    lines: list[str] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    image_path: Path | None = None
    caption: str = ""
    section_type: str = "main_body"  # "main_body", "references", "appendix"
    page_break_before: bool = False


def parse_markdown_blocks(
    text: str,
    figures_dir: Path | None = None,
) -> list[LayoutBlock]:
    """Parse markdown document text into structured layout blocks."""
    blocks: list[LayoutBlock] = []
    lines = text.splitlines()
    i = 0
    current_section = "main_body"
    added_central_fig = False
    added_kinetics_fig = False

    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.strip()

        # HTML comments
        if line.startswith("<!--") and line.endswith("-->"):
            i += 1
            continue

        # Blank line
        if not line:
            i += 1
            continue

        # Code block
        if line.startswith("```"):
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            blocks.append(
                LayoutBlock(
                    kind="code",
                    lines=code_lines,
                    section_type=current_section,
                )
            )
            continue

        # Markdown Table
        if line.startswith("|") and line.endswith("|"):
            table_raw: list[str] = [line]
            i += 1
            while (
                i < len(lines)
                and lines[i].strip().startswith("|")
                and lines[i].strip().endswith("|")
            ):
                table_raw.append(lines[i].strip())
                i += 1

            headers: list[str] = []
            rows: list[list[str]] = []
            for row_idx, r_str in enumerate(table_raw):
                cells = [c.strip() for c in r_str.strip("|").split("|")]
                # Skip separator line |---|---|
                if row_idx == 1 and all(set(c).issubset({"-", ":", " "}) for c in cells):
                    continue
                cleaned_cells = [sanitize_markdown_text(c) for c in cells]
                if not headers:
                    headers = cleaned_cells
                else:
                    rows.append(cleaned_cells)

            blocks.append(
                LayoutBlock(
                    kind="table",
                    headers=headers,
                    rows=rows,
                    section_type=current_section,
                )
            )
            continue

        # Document Title (H1)
        if raw_line.startswith("# "):
            title_text = sanitize_markdown_text(raw_line[2:].strip())
            blocks.append(
                LayoutBlock(
                    kind="h1",
                    text=title_text,
                    section_type=current_section,
                )
            )
            i += 1
            # Check for author / affiliation metadata block immediately following title
            meta_lines: list[str] = []
            while (
                i < len(lines)
                and lines[i].strip()
                and not lines[i].strip().startswith("#")
                and lines[i].strip() not in ("---", "***")
            ):
                meta_lines.append(sanitize_markdown_text(lines[i].strip()))
                i += 1
            if meta_lines:
                blocks.append(
                    LayoutBlock(
                        kind="meta",
                        lines=meta_lines,
                        section_type=current_section,
                    )
                )
            continue

        # Horizontal Rule
        if line in ("---", "***", "___"):
            blocks.append(
                LayoutBlock(
                    kind="hr",
                    section_type=current_section,
                )
            )
            i += 1
            continue

        # Section Heading (H2)
        if raw_line.startswith("## "):
            h2_text = sanitize_markdown_text(raw_line[3:].strip())
            break_page = False
            if "References" in h2_text:
                current_section = "references"
                break_page = True
            elif "Appendix" in h2_text:
                current_section = "appendix"
                break_page = True

            blocks.append(
                LayoutBlock(
                    kind="h2",
                    text=h2_text,
                    section_type=current_section,
                    page_break_before=break_page,
                )
            )
            i += 1

            # Check if central figure should be inserted under Section 2
            if (
                figures_dir
                and not added_central_fig
                and "2. Threat Model" in h2_text
                and (figures_dir / "central.png").exists()
            ):
                caption_text = (
                    "Figure 1: Swarm testbed architecture and "
                    "split canary credential threat model."
                )
                blocks.append(
                    LayoutBlock(
                        kind="figure",
                        image_path=figures_dir / "central.png",
                        caption=caption_text,
                        section_type=current_section,
                    )
                )
                added_central_fig = True
            continue

        # Subsection Heading (H3)
        if raw_line.startswith("### "):
            h3_text = sanitize_markdown_text(raw_line[4:].strip())
            blocks.append(
                LayoutBlock(
                    kind="h3",
                    text=h3_text,
                    section_type=current_section,
                )
            )
            i += 1

            # Check if kinetics figure should be inserted under Section 6.1
            if (
                figures_dir
                and not added_kinetics_fig
                and "6.1 Free-Flow Contagion Kinetics" in h3_text
                and (figures_dir / "kinetics.png").exists()
            ):
                caption_text = (
                    "Figure 2: Empirical contagion transmission kinetics "
                    "and reproduction metrics across network topologies."
                )
                blocks.append(
                    LayoutBlock(
                        kind="figure",
                        image_path=figures_dir / "kinetics.png",
                        caption=caption_text,
                        section_type=current_section,
                    )
                )
                added_kinetics_fig = True
            continue

        # Sub-subsection Heading (H4)
        if raw_line.startswith("#### "):
            h4_text = sanitize_markdown_text(raw_line[5:].strip())
            blocks.append(
                LayoutBlock(
                    kind="h4",
                    text=h4_text,
                    section_type=current_section,
                )
            )
            i += 1
            continue

        # Bullet List or Numbered List
        if re.match(r"^\s*([*\-]|\d+\.)\s+", raw_line):
            list_items: list[str] = [_strip_marker(sanitize_markdown_text(raw_line))]
            i += 1
            while i < len(lines) and (
                re.match(r"^\s*([*\-]|\d+\.)\s+", lines[i])
                or (lines[i].startswith("  ") and lines[i].strip())
            ):
                list_items.append(_strip_marker(sanitize_markdown_text(lines[i])))
                i += 1
            blocks.append(
                LayoutBlock(
                    kind="list",
                    lines=list_items,
                    section_type=current_section,
                )
            )
            continue

        # Paragraph
        para_parts: list[str] = [raw_line.strip()]
        i += 1
        while (
            i < len(lines)
            and lines[i].strip()
            and not lines[i].startswith("#")
            and not lines[i].strip().startswith("|")
            and not lines[i].strip().startswith("```")
            and lines[i].strip() not in ("---", "***")
            and not re.match(r"^\s*([*\-]|\d+\.)\s+", lines[i])
        ):
            para_parts.append(lines[i].strip())
            i += 1

        full_para = sanitize_markdown_text(" ".join(para_parts))
        blocks.append(
            LayoutBlock(
                kind="para",
                text=full_para,
                section_type=current_section,
            )
        )

    return blocks


def compile_report_sources(
    main_report_path: Path,
    ethics_path: Path | None = None,
    reproduction_path: Path | None = None,
) -> str:
    """Compile main report markdown with ethics and reproduction appendices."""
    main_text = main_report_path.read_text(encoding="utf-8")

    # If no separate appendix files provided, return main text as is
    if ethics_path is None and reproduction_path is None:
        return main_text

    # Extract main body up to references
    if "## References" in main_text:
        main_body, remainder = main_text.split("## References", 1)
        after_references = "## References" + remainder
    else:
        main_body = main_text
        after_references = ""

    # Extract references section
    if "## Appendix" in after_references:
        references_text, app_remainder = after_references.split("## Appendix", 1)
        preexisting_text = ""
        # Locate pre-existing work section
        for part in ("## Appendix" + app_remainder).split("## Appendix"):
            if "Pre-existing Work" in part:
                appendix_title = "## Appendix B. Pre-existing Work vs Sprint Work Declaration"
                preexisting_text = f"{appendix_title}\n\n{part.split(chr(10), 1)[1].strip()}"
                break
    else:
        references_text = after_references.strip()
        preexisting_text = ""

    compiled_parts: list[str] = [main_body.strip(), references_text.strip()]

    # Append Ethics appendix as Appendix A
    if ethics_path and ethics_path.exists():
        raw_ethics = ethics_path.read_text(encoding="utf-8")
        clean_ethics = re.sub(r"^#\s+[^\n]*\n", "", raw_ethics).strip()
        compiled_parts.append(
            f"## Appendix A. Limitations and Dual-Use / Ethical Considerations\n\n{clean_ethics}"
        )

    # Append Pre-existing work as Appendix B
    if preexisting_text:
        compiled_parts.append(preexisting_text)

    # Append Reproduction guide as Appendix C
    if reproduction_path and reproduction_path.exists():
        raw_repro = reproduction_path.read_text(encoding="utf-8")
        clean_repro = re.sub(r"^#\s+[^\n]*\n", "", raw_repro).strip()
        compiled_parts.append(f"## Appendix C. Reproduction Guide\n\n{clean_repro}")

    return "\n\n---\n\n".join(compiled_parts)


class PDFReportBuilder:
    """Multi-page academic report layout engine producing deterministic PDF documents."""

    def __init__(
        self,
        page_width: float = 8.27,
        page_height: float = 11.69,
        margin_x: float = 0.65,
        margin_y: float = 0.65,
        figures_dir: Path | None = None,
    ) -> None:
        self.page_width = page_width
        self.page_height = page_height
        self.margin_x = margin_x
        self.margin_y = margin_y
        self.usable_width = page_width - 2 * margin_x
        self.usable_height = page_height - 2 * margin_y
        self.y_top = page_height - margin_y
        self.y_bottom = margin_y
        self.figures_dir = figures_dir

    def build(
        self,
        markdown_text: str,
        output_pdf_path: Path,
        audit_json_path: Path | None = None,
    ) -> dict[str, Any]:
        """Render markdown blocks to multi-page PDF and generate page audit report."""
        blocks = parse_markdown_blocks(markdown_text, figures_dir=self.figures_dir)
        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

        pages_data: list[list[dict[str, Any]]] = []
        page_sections: list[str] = []

        current_items: list[dict[str, Any]] = []
        current_y = self.y_top
        current_section = "main_body"

        def _finish_page() -> None:
            nonlocal current_items, current_y
            if current_items:
                pages_data.append(current_items)
                page_sections.append(current_section)
                current_items = []
                current_y = self.y_top

        for b_idx, b in enumerate(blocks):
            # Check for explicit section breaks
            if b.page_break_before and current_items:
                _finish_page()

            current_section = b.section_type

            if b.kind == "h1":
                wrapped = textwrap.wrap(b.text, width=54)
                h1_h = len(wrapped) * 0.28 + 0.12
                if current_y - h1_h < self.y_bottom and current_items:
                    _finish_page()
                current_items.append(
                    {"type": "h1", "lines": wrapped, "y": current_y, "height": h1_h}
                )
                current_y -= h1_h

            elif b.kind == "meta":
                meta_h = len(b.lines) * 0.14 + 0.10
                if current_y - meta_h < self.y_bottom and current_items:
                    _finish_page()
                current_items.append(
                    {"type": "meta", "lines": b.lines, "y": current_y, "height": meta_h}
                )
                current_y -= meta_h

            elif b.kind == "hr":
                hr_h = 0.08
                if current_y - hr_h < self.y_bottom and current_items:
                    _finish_page()
                current_items.append({"type": "hr", "y": current_y, "height": hr_h})
                current_y -= hr_h

            elif b.kind == "h2":
                h2_h = 0.30
                if current_y - h2_h < self.y_bottom and current_items:
                    _finish_page()
                current_items.append(
                    {"type": "h2", "text": b.text, "y": current_y, "height": h2_h}
                )
                current_y -= h2_h

            elif b.kind == "h3":
                h3_h = 0.24
                if current_y - h3_h < self.y_bottom and current_items:
                    _finish_page()
                current_items.append(
                    {"type": "h3", "text": b.text, "y": current_y, "height": h3_h}
                )
                current_y -= h3_h

            elif b.kind == "h4":
                h4_h = 0.20
                keep_h = h4_h
                nxt = blocks[b_idx + 1] if b_idx + 1 < len(blocks) else None
                if nxt is not None and nxt.kind == "table":
                    # Keep a table caption on the same page as its table.
                    keep_h += 0.30 + len(nxt.rows) * 0.18 + 0.08
                if current_y - keep_h < self.y_bottom and current_items:
                    _finish_page()
                current_items.append(
                    {"type": "h4", "text": b.text, "y": current_y, "height": h4_h}
                )
                current_y -= h4_h

            elif b.kind == "para":
                wrapped_lines = textwrap.wrap(b.text, width=98)
                line_h = 0.140
                gap = 0.05
                i_line = 0
                while i_line < len(wrapped_lines):
                    remaining_space = current_y - self.y_bottom
                    lines_fit = int(remaining_space // line_h)
                    if lines_fit <= 0:
                        _finish_page()
                        continue
                    chunk = wrapped_lines[i_line : i_line + lines_fit]
                    is_last_chunk = (i_line + lines_fit) >= len(wrapped_lines)
                    chunk_h = len(chunk) * line_h + (gap if is_last_chunk else 0.0)
                    current_items.append(
                        {
                            "type": "para_lines",
                            "lines": chunk,
                            "y": current_y,
                            "height": chunk_h,
                        }
                    )
                    current_y -= chunk_h
                    i_line += len(chunk)

            elif b.kind == "list":
                line_h = 0.140
                for item in b.lines:
                    wrapped_item = textwrap.wrap(item, width=94)
                    i_l = 0
                    while i_l < len(wrapped_item):
                        remaining_space = current_y - self.y_bottom
                        lines_fit = int(remaining_space // line_h)
                        if lines_fit <= 0:
                            _finish_page()
                            continue
                        chunk = wrapped_item[i_l : i_l + lines_fit]
                        chunk_h = len(chunk) * line_h + 0.02
                        current_items.append(
                            {
                                "type": "list_item",
                                "lines": chunk,
                                "is_first": (i_l == 0),
                                "y": current_y,
                                "height": chunk_h,
                            }
                        )
                        current_y -= chunk_h
                        i_l += len(chunk)
                current_y -= 0.04

            elif b.kind == "code":
                code_line_h = 0.125
                code_h = len(b.lines) * code_line_h + 0.08
                if current_y - code_h < self.y_bottom and current_items:
                    _finish_page()
                current_items.append(
                    {"type": "code", "lines": b.lines, "y": current_y, "height": code_h}
                )
                current_y -= code_h

            elif b.kind == "table":
                # Compute table height
                header_h = 0.30
                row_h = 0.18
                table_h = header_h + len(b.rows) * row_h + 0.08
                if current_y - table_h < self.y_bottom and current_items:
                    _finish_page()
                current_items.append(
                    {
                        "type": "table",
                        "headers": b.headers,
                        "rows": b.rows,
                        "y": current_y,
                        "height": table_h,
                    }
                )
                current_y -= table_h

            elif b.kind == "figure":
                fig_h = 2.40
                if current_y - fig_h < self.y_bottom and current_items:
                    _finish_page()
                current_items.append(
                    {
                        "type": "figure",
                        "image_path": b.image_path,
                        "caption": b.caption,
                        "y": current_y,
                        "height": fig_h,
                    }
                )
                current_y -= fig_h

        # Final page
        _finish_page()

        total_pages = len(pages_data)

        # Audit page counts
        # Identify main body pages, references start page, and appendix start page
        main_body_count = 0
        ref_start_page = 0
        app_start_page = 0

        for p_idx, s_type in enumerate(page_sections, 1):
            if s_type == "main_body":
                main_body_count = p_idx
            elif s_type == "references" and ref_start_page == 0:
                ref_start_page = p_idx
            elif s_type == "appendix" and app_start_page == 0:
                app_start_page = p_idx

        # If references or appendix was not found, set defaults based on count
        if ref_start_page == 0:
            ref_start_page = main_body_count + 1
        if app_start_page == 0:
            app_start_page = ref_start_page + 1

        within_cap = 4 <= main_body_count <= 8

        audit_data: dict[str, Any] = {
            "total_pages": total_pages,
            "main_body_pages": main_body_count,
            "references_start_page": ref_start_page,
            "appendix_start_page": app_start_page,
            "within_4_to_8_page_cap": within_cap,
        }

        # Write PDF using PdfPages
        with PdfPages(output_pdf_path) as pdf:
            for p_num, items in enumerate(pages_data, 1):
                fig = plt.figure(figsize=(self.page_width, self.page_height), dpi=300)
                ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
                ax.axis("off")
                ax.set_xlim(0, self.page_width)
                ax.set_ylim(0, self.page_height)

                # Running header on pages 2 and later
                if p_num > 1:
                    ax.text(
                        self.margin_x,
                        self.page_height - 0.45,
                        "Infection Chains in LLM Swarms: Spread, Detection and Layered Gating",
                        fontsize=7.5,
                        fontstyle="italic",
                        color="#666666",
                        va="bottom",
                    )
                    ax.plot(
                        [self.margin_x, self.page_width - self.margin_x],
                        [self.page_height - 0.48, self.page_height - 0.48],
                        color="#dddddd",
                        linewidth=0.5,
                    )

                # Running footer on all pages
                ax.plot(
                    [self.margin_x, self.page_width - self.margin_x],
                    [0.52, 0.52],
                    color="#dddddd",
                    linewidth=0.5,
                )
                ax.text(
                    self.page_width / 2,
                    0.38,
                    f"Page {p_num} of {total_pages}",
                    fontsize=8.0,
                    color="#444444",
                    ha="center",
                    va="top",
                )

                # Render page elements
                for it in items:
                    it_type = it["type"]
                    it_y = it["y"]

                    if it_type == "h1":
                        curr_y = it_y
                        for line in it["lines"]:
                            ax.text(
                                self.margin_x,
                                curr_y,
                                line,
                                fontsize=15.0,
                                fontweight="bold",
                                color="#111111",
                                va="top",
                            )
                            curr_y -= 0.28

                    elif it_type == "meta":
                        curr_y = it_y
                        for line in it["lines"]:
                            ax.text(
                                self.margin_x,
                                curr_y,
                                line,
                                fontsize=8.5,
                                fontstyle="italic",
                                color="#333333",
                                va="top",
                            )
                            curr_y -= 0.14

                    elif it_type == "hr":
                        ax.plot(
                            [self.margin_x, self.page_width - self.margin_x],
                            [it_y - 0.04, it_y - 0.04],
                            color="#cccccc",
                            linewidth=0.5,
                        )

                    elif it_type == "h2":
                        ax.text(
                            self.margin_x,
                            it_y,
                            it["text"],
                            fontsize=11.5,
                            fontweight="bold",
                            color="#111111",
                            va="top",
                        )
                        ax.plot(
                            [self.margin_x, self.page_width - self.margin_x],
                            [it_y - 0.18, it_y - 0.18],
                            color="#222222",
                            linewidth=0.75,
                        )

                    elif it_type == "h3":
                        ax.text(
                            self.margin_x,
                            it_y,
                            it["text"],
                            fontsize=9.5,
                            fontweight="bold",
                            color="#222222",
                            va="top",
                        )

                    elif it_type == "h4":
                        ax.text(
                            self.margin_x,
                            it_y,
                            it["text"],
                            fontsize=8.5,
                            fontweight="bold",
                            color="#333333",
                            va="top",
                        )

                    elif it_type == "para_lines":
                        curr_y = it_y
                        for line in it["lines"]:
                            ax.text(
                                self.margin_x,
                                curr_y,
                                line,
                                fontsize=8.5,
                                color="#222222",
                                va="top",
                            )
                            curr_y -= 0.140

                    elif it_type == "list_item":
                        curr_y = it_y
                        for l_idx, line in enumerate(it["lines"]):
                            if l_idx == 0 and it["is_first"]:
                                ax.text(
                                    self.margin_x,
                                    curr_y,
                                    "•",
                                    fontsize=8.5,
                                    color="#222222",
                                    va="top",
                                )
                            ax.text(
                                self.margin_x + 0.15,
                                curr_y,
                                line,
                                fontsize=8.5,
                                color="#222222",
                                va="top",
                            )
                            curr_y -= 0.140

                    elif it_type == "code":
                        bg_rect = plt.Rectangle(
                            (self.margin_x, it_y - it["height"]),
                            self.usable_width,
                            it["height"],
                            facecolor="#f7f7f7",
                            edgecolor="#e2e2e2",
                            linewidth=0.5,
                        )
                        ax.add_patch(bg_rect)
                        curr_y = it_y - 0.04
                        for line in it["lines"]:
                            ax.text(
                                self.margin_x + 0.08,
                                curr_y,
                                line,
                                fontsize=7.5,
                                fontfamily="monospace",
                                color="#222222",
                                va="top",
                            )
                            curr_y -= 0.125

                    elif it_type == "table":
                        headers = it["headers"]
                        rows = it["rows"]

                        # Calculate proportional column widths
                        max_lens = [len(h) for h in headers]
                        for r in rows:
                            for c_i, c_val in enumerate(r):
                                if c_i < len(max_lens):
                                    max_lens[c_i] = max(max_lens[c_i], len(c_val))
                                else:
                                    max_lens.append(len(c_val))

                        total_len = sum(max_lens) if sum(max_lens) > 0 else 1
                        col_widths = [(ml / total_len) * self.usable_width for ml in max_lens]
                        # Ensure reasonable min width
                        col_widths = [max(cw, 0.6) for cw in col_widths]
                        scale = self.usable_width / sum(col_widths)
                        col_widths = [cw * scale for cw in col_widths]

                        tab_y = it_y
                        header_h = 0.28
                        row_h = 0.18

                        # Header top rule
                        ax.plot(
                            [self.margin_x, self.margin_x + self.usable_width],
                            [tab_y, tab_y],
                            color="#222222",
                            linewidth=1.0,
                        )

                        # Header cells
                        cx = self.margin_x
                        for c_i, h_text in enumerate(headers):
                            cw = col_widths[c_i] if c_i < len(col_widths) else 0.5
                            wrap_w = max(int(cw / 0.065), 5)
                            wrapped_h = textwrap.fill(h_text.replace('_', ' '), width=wrap_w)
                            ax.text(
                                cx + 0.03,
                                tab_y - 0.04,
                                wrapped_h,
                                fontsize=6.8,
                                fontweight="bold",
                                color="#111111",
                                va="top",
                            )
                            cx += cw

                        tab_y -= header_h
                        # Header bottom rule
                        ax.plot(
                            [self.margin_x, self.margin_x + self.usable_width],
                            [tab_y, tab_y],
                            color="#444444",
                            linewidth=0.75,
                        )

                        # Data rows
                        for r_idx, r_vals in enumerate(rows):
                            # Shading for alternating rows
                            if r_idx % 2 == 1:
                                r_rect = plt.Rectangle(
                                    (self.margin_x, tab_y - row_h),
                                    self.usable_width,
                                    row_h,
                                    facecolor="#fafafa",
                                    edgecolor="none",
                                )
                                ax.add_patch(r_rect)

                            cx = self.margin_x
                            for c_i, val in enumerate(r_vals):
                                cw = col_widths[c_i] if c_i < len(col_widths) else 0.5
                                wrap_w = max(int(cw / 0.060), 5)
                                wrapped_val = textwrap.fill(val, width=wrap_w)
                                ax.text(
                                    cx + 0.03,
                                    tab_y - 0.03,
                                    wrapped_val,
                                    fontsize=6.8,
                                    color="#222222",
                                    va="top",
                                )
                                cx += cw
                            tab_y -= row_h

                        # Table bottom rule
                        ax.plot(
                            [self.margin_x, self.margin_x + self.usable_width],
                            [tab_y, tab_y],
                            color="#222222",
                            linewidth=1.0,
                        )

                    elif it_type == "figure":
                        img_path = it["image_path"]
                        if img_path and Path(img_path).exists():
                            img_data = plt.imread(str(img_path))
                            img_w = self.usable_width * 0.85
                            img_h = 1.90
                            img_x = self.margin_x + (self.usable_width - img_w) / 2
                            ax.imshow(
                                img_data,
                                extent=(
                                    float(img_x),
                                    float(img_x + img_w),
                                    float(it_y - img_h),
                                    float(it_y),
                                ),
                                aspect="auto",
                            )
                            # Caption below image
                            ax.text(
                                self.page_width / 2,
                                it_y - img_h - 0.08,
                                it["caption"],
                                fontsize=8.0,
                                fontstyle="italic",
                                color="#333333",
                                ha="center",
                                va="top",
                            )

                pdf.savefig(fig)
                plt.close(fig)

        # Write audit JSON report
        if audit_json_path:
            audit_json_path.parent.mkdir(parents=True, exist_ok=True)
            audit_json_path.write_text(json.dumps(audit_data, indent=2), encoding="utf-8")

        return audit_data


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for standalone submission PDF builder."""
    parser = argparse.ArgumentParser(
        description="Compile and export Markdown report to PDF with page audit."
    )
    parser.add_argument(
        "--report",
        "--main-report",
        dest="report",
        type=Path,
        default=Path("report/DRAFT_REPORT.md"),
        help="Path to main research report markdown file.",
    )
    parser.add_argument(
        "--ethics",
        type=Path,
        default=Path("report/LIMITATIONS_AND_ETHICS.md"),
        help="Path to limitations and ethics appendix markdown file.",
    )
    parser.add_argument(
        "--reproduction",
        type=Path,
        default=Path("report/REPRODUCTION_GUIDE.md"),
        help="Path to reproduction guide appendix markdown file.",
    )
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=Path("figures"),
        help="Path to figures directory containing central.png or kinetics.png.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("report/SWARM_CONTAGION_REPORT.pdf"),
        help="Destination path for generated PDF document.",
    )
    parser.add_argument(
        "--audit-output",
        type=Path,
        default=Path("report/pdf_audit.json"),
        help="Destination path for page audit JSON metadata.",
    )

    args = parser.parse_args(argv)

    if not args.report.exists():
        print(f"Error: main report file {args.report} does not exist", file=sys.stderr)
        return 1

    ethics_path = args.ethics if args.ethics.exists() else None
    repro_path = args.reproduction if args.reproduction.exists() else None
    figures_dir = args.figures_dir if args.figures_dir.exists() else None

    compiled_markdown = compile_report_sources(
        main_report_path=args.report,
        ethics_path=ethics_path,
        reproduction_path=repro_path,
    )

    builder = PDFReportBuilder(figures_dir=figures_dir)
    audit = builder.build(
        markdown_text=compiled_markdown,
        output_pdf_path=args.output,
        audit_json_path=args.audit_output,
    )

    print("Submission PDF Export Complete:")
    print(f"  Output PDF: {args.output} ({args.output.stat().st_size} bytes)")
    print(f"  Audit Report: {args.audit_output}")
    print(f"  Total Pages: {audit['total_pages']}")
    print(f"  Main Body Pages (Sections 1 to 6): {audit['main_body_pages']}")
    print(f"  References Start Page: {audit['references_start_page']}")
    print(f"  Appendix Start Page: {audit['appendix_start_page']}")
    print(f"  Within 4-8 Page Hard Cap: {audit['within_4_to_8_page_cap']}")

    if not audit["within_4_to_8_page_cap"]:
        pages = audit["main_body_pages"]
        print(
            f"Warning: main body pages ({pages}) violates the 4 to 8 page hard cap.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
