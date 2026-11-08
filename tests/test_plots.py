"""Tests for swarmlab.metrics.plots."""

import ast
import csv
import struct
from collections.abc import Sequence
from pathlib import Path

import pytest

from swarmlab.metrics.plots import (
    KINETICS_COLUMNS,
    PANEL_A_COLUMNS,
    PANEL_B_COLUMNS,
    plot_central_figure,
    plot_kinetics,
    read_table,
)

# Standard 8-byte PNG header signature
PNG_SIGNATURE: bytes = b"\x89PNG\r\n\x1a\n"

# Allowed numeric literals in plots.py, justified by layout and structural requirements:
# 0, 0.0: Indexing origin, lower boundary, or axis limit
# 1, 1.0: Increment step, single subplot row, upper probability limit
# 2: Two subplot columns in central figure layout, divisor for bar width centering
# 9: Minimum legible font size in points
# 150: Image resolution in dots per inch (DPI)
# 11.0: Width in inches for central two-panel figure
# 5.0: Height in inches for central two-panel figure, and annotation offset in points
# 7.0: Width in inches for kinetics figure
# 4.5: Height in inches for kinetics figure
# 0.35: Bar width in grouped bar chart
# 3.0: Error bar cap size in points
# 40.0: Base scatter marker area in points squared
# 300.0: Multiplier scaling marker area by utility loss
# 0.2: Transparency alpha for shaded confidence interval band
# 1.5: Line width in points for kinetics line plot
ALLOWED_NUMERIC_LITERALS: set[int | float] = {
    0,
    1,
    2,
    9,
    150,
    11.0,
    5.0,
    7.0,
    4.5,
    0.35,
    3.0,
    40.0,
    300.0,
    0.2,
    1.5,
}

# Test fixture data: synthetic values used strictly for exercising functions
FIXTURE_PANEL_A: list[dict[str, str]] = [
    {"detector": "D1", "playbook": "seen", "tpr": "0.85", "ci_lo": "0.78", "ci_hi": "0.90"},
    {"detector": "D1", "playbook": "held_out", "tpr": "0.65", "ci_lo": "0.58", "ci_hi": "0.72"},
    {"detector": "D2", "playbook": "seen", "tpr": "0.90", "ci_lo": "0.84", "ci_hi": "0.94"},
    {"detector": "D2", "playbook": "held_out", "tpr": "0.75", "ci_lo": "0.68", "ci_hi": "0.81"},
]

FIXTURE_PANEL_B: list[dict[str, str]] = [
    {
        "defense": "D1",
        "llm_call_share": "0.00",
        "utility_loss": "0.02",
        "exfil_reduction": "0.40",
        "r0": "1.8",
    },
    {
        "defense": "D2",
        "llm_call_share": "1.00",
        "utility_loss": "0.05",
        "exfil_reduction": "0.75",
        "r0": "0.9",
    },
    {
        "defense": "D3",
        "llm_call_share": "1.00",
        "utility_loss": "0.08",
        "exfil_reduction": "0.82",
        "r0": "0.7",
    },
    {
        "defense": "D5",
        "llm_call_share": "0.35",
        "utility_loss": "0.06",
        "exfil_reduction": "0.80",
        "r0": "0.8",
    },
]

FIXTURE_KINETICS: list[dict[str, str]] = [
    {
        "round": "0",
        "topology": "ring",
        "harm": "split",
        "infected_mean": "1.0",
        "ci_lo": "1.0",
        "ci_hi": "1.0",
    },
    {
        "round": "1",
        "topology": "ring",
        "harm": "split",
        "infected_mean": "1.8",
        "ci_lo": "1.4",
        "ci_hi": "2.2",
    },
    {
        "round": "2",
        "topology": "ring",
        "harm": "split",
        "infected_mean": "2.5",
        "ci_lo": "2.0",
        "ci_hi": "3.0",
    },
    {
        "round": "0",
        "topology": "complete",
        "harm": "solo",
        "infected_mean": "1.0",
        "ci_lo": "1.0",
        "ci_hi": "1.0",
    },
    {
        "round": "1",
        "topology": "complete",
        "harm": "solo",
        "infected_mean": "2.4",
        "ci_lo": "1.9",
        "ci_hi": "2.9",
    },
    {
        "round": "2",
        "topology": "complete",
        "harm": "solo",
        "infected_mean": "4.1",
        "ci_lo": "3.5",
        "ci_hi": "4.7",
    },
]


