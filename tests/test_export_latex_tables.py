"""Unit tests for exporting analysis CSV files to LaTeX tables."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scripts.export_latex_tables import (
    dataframe_to_latex_table,
    export_analysis_tables,
    main,
)


def test_dataframe_to_latex_table_mixed_types() -> None:
    """Verify conversion of DataFrame with floats, ints, strings, nulls, and TODO markers."""
    float_val1 = 0.12345
    float_val2 = 0.67891
    expected_float1 = f"{float_val1:.3f}"
    expected_float2 = f"{float_val2:.3f}"

    int_val1 = 10
    int_val2 = 25
    int_val3 = 0

    df = pd.DataFrame(
        {
            "model_name": ["agent_alpha", "agent_beta", "control_group"],
            "count_runs": [int_val1, int_val2, int_val3],
            "leak_rate": [float_val1, float_val2, np.nan],
            "status_note": ["TODO(result)", "stable", None],
        }
    )

    caption = "Summary of model infection rates"
    label = "tab:model_summary"
    latex = dataframe_to_latex_table(df, caption=caption, label=label)

    # LaTeX table environment and booktabs elements
    assert r"\begin{table}" in latex
    assert r"\end{table}" in latex
    assert f"\\caption{{{caption}}}" in latex
    assert f"\\label{{{label}}}" in latex
    assert r"\begin{tabular}" in latex
    assert r"\end{tabular}" in latex
    assert r"\toprule" in latex
    assert r"\midrule" in latex
    assert r"\bottomrule" in latex

    # Headers escaping
    assert "model\\_name" in latex
    assert "count\\_runs" in latex
    assert "leak\\_rate" in latex
    assert "status\\_note" in latex

    # Derived values
    assert expected_float1 in latex
    assert expected_float2 in latex
    assert str(int_val1) in latex
    assert str(int_val2) in latex
    assert str(int_val3) in latex

    # Text escaping in data rows
    assert "agent\\_alpha" in latex
    assert "agent\\_beta" in latex
    assert "control\\_group" in latex
    assert "stable" in latex

    # Nulls formatted as '--'
    assert "--" in latex

    # Preservation of TODO marker without alteration
    assert "TODO(result)" in latex


def test_dataframe_to_latex_table_special_characters_and_todo() -> None:
    """Verify proper escaping of LaTeX special characters while preserving TODO markers."""
    df = pd.DataFrame(
        {
            "param_%": ["50%"],
            "item_#": ["#1"],
            "price_$": ["$10"],
            "a&b": ["x&y"],
            "todo_col": ["TODO(arm_1_95%)"],
        }
    )

    latex = dataframe_to_latex_table(df, caption="Special characters", label="tab:special")

    # Header escapes
    assert r"param\_\%" in latex
    assert r"item\_\#" in latex
    assert r"price\_\$" in latex
    assert r"a\&b" in latex
    assert r"todo\_col" in latex

    # Cell escapes
    assert r"50\%" in latex
    assert r"\#1" in latex
    assert r"\$10" in latex
    assert r"x\&y" in latex

    # Ensure TODO marker with internal underscores and percent is unaltered
    assert "TODO(arm_1_95%)" in latex
    assert r"TODO(arm\_1\_95\%)" not in latex


def test_dataframe_to_latex_table_custom_float_format() -> None:
    """Verify custom float formatting string."""
    val = 0.123456
    df = pd.DataFrame({"score": [val]})

    expected_4dec = f"{val:.4f}"
    latex_4dec = dataframe_to_latex_table(
        df,
        caption="Four decimals",
        label="tab:4dec",
        float_format="{:.4f}",
    )
    assert expected_4dec in latex_4dec

    expected_2dec = f"{val:.2f}"
    latex_2dec = dataframe_to_latex_table(
        df,
        caption="Two decimals",
        label="tab:2dec",
        float_format="%.2f",
    )
    assert expected_2dec in latex_2dec


def test_dataframe_to_latex_table_empty() -> None:
    """Verify table generation on an empty DataFrame."""
    df = pd.DataFrame(columns=["arm_id", "sample_size"])
    latex = dataframe_to_latex_table(df, caption="Empty table", label="tab:empty")

    assert r"\begin{table}" in latex
    assert r"arm\_id & sample\_size \\" in latex
    assert r"\toprule" in latex
    assert r"\midrule" in latex
    assert r"\bottomrule" in latex
    assert r"\end{table}" in latex


def test_export_analysis_tables(tmp_path: Path) -> None:
    """Verify scanning analysis directory for standard CSVs and exporting .tex files."""
    analysis_dir = tmp_path / "analysis"
    output_dir = tmp_path / "tables"
    analysis_dir.mkdir(parents=True)

    # Create standard CSV files
    val1 = 0.85
    val2 = 0.15
    summary_df = pd.DataFrame({"metric": ["precision", "recall"], "score": [val1, val2]})
    summary_df.to_csv(analysis_dir / "summary.csv", index=False)

    gating_df = pd.DataFrame({"detector": ["lexical", "guardrail"], "threshold": [0.5, 0.7]})
    gating_df.to_csv(analysis_dir / "gating.csv", index=False)

    kinetics_df = pd.DataFrame({"round": [0, 1, 2], "infected": [1, 2, 4]})
    kinetics_df.to_csv(analysis_dir / "kinetics_a1.csv", index=False)

    # Extra non-standard file should not be exported
    ignored_df = pd.DataFrame({"foo": ["bar"]})
    ignored_df.to_csv(analysis_dir / "other.csv", index=False)

    generated = export_analysis_tables(analysis_dir, output_dir)

    expected_names = ["summary.tex", "gating.tex", "kinetics_a1.tex"]
    assert [p.name for p in generated] == expected_names

    for path in generated:
        assert path.is_file()
        content = path.read_text(encoding="utf-8")
        assert r"\begin{table}" in content
        assert r"\begin{tabular}" in content
        assert r"\toprule" in content
        assert r"\bottomrule" in content

    assert not (output_dir / "other.tex").exists()


def test_export_analysis_tables_missing_input_dir(tmp_path: Path) -> None:
    """Verify error when analysis directory does not exist."""
    missing_dir = tmp_path / "nonexistent"
    output_dir = tmp_path / "tables"
    with pytest.raises(FileNotFoundError):
        export_analysis_tables(missing_dir, output_dir)


def test_main_cli(tmp_path: Path) -> None:
    """Verify CLI main entry point execution."""
    analysis_dir = tmp_path / "analysis"
    output_dir = tmp_path / "tables"
    analysis_dir.mkdir(parents=True)

    df = pd.DataFrame({"col_a": [1, 2], "col_b": [3.4, 5.6]})
    df.to_csv(analysis_dir / "summary.csv", index=False)

    exit_code = main(["--input-dir", str(analysis_dir), "--output-dir", str(output_dir)])
    assert exit_code == 0
    assert (output_dir / "summary.tex").is_file()

    # Test error exit code on invalid input dir
    err_code = main(["--input-dir", str(tmp_path / "missing"), "--output-dir", str(output_dir)])
    assert err_code != 0
