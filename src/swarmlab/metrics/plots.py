"""Plotting utilities for experiment results and metrics."""

from collections.abc import Sequence
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Column definitions for result tables
PANEL_A_COLUMNS = ("detector", "playbook", "tpr", "ci_lo", "ci_hi")
PANEL_B_COLUMNS = ("defense", "llm_call_share", "utility_loss", "exfil_reduction", "r0")
KINETICS_COLUMNS = ("round", "topology", "harm", "infected_mean", "ci_lo", "ci_hi")

# Colorblind-safe palette (Okabe-Ito)
COLORBLIND_PALETTE: list[str] = [
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#F0E442",
    "#56B4E9",
    "#E69F00",
    "#CC79A7",
    "#000000",
]

# Layout constants
FIGURE_DPI: int = 150
FONT_SIZE: int = 9
CENTRAL_FIG_WIDTH: float = 11.0
CENTRAL_FIG_HEIGHT: float = 5.0
KINETICS_FIG_WIDTH: float = 7.0
KINETICS_FIG_HEIGHT: float = 4.5
BAR_WIDTH: float = 0.35
CAP_SIZE: float = 3.0
MARKER_BASE_SIZE: float = 40.0
MARKER_SCALE: float = 300.0
SHADING_ALPHA: float = 0.2
TEXT_OFFSET: float = 5.0
LINE_WIDTH: float = 1.5


def read_table(path: Path, columns: Sequence[str]) -> list[dict[str, str]]:
    """Read a CSV file and verify required columns exist.

    Extra columns are allowed. Missing columns raise a ValueError.
    Returns row dictionaries with original string values.
    """
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            missing = list(columns)
        else:
            existing = set(reader.fieldnames)
            missing = [col for col in columns if col not in existing]

        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        return list(reader)


def plot_central_figure(panel_a_csv: Path, panel_b_csv: Path, out_png: Path) -> None:
    """Generate the central figure containing offline detection and online defense trade-offs.

    Panel A displays grouped bars of TPR by detector across seen and held-out playbooks.
    Panel B displays exfiltration reduction against LLM call share with marker size
    scaled by utility loss.
    """
    rows_a = read_table(panel_a_csv, PANEL_A_COLUMNS)
    rows_b = read_table(panel_b_csv, PANEL_B_COLUMNS)

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(CENTRAL_FIG_WIDTH, CENTRAL_FIG_HEIGHT))

    try:
        # Panel A: Detection by playbook
        detectors = list(dict.fromkeys(r["detector"] for r in rows_a))
        records_a: dict[tuple[str, str], dict[str, str]] = {
            (r["detector"], r["playbook"]): r for r in rows_a
        }
        playbooks = ("seen", "held_out")

        for j, playbook in enumerate(playbooks):
            x_positions: list[float] = []
            tprs: list[float] = []
            yerr_low: list[float] = []
            yerr_high: list[float] = []

            for i, detector in enumerate(detectors):
                key = (detector, playbook)
                if key in records_a:
                    row = records_a[key]
                    tpr_val = float(row["tpr"])
                    ci_lo = float(row["ci_lo"])
                    ci_hi = float(row["ci_hi"])

                    if j == 0:
                        x_pos = float(i) - BAR_WIDTH / 2
                    else:
                        x_pos = float(i) + BAR_WIDTH / 2

                    x_positions.append(x_pos)
                    tprs.append(tpr_val)
                    yerr_low.append(tpr_val - ci_lo)
                    yerr_high.append(ci_hi - tpr_val)

            color = COLORBLIND_PALETTE[j % len(COLORBLIND_PALETTE)]
            ax_a.bar(
                x_positions,
                tprs,
                width=BAR_WIDTH,
                yerr=[yerr_low, yerr_high],
                capsize=CAP_SIZE,
                label=playbook,
                color=color,
            )

        ax_a.set_xticks([float(i) for i in range(len(detectors))])
        ax_a.set_xticklabels(detectors, fontsize=FONT_SIZE)
        ax_a.set_ylim(0.0, 1.0)
        ax_a.set_ylabel("TPR at fixed message FPR", fontsize=FONT_SIZE)
        ax_a.set_title("Detection by playbook", fontsize=FONT_SIZE)
        ax_a.legend(fontsize=FONT_SIZE)

        # Panel B: Exfiltration reduction versus guardrail LLM call share
        for idx, row in enumerate(rows_b):
            defense = row["defense"]
            x = float(row["llm_call_share"])
            y = float(row["exfil_reduction"])
            utility_loss = float(row["utility_loss"])
            r0 = row["r0"]

            # Marker area in points squared scales with utility loss:
            # size = MARKER_BASE_SIZE + MARKER_SCALE * utility_loss
            size = MARKER_BASE_SIZE + MARKER_SCALE * utility_loss
            color = COLORBLIND_PALETTE[idx % len(COLORBLIND_PALETTE)]
            ax_b.scatter(x, y, s=size, color=color)

            annotation_text = f"{defense} (R0={r0})"
            ax_b.annotate(
                annotation_text,
                (x, y),
                xytext=(TEXT_OFFSET, TEXT_OFFSET),
                textcoords="offset points",
                fontsize=FONT_SIZE,
            )

        ax_b.scatter([], [], s=MARKER_BASE_SIZE, color="gray", label="marker size: utility loss")
        ax_b.set_xlabel("Share of messages sent to the guardrail LLM", fontsize=FONT_SIZE)
        ax_b.set_ylabel("Reduction of exfiltration rate versus no defense", fontsize=FONT_SIZE)
        ax_b.set_title("Exfiltration reduction vs LLM cost", fontsize=FONT_SIZE)
        ax_b.legend(fontsize=FONT_SIZE)

        out_png.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_png, dpi=FIGURE_DPI, bbox_inches="tight")
    finally:
        plt.close(fig)


def plot_kinetics(kinetics_csv: Path, out_png: Path) -> None:
    """Generate line plot of infected agent counts across rounds with confidence intervals."""
    rows = read_table(kinetics_csv, KINETICS_COLUMNS)

    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (row["topology"], row["harm"])
        if key not in groups:
            groups[key] = []
        groups[key].append(row)

    fig, ax = plt.subplots(figsize=(KINETICS_FIG_WIDTH, KINETICS_FIG_HEIGHT))

    try:
        for idx, ((topology, harm), group_rows) in enumerate(groups.items()):
            sorted_rows = sorted(group_rows, key=lambda r: float(r["round"]))
            rounds = [float(r["round"]) for r in sorted_rows]
            means = [float(r["infected_mean"]) for r in sorted_rows]
            ci_los = [float(r["ci_lo"]) for r in sorted_rows]
            ci_his = [float(r["ci_hi"]) for r in sorted_rows]

            color = COLORBLIND_PALETTE[idx % len(COLORBLIND_PALETTE)]
            label = f"{topology}, {harm}"

            ax.plot(rounds, means, label=label, color=color, linewidth=LINE_WIDTH)
            ax.fill_between(rounds, ci_los, ci_his, color=color, alpha=SHADING_ALPHA)

        ax.set_xlabel("Round", fontsize=FONT_SIZE)
        ax.set_ylabel("Infected agents (mean)", fontsize=FONT_SIZE)
        ax.set_title("Infection kinetics across rounds", fontsize=FONT_SIZE)
        ax.legend(fontsize=FONT_SIZE)

        out_png.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_png, dpi=FIGURE_DPI, bbox_inches="tight")
    finally:
        plt.close(fig)
