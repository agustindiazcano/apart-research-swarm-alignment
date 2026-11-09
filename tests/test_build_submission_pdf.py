"""Unit tests for standalone submission PDF exporter and page cap audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from scripts.build_submission_pdf import (  # noqa: E402
    PDFReportBuilder,
    compile_report_sources,
    main,
    parse_markdown_blocks,
    sanitize_markdown_text,
)


def test_sanitize_markdown_text() -> None:
    """Verify LaTeX math symbols and html comments are converted to plain typography."""
    raw = (
        r"Distance $d \ge 2$, model $D_1$, and $R_{0,\text{rec}} = \frac{1}{|I|} \sum C(u)$."
        "\n<!-- RESULTS:BEGIN sample -->\nSome text <!-- RESULTS:END sample -->"
    )
    cleaned = sanitize_markdown_text(raw)
    assert "$" not in cleaned
    assert "d ≥ 2" in cleaned or "d >= 2" in cleaned
    assert "D1" in cleaned or "D₁" in cleaned
    assert "RESULTS:BEGIN" not in cleaned
    assert "RESULTS:END" not in cleaned


def test_parse_markdown_blocks() -> None:
    """Verify markdown lines are categorized into structured layout blocks."""
    md_content = """# Infection Chains in LLM Swarms
**Author:** Test Author
*Institution*

---

## 1. Introduction
This is the first paragraph with some details.

### 1.1 Threat Model
- Point 1: first item
- Point 2: second item

```bash
echo hello
```

| Metric | Value |
|---|---|
| A | 1 |
| B | 2 |
"""
    blocks = parse_markdown_blocks(md_content)
    block_types = [b.kind for b in blocks]
    assert "h1" in block_types
    assert "meta" in block_types
    assert "h2" in block_types
    assert "h3" in block_types
    assert "para" in block_types
    assert "list" in block_types
    assert "code" in block_types
    assert "table" in block_types


def test_compile_report_sources(tmp_path: Path) -> None:
    """Verify compilation of main report, limitations/ethics, and reproduction guide."""
    main_md = tmp_path / "main.md"
    ethics_md = tmp_path / "ethics.md"
    repro_md = tmp_path / "repro.md"

    main_md.write_text(
        "# Main Title\n\n## 1. Intro\nText\n\n## References\n[1] Ref A\n\n"
        "## Appendix B. Pre-existing Work vs Sprint Work Declaration\nTable B1",
        encoding="utf-8",
    )
    ethics_md.write_text(
        "# Appendix: Limitations and Dual-Use / Ethical Considerations\n\n## 1. Ethics\nDetails",
        encoding="utf-8",
    )
    repro_md.write_text(
        "# Reproduction Guide: Swarm Contagion Testbed\n\n## 1. Steps\nCommand sequence",
        encoding="utf-8",
    )

    compiled = compile_report_sources(
        main_report_path=main_md,
        ethics_path=ethics_md,
        reproduction_path=repro_md,
    )

    assert "## 1. Intro" in compiled
    assert "## References" in compiled
    assert "## Appendix A. Limitations and Dual-Use / Ethical Considerations" in compiled
    assert "## Appendix B. Reproduction Guide" in compiled
    assert "## Appendix C. Pre-existing Work vs Sprint Work Declaration" in compiled


def test_pdf_creation_and_header(tmp_path: Path) -> None:
    """Verify that generated PDF starts with %PDF- header and is non-empty."""
    out_pdf = tmp_path / "test_report.pdf"
    audit_json = tmp_path / "test_audit.json"

    sample_md = """# Test Title
**Author:** Jane Doe
*Test Lab*

---

## 1. Section One
Paragraph text for section one.

## References
1. Reference entry one.

## Appendix A. Notes
Appendix content here.
"""
    builder = PDFReportBuilder()
    audit = builder.build(
        markdown_text=sample_md,
        output_pdf_path=out_pdf,
        audit_json_path=audit_json,
    )

    assert out_pdf.exists()
    assert out_pdf.stat().st_size > 0
    header = out_pdf.read_bytes()[:5]
    assert header == b"%PDF-"

    assert audit_json.exists()
    assert audit["total_pages"] >= 3
    assert audit["main_body_pages"] == 1
    assert audit["references_start_page"] == 2
    assert audit["appendix_start_page"] == 3


def test_figure_embedding(tmp_path: Path) -> None:
    """Verify that figures directory images are embedded into the PDF document."""
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir()

    fig_path = figures_dir / "central.png"
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot([0, 1], [0, 1], label="Test Line")
    ax.legend()
    fig.savefig(fig_path, dpi=100)
    plt.close(fig)

    out_pdf = tmp_path / "report_with_fig.pdf"
    audit_json = tmp_path / "audit_with_fig.json"

    sample_md = """# Title