def write_fixture_csv(path: Path, fieldnames: Sequence[str], rows: list[dict[str, str]]) -> None:
    """Helper to write fixture CSV data for tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def extract_png_dimensions(png_bytes: bytes) -> tuple[int, int]:
    """Extract width and height from PNG IHDR chunk using standard library struct."""
    assert png_bytes.startswith(PNG_SIGNATURE), "File missing PNG signature bytes"
    assert png_bytes[12:16] == b"IHDR", "First PNG chunk is not IHDR"
    width, height = struct.unpack(">II", png_bytes[16:24])
    return width, height


def test_read_table_success(tmp_path: Path) -> None:
    """Read valid CSV table with exact required columns."""
    csv_file = tmp_path / "panel_a.csv"
    write_fixture_csv(csv_file, PANEL_A_COLUMNS, FIXTURE_PANEL_A)

    rows = read_table(csv_file, PANEL_A_COLUMNS)
    assert len(rows) == len(FIXTURE_PANEL_A)
    assert rows == FIXTURE_PANEL_A


def test_read_table_extra_columns(tmp_path: Path) -> None:
    """Read CSV table containing extra columns beyond required ones."""
    csv_file = tmp_path / "panel_a_extra.csv"
    extra_fieldnames = list(PANEL_A_COLUMNS) + ["aux_info", "timestamp"]
    extra_rows = [
        {**row, "aux_info": "extra_val", "timestamp": "2026-11-08"} for row in FIXTURE_PANEL_A
    ]
    write_fixture_csv(csv_file, extra_fieldnames, extra_rows)

    rows = read_table(csv_file, PANEL_A_COLUMNS)
    assert len(rows) == len(extra_rows)
    for row, expected in zip(rows, extra_rows, strict=True):
        assert row["detector"] == expected["detector"]
        assert row["aux_info"] == "extra_val"


def test_read_table_missing_columns(tmp_path: Path) -> None:
    """Raise ValueError listing missing columns when required columns are absent."""
    csv_file = tmp_path / "panel_a_missing.csv"
    incomplete_fieldnames = ("detector", "playbook")
    incomplete_rows = [{"detector": "D1", "playbook": "seen"}]
    write_fixture_csv(csv_file, incomplete_fieldnames, incomplete_rows)

    with pytest.raises(ValueError) as exc_info:
        read_table(csv_file, PANEL_A_COLUMNS)

    error_msg = str(exc_info.value)
    assert "tpr" in error_msg
    assert "ci_lo" in error_msg
    assert "ci_hi" in error_msg


def test_plot_central_figure_success(tmp_path: Path) -> None:
    """Generate central figure PNG and verify header, non-zero size, and dimension stability."""
    csv_a = tmp_path / "panel_a.csv"
    csv_b = tmp_path / "panel_b.csv"
    write_fixture_csv(csv_a, PANEL_A_COLUMNS, FIXTURE_PANEL_A)
    write_fixture_csv(csv_b, PANEL_B_COLUMNS, FIXTURE_PANEL_B)

    out_png_1 = tmp_path / "sub" / "dir" / "central_figure_1.png"
    out_png_2 = tmp_path / "sub" / "dir" / "central_figure_2.png"

    plot_central_figure(csv_a, csv_b, out_png_1)
    assert out_png_1.exists()
    data_1 = out_png_1.read_bytes()
    assert len(data_1) > 0
    assert data_1.startswith(PNG_SIGNATURE)

    width_1, height_1 = extract_png_dimensions(data_1)
    assert width_1 > 0
    assert height_1 > 0

    plot_central_figure(csv_a, csv_b, out_png_2)
    assert out_png_2.exists()
    data_2 = out_png_2.read_bytes()
    width_2, height_2 = extract_png_dimensions(data_2)

    assert (width_1, height_1) == (width_2, height_2)


def test_plot_central_figure_missing_column_raises_before_write(tmp_path: Path) -> None:
    """Verify ValueError is raised and no output file is created if a column is missing."""
    csv_a_valid = tmp_path / "panel_a.csv"
    write_fixture_csv(csv_a_valid, PANEL_A_COLUMNS, FIXTURE_PANEL_A)

    csv_b_bad = tmp_path / "panel_b_bad.csv"
    write_fixture_csv(csv_b_bad, ("defense", "r0"), [{"defense": "D1", "r0": "1.0"}])

    out_png = tmp_path / "unwritten" / "central.png"

    with pytest.raises(ValueError) as exc_info:
        plot_central_figure(csv_a_valid, csv_b_bad, out_png)

    assert "llm_call_share" in str(exc_info.value)
    assert not out_png.exists()


def test_plot_kinetics_success(tmp_path: Path) -> None:
    """Generate kinetics PNG and verify header, non-zero size, and dimension stability."""
    csv_kinetics = tmp_path / "kinetics.csv"
    write_fixture_csv(csv_kinetics, KINETICS_COLUMNS, FIXTURE_KINETICS)

    out_png_1 = tmp_path / "nested" / "kinetics_1.png"
    out_png_2 = tmp_path / "nested" / "kinetics_2.png"

    plot_kinetics(csv_kinetics, out_png_1)
    assert out_png_1.exists()
    data_1 = out_png_1.read_bytes()
    assert len(data_1) > 0
    assert data_1.startswith(PNG_SIGNATURE)

    width_1, height_1 = extract_png_dimensions(data_1)
    assert width_1 > 0
    assert height_1 > 0

    plot_kinetics(csv_kinetics, out_png_2)
    assert out_png_2.exists()
    data_2 = out_png_2.read_bytes()
    width_2, height_2 = extract_png_dimensions(data_2)

    assert (width_1, height_1) == (width_2, height_2)


def test_plot_kinetics_missing_column_raises_before_write(tmp_path: Path) -> None:
    """Verify ValueError is raised and no file is created when kinetics column is missing."""
    csv_bad = tmp_path / "kinetics_bad.csv"
    write_fixture_csv(csv_bad, ("round", "topology"), [{"round": "0", "topology": "ring"}])

    out_png = tmp_path / "unwritten" / "kinetics.png"

    with pytest.raises(ValueError) as exc_info:
        plot_kinetics(csv_bad, out_png)

    assert "infected_mean" in str(exc_info.value)
    assert not out_png.exists()


def test_static_check_numeric_literals() -> None:
    """Ensure plots.py contains no numeric literals other than approved layout constants."""
    source_path = Path("src/swarmlab/metrics/plots.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    found_literals: list[int | float] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
        ):
            assert node.value in ALLOWED_NUMERIC_LITERALS, (
                f"Numeric literal {node.value} (type {type(node.value).__name__}) "
                f"in {source_path} is not in ALLOWED_NUMERIC_LITERALS."
            )
            found_literals.append(node.value)

    assert len(found_literals) > 0
