"""Unit tests for compiling the final research report and LaTeX skeleton."""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Ensure scripts directory is importable
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.compile_report import (  # noqa: E402
    PageBudgetAuditResult,
    audit_page_budget,
    compile_markdown_to_latex,
    compile_report,
    extract_main_body,
    insert_latex_tables,
    markdown_table_to_latex,
    merge_report_sections,
    parse_args,
    update_results_blocks,
)


def sample_draft_markdown(word_count: int = 3500) -> str:
    """Generate a synthetic draft report markdown string with a target word count."""
    # Build text for sections 1 to 6
    section_words = word_count // 6
    paragraph = "Deterministic evaluation of multi-agent lateral communication dynamics. " * 10
    repeats_per_section = max(1, section_words // len(paragraph.split()))

    sections = [
        "# Infection Chains in LLM Swarms: Spread, Detection and Layered Gating\n",
        "## Abstract\nThis paper evaluates contagion dynamics across communicating agent swarms.\n",
    ]
    for i in range(1, 7):
        sections.append(f"## {i}. Section Title {i}\n")
        sections.append((paragraph + "\n\n") * repeats_per_section)

    sections.append("\n## References\n1. Author, A. (2026). Title. Journal, 1(1), 1-10.\n")
    sections.append("\n## Appendix A. Preliminary Notes\nPreliminary content.\n")
    sections.append(
        "\n## Appendix B. Pre-existing Work vs Sprint Work Declaration\nTable of declarations.\n"
    )
    return "\n".join(sections)


def sample_ethics_markdown() -> str:
    """Generate a synthetic ethics appendix markdown string."""
    return (
        "# Appendix: Limitations and Dual-Use / Ethical Considerations\n\n"
        "## 1. Dual-Use Risk Analysis\n"
        "Research analyzing lateral movement within swarms presents dual-use considerations.\n\n"
        "## 2. Experimental Limitations\n"
        "The experiments evaluate a finite interaction horizon.\n"
    )


def sample_repro_markdown() -> str:
    """Generate a synthetic reproduction guide markdown string."""
    return (
        "# Reproduction Guide: Swarm Contagion Testbed\n\n"
        "## 1. Overview\n"
        "This guide describes steps to reproduce all experimental findings.\n\n"
        "## 2. System Requirements\n"
        "Python 3.12 or higher is required.\n"
    )


def test_extract_main_body_isolates_sections_1_to_6() -> None:
    """Verify that extract_main_body stops before References and Appendices."""
    markdown = sample_draft_markdown(word_count=1000)
    main_body = extract_main_body(markdown)

    assert "## 1. Section Title 1" in main_body
    assert "## 6. Section Title 6" in main_body
    assert "## References" not in main_body
    assert "## Appendix" not in main_body


def test_merge_report_sections() -> None:
    """Verify merging draft sections 1 to 6 with ethics, repro guide, and declarations."""
    draft = sample_draft_markdown(word_count=600)
    ethics = sample_ethics_markdown()
    repro = sample_repro_markdown()

    merged = merge_report_sections(
        draft_text=draft,
        ethics_text=ethics,
        repro_text=repro,
    )

    assert "## 1. Section Title 1" in merged
    assert "## 6. Section Title 6" in merged
    assert "## References" in merged
    assert "## Appendix A: Limitations and Dual-Use / Ethical Considerations" in merged
    assert "## Appendix B: Technical Reproduction Guide" in merged
    assert "## Appendix C: Pre-existing Work vs Sprint Work Declaration" in merged

    # Verify that the original draft Appendix A was replaced by the full ethics text
    assert "Preliminary content" not in merged
    assert "Dual-Use Risk Analysis" in merged
    assert "Technical Reproduction Guide" in merged


def test_page_budget_auditor_pass() -> None:
    """Verify that page budget audit passes when main body is between 4 and 8 pages."""
    # At 550 words per page, 3300 words is 6.0 pages (within 4 to 8 pages)
    draft = sample_draft_markdown(word_count=3300)
    ethics = sample_ethics_markdown()
    repro = sample_repro_markdown()
    merged = merge_report_sections(draft, ethics, repro)

    result = audit_page_budget(merged, words_per_page=550.0)

    assert isinstance(result, PageBudgetAuditResult)
    assert result.passed is True
    assert result.is_within_budget is True
    assert result.has_ethics_appendix is True
    assert 4.0 <= result.estimated_pages <= 8.0
    assert result.min_pages == 4.0
    assert result.max_pages == 8.0
    assert len(result.errors) == 0


def test_page_budget_auditor_under_minimum() -> None:
    """Verify that page budget audit fails when main body is under 4 pages."""
    # At 550 words per page, 1100 words is 2.0 pages (under 4 pages)
    draft = sample_draft_markdown(word_count=1100)
    ethics = sample_ethics_markdown()
    repro = sample_repro_markdown()
    merged = merge_report_sections(draft, ethics, repro)

    result = audit_page_budget(merged, words_per_page=550.0)

    assert result.passed is False
    assert result.is_within_budget is False
    assert result.estimated_pages < 4.0
    assert any("under minimum" in msg.lower() for msg in result.errors)


def test_page_budget_auditor_exceeds_maximum() -> None:
    """Verify that page budget audit fails when main body exceeds 8 pages."""
    # At 550 words per page, 5500 words is 10.0 pages (exceeds 8 pages)
    draft = sample_draft_markdown(word_count=5500)
    ethics = sample_ethics_markdown()
    repro = sample_repro_markdown()
    merged = merge_report_sections(draft, ethics, repro)

    result = audit_page_budget(merged, words_per_page=550.0)

    assert result.passed is False
    assert result.is_within_budget is False
    assert result.estimated_pages > 8.0
    assert any("exceeds" in msg.lower() for msg in result.errors)


def test_page_budget_auditor_missing_ethics_appendix() -> None:
    """Verify that page budget audit fails if the ethics appendix is omitted."""
    draft = sample_draft_markdown(word_count=3300)
    # Merged text without ethics appendix
    merged_without_ethics = draft

    result = audit_page_budget(merged_without_ethics, words_per_page=550.0)

    assert result.passed is False
    assert result.has_ethics_appendix is False
    assert any("ethics appendix" in msg.lower() for msg in result.errors)


def test_page_budget_auditor_excludes_references_and_appendices() -> None:
    """Verify that references and appendices do not count toward main body page budget."""
    # Small main body (1000 words ~ 1.8 pages)
    draft = sample_draft_markdown(word_count=1000)
    # Very long appendix (4000 words)
    long_appendix = (
        "## Appendix A: Limitations and Dual-Use / Ethical Considerations\n\n"
        + ("Extensive discussion on governance and risk mitigation protocols. " * 500)
    )
    doc_with_long_appendix = draft + "\n\n" + long_appendix

    result = audit_page_budget(doc_with_long_appendix, words_per_page=550.0)

    # Main body page count should reflect ~1000 words, not ~5000 words
    assert result.estimated_pages < 3.0
    assert result.is_within_budget is False


def test_update_results_blocks() -> None:
    """Verify updating marked results blocks in markdown text."""
    text = (
        "Intro text.\n\n"
        "<!-- RESULTS:BEGIN table_alpha -->\n"
        "Old table content\n"
        "<!-- RESULTS:END table_alpha -->\n\n"
        "Conclusion text."
    )
    rendered = {"table_alpha": "| Col 1 | Col 2 |\n|---|---|\n| A | B |"}

    updated = update_results_blocks(text, rendered)

    assert "Old table content" not in updated
    assert "| Col 1 | Col 2 |" in updated
    assert "<!-- RESULTS:BEGIN table_alpha -->" in updated
    assert "<!-- RESULTS:END table_alpha -->" in updated
    assert "Intro text." in updated
    assert "Conclusion text." in updated


def test_markdown_table_to_latex() -> None:
    """Verify converting a markdown table into LaTeX booktabs environment."""
    md_table = (
        "| Model | Score | Notes |\n"
        "|---|---|---|\n"
        "| agent_1 | 0.850 | TODO(result) |\n"
        "| agent_2 | 0.920 | Complete |"
    )
    latex_table = markdown_table_to_latex(
        md_table,
        caption="Evaluation of agent performance.",
        label="tab:eval_perf",
    )

    assert r"\begin{table}" in latex_table
    assert r"\centering" in latex_table
    assert r"\caption{Evaluation of agent performance.}" in latex_table
    assert r"\label{tab:eval_perf}" in latex_table
    assert (
        r"\begin{tabular}{lll}" in latex_table
        or r"\begin{tabular}{lrr}" in latex_table
        or r"\begin{tabular}" in latex_table
    )
    assert r"\toprule" in latex_table
    assert r"\midrule" in latex_table
    assert r"\bottomrule" in latex_table
    assert r"\end{tabular}" in latex_table
    assert r"\end{table}" in latex_table
    assert "TODO(result)" in latex_table  # Marker preserved
    assert "agent\\_1" in latex_table     # Underscore escaped


def test_insert_latex_tables() -> None:
    """Verify inserting pre-rendered LaTeX tables into document template."""
    latex_text = (
        "\\section{Results}\n\n"
        "% TABLE:BEGIN table_summary\n"
        "Placeholder table\n"
        "% TABLE:END table_summary\n"
    )
    custom_table = "\\begin{table}\n\\caption{Summary}\n\\end{table}"
    tables_map = {"table_summary": custom_table}

    output = insert_latex_tables(latex_text, tables=tables_map)

    assert "Placeholder table" not in output
    assert custom_table in output


def test_compile_markdown_to_latex() -> None:
    """Verify full conversion from compiled markdown to a valid LaTeX skeleton."""
    draft = sample_draft_markdown(word_count=1200)
    ethics = sample_ethics_markdown()
    repro = sample_repro_markdown()
    merged = merge_report_sections(draft, ethics, repro)

    latex_code = compile_markdown_to_latex(merged)

    assert r"\documentclass[11pt,a4paper]{article}" in latex_code
    assert r"\usepackage{booktabs}" in latex_code
    assert r"\begin{document}" in latex_code
    assert r"\maketitle" in latex_code
    assert r"\begin{abstract}" in latex_code
    assert r"\end{abstract}" in latex_code
    assert r"\section{Section Title 1}" in latex_code
    assert r"\section{References}" in latex_code or r"\begin{thebibliography}" in latex_code
    assert r"\appendix" in latex_code
    assert r"\section{Limitations and Dual-Use / Ethical Considerations}" in latex_code
    assert r"\section{Technical Reproduction Guide}" in latex_code
    assert r"\end{document}" in latex_code


def test_compile_report_execution(tmp_path: Path) -> None:
    """Verify end-to-end execution of compile_report on workspace files."""
    draft_file = REPO_ROOT / "report" / "DRAFT_REPORT.md"
    ethics_file = REPO_ROOT / "report" / "LIMITATIONS_AND_ETHICS.md"
    repro_file = REPO_ROOT / "report" / "REPRODUCTION_GUIDE.md"

    out_md = tmp_path / "FINAL_REPORT.md"
    out_tex = tmp_path / "paper.tex"

    compiled_md, compiled_tex, audit = compile_report(
        draft_path=draft_file,
        ethics_path=ethics_file,
        repro_path=repro_file,
        output_markdown_path=out_md,
        output_latex_path=out_tex,
        words_per_page=550.0,
    )

    assert out_md.is_file()
    assert out_tex.is_file()
    assert out_md.stat().st_size > 0
    assert out_tex.stat().st_size > 0

    # Verify sections present in markdown
    assert "## Abstract" in compiled_md
    assert "## 1. Introduction" in compiled_md
    assert "## 6. Empirical Results Framework and Tables" in compiled_md
    assert "## References" in compiled_md
    assert "## Appendix A: Limitations and Dual-Use / Ethical Considerations" in compiled_md
    assert "## Appendix B: Technical Reproduction Guide" in compiled_md
    assert "## Appendix C: Pre-existing Work vs Sprint Work Declaration" in compiled_md

    # Verify LaTeX structure
    assert r"\documentclass" in compiled_tex
    assert r"\begin{document}" in compiled_tex
    assert r"\appendix" in compiled_tex
    assert r"\end{document}" in compiled_tex

    # Verify audit result structure
    assert audit.has_ethics_appendix is True
    assert 4.0 <= audit.estimated_pages <= 8.0
    assert audit.passed is True


def test_compiled_outputs_no_em_dash_or_forbidden_words(tmp_path: Path) -> None:
    """Verify absence of em dashes and forbidden words in compiled files."""
    draft_file = REPO_ROOT / "report" / "DRAFT_REPORT.md"
    ethics_file = REPO_ROOT / "report" / "LIMITATIONS_AND_ETHICS.md"
    repro_file = REPO_ROOT / "report" / "REPRODUCTION_GUIDE.md"

    out_md = tmp_path / "FINAL_REPORT.md"
    out_tex = tmp_path / "paper.tex"

    compiled_md, compiled_tex, _ = compile_report(
        draft_path=draft_file,
        ethics_path=ethics_file,
        repro_path=repro_file,
        output_markdown_path=out_md,
        output_latex_path=out_tex,
    )

    em_dash = "\u2014"
    assert em_dash not in compiled_md, "Em dash found in compiled markdown"
    assert em_dash not in compiled_tex, "Em dash found in compiled LaTeX"

    for suffix in ["est", "estly", "esty"]:
        forbidden = "hon" + suffix
        pattern = re.compile(rf"\b{forbidden}\b", re.IGNORECASE)
        assert not pattern.search(compiled_md), f"Forbidden word '{forbidden}' in markdown"
        assert not pattern.search(compiled_tex), f"Forbidden word '{forbidden}' in LaTeX"


def test_cli_parsing() -> None:
    """Verify command line argument parsing options."""
    args = parse_args(["--check", "--words-per-page", "500"])
    assert args.check is True
    assert args.words_per_page == 500.0