**Author:** Test

## 2. Threat Model and Architecture
Overview of the system architecture.

## References
1. Ref A
"""
    builder = PDFReportBuilder(figures_dir=figures_dir)
    audit = builder.build(
        markdown_text=sample_md,
        output_pdf_path=out_pdf,
        audit_json_path=audit_json,
    )

    assert out_pdf.exists()
    assert out_pdf.stat().st_size > 0
    assert audit["total_pages"] >= 2


def test_table_formatting_and_wrapping(tmp_path: Path) -> None:
    """Verify that markdown tables are parsed and laid out without error."""
    out_pdf = tmp_path / "table_report.pdf"
    audit_json = tmp_path / "table_audit.json"

    md_with_table = """# Report
**Author:** Author

## 1. Experimental Setup

| Metric Name | Baseline Value | Proposed Gate | Relative Delta | Notes |
|---|---|---|---|---|
| True Positive Rate | 0.850 | 0.940 | +0.090 | Evaluated on held-out split |
| False Positive Rate | 0.005 | 0.004 | -0.001 | Bound under target cap |
| Median Latency (s) | 1.200 | 1.350 | +0.150 | Micro-LLM evaluation cost |

## References
1. Ref A
"""
    builder = PDFReportBuilder()
    audit = builder.build(
        markdown_text=md_with_table,
        output_pdf_path=out_pdf,
        audit_json_path=audit_json,
    )

    assert out_pdf.exists()
    assert audit["total_pages"] >= 2


def test_full_project_report_page_cap_audit(tmp_path: Path) -> None:
    """Verify 4 to 8 page hard cap enforcement on actual project report files."""
    repo_root = Path(__file__).resolve().parents[1]
    draft_path = repo_root / "report" / "DRAFT_REPORT.md"
    ethics_path = repo_root / "report" / "LIMITATIONS_AND_ETHICS.md"
    repro_path = repo_root / "report" / "REPRODUCTION_GUIDE.md"

    assert draft_path.exists(), "report/DRAFT_REPORT.md must exist"
    assert ethics_path.exists(), "report/LIMITATIONS_AND_ETHICS.md must exist"
    assert repro_path.exists(), "report/REPRODUCTION_GUIDE.md must exist"

    compiled_md = compile_report_sources(
        main_report_path=draft_path,
        ethics_path=ethics_path,
        reproduction_path=repro_path,
    )

    out_pdf = tmp_path / "SWARM_CONTAGION_REPORT.pdf"
    audit_json = tmp_path / "pdf_audit.json"

    builder = PDFReportBuilder()
    builder.build(
        markdown_text=compiled_md,
        output_pdf_path=out_pdf,
        audit_json_path=audit_json,
    )

    assert out_pdf.exists()
    assert out_pdf.stat().st_size > 10000

    audit_data = json.loads(audit_json.read_text(encoding="utf-8"))
    assert "total_pages" in audit_data
    assert "main_body_pages" in audit_data
    assert "references_start_page" in audit_data
    assert "appendix_start_page" in audit_data
    assert "within_4_to_8_page_cap" in audit_data

    main_body_pages = audit_data["main_body_pages"]
    # The hackathon hard cap requires Sections 1 to 6 to be between 4 and 8 pages inclusive
    assert 4 <= main_body_pages <= 8, (
        f"Main body pages ({main_body_pages}) must be between 4 and 8 pages"
    )
    assert audit_data["within_4_to_8_page_cap"] is True
    assert audit_data["references_start_page"] == main_body_pages + 1
    assert audit_data["appendix_start_page"] > audit_data["references_start_page"]
    assert audit_data["total_pages"] >= audit_data["appendix_start_page"]


def test_cli_execution(tmp_path: Path) -> None:
    """Verify CLI execution via main function with arguments."""
    repo_root = Path(__file__).resolve().parents[1]
    draft_path = repo_root / "report" / "DRAFT_REPORT.md"
    out_pdf = tmp_path / "cli_report.pdf"
    out_audit = tmp_path / "cli_audit.json"

    code = main([
        "--report",
        str(draft_path),
        "--output",
        str(out_pdf),
        "--audit-output",
        str(out_audit),
    ])
    assert code == 0
    assert out_pdf.exists()
    assert out_audit.exists()


def test_cli_execution_missing_file(tmp_path: Path) -> None:
    """Verify CLI error handling when main report path does not exist."""
    missing_path = tmp_path / "nonexistent.md"
    code = main(["--report", str(missing_path)])
    assert code == 1
