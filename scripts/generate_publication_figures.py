"""Publication figures generator for campaign results and metrics."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from swarmlab.metrics.events import read_events  # noqa: E402
from swarmlab.metrics.extract import infection_state  # noqa: E402
from swarmlab.metrics.plots import (  # noqa: E402
    plot_central_figure,
    plot_kinetics,
)
from swarmlab.metrics.stats import auroc  # noqa: E402
from swarmlab.schema import GroundTruth  # noqa: E402

# Colorblind-safe palette (Okabe-Ito)
OKABE_ITO_PALETTE: tuple[str, ...] = (
    "#0072B2",  # blue
    "#D55E00",  # vermilion
    "#009E73",  # bluish green
    "#56B4E9",  # sky blue
    "#E69F00",  # orange
    "#CC79A7",  # reddish purple
    "#000000",  # black
)

DETECTOR_COLORS: dict[str, str] = {
    "d1": "#0072B2",
    "d2": "#D55E00",
    "d3": "#009E73",
    "d4": "#56B4E9",
    "d5": "#CC79A7",
}

DEFENSE_COLORS: dict[str, str] = {
    "D1": "#0072B2",
    "D2": "#D55E00",
    "D3": "#009E73",
    "D4": "#56B4E9",
    "D5": "#CC79A7",
}

ROLE_COLORS: dict[str, str] = {
    "patient_zero": "#D55E00",
    "recruited": "#E69F00",
    "holder": "#009E73",
    "standard": "#56B4E9",
}


def _has_data_rows(path: Path) -> bool:
    """Return True if path is a file and contains at least one non-empty data row."""
    if not path.is_file():
        return False
    try:
        with open(path, encoding="utf-8", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader, None)
            if header is None:
                return False
            for row in reader:
                if row and any(cell.strip() for cell in row):
                    return True
        return False
    except Exception:
        return False


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert a value to float with a fallback default."""
    if val is None or val == "" or str(val).lower() in ("null", "none"):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def ensure_central_and_kinetics(output_dir: Path) -> list[Path]:
    """Generate central.png and kinetics.png if corresponding source CSV files exist.

    Uses plot_central_figure if panel_a.csv and panel_b.csv exist with data rows.
    Uses plot_kinetics if kinetics_a1.csv (or fallback kinetics.csv) exists with data rows.
    Returns list of generated Path objects.
    """
    generated: list[Path] = []
    output_dir = Path(output_dir)

    panel_a = output_dir / "panel_a.csv"
    panel_b = output_dir / "panel_b.csv"
    if _has_data_rows(panel_a) and _has_data_rows(panel_b):
        central_png = output_dir / "central.png"
        plot_central_figure(panel_a, panel_b, central_png)
        generated.append(central_png)

    kinetics_a1 = output_dir / "kinetics_a1.csv"
    kinetics_fallback = output_dir / "kinetics.csv"
    kinetics_path: Path | None = None
    if _has_data_rows(kinetics_a1):
        kinetics_path = kinetics_a1
    elif _has_data_rows(kinetics_fallback):
        kinetics_path = kinetics_fallback

    if kinetics_path is not None:
        kinetics_png = output_dir / "kinetics.png"
        plot_kinetics(kinetics_path, kinetics_png)
        generated.append(kinetics_png)

    return generated


def _compute_empirical_roc(
    pos_scores: Sequence[float], neg_scores: Sequence[float]
) -> tuple[np.ndarray, np.ndarray]:
    """Compute empirical false positive and true positive rates by threshold sweeping."""
    all_scores = list(pos_scores) + list(neg_scores)
    thresh_set = set(all_scores) | {1.0 + 1e-9, -1e-9}
    thresholds = sorted(thresh_set, reverse=True)

    pos_arr = np.asarray(pos_scores, dtype=float)
    neg_arr = np.asarray(neg_scores, dtype=float)

    fprs: list[float] = []
    tprs: list[float] = []

    for t in thresholds:
        fpr = float(np.mean(neg_arr >= t)) if len(neg_arr) > 0 else 0.0
        tpr = float(np.mean(pos_arr >= t)) if len(pos_arr) > 0 else 0.0
        fprs.append(fpr)
        tprs.append(tpr)

    return np.asarray(fprs, dtype=float), np.asarray(tprs, dtype=float)


def plot_roc_comparison(scores_json_path: Path, out_png: Path, dpi: int = 300) -> Path:
    """Plot empirical ROC curves comparing detectors on seen vs held-out playbooks.

    Reads scores_json_path, computes empirical ROC curves and AUROC values, and
    saves a 1x2 panel figure.
    """
    scores_json_path = Path(scores_json_path)
    out_png = Path(out_png)

    raw_data = json.loads(scores_json_path.read_text(encoding="utf-8"))
    messages: list[dict[str, Any]] = (
        raw_data["messages"]
        if isinstance(raw_data, dict) and "messages" in raw_data
        else (raw_data if isinstance(raw_data, list) else [])
    )

    candidate_detectors = ("d1", "d2", "d3", "d4", "d5")
    present_detectors = [
        d for d in candidate_detectors if any(m.get(d) is not None for m in messages)
    ]

    fig, (ax_seen, ax_heldout) = plt.subplots(1, 2, figsize=(11.0, 4.8))

    panel_configs = [
        (ax_seen, "Seen Playbooks (Styles 0 & 1)", (0, 1)),
        (ax_heldout, "Held-Out Playbook (Style 2)", (2,)),
    ]

    for ax, title, styles in panel_configs:
        panel_msgs = [m for m in messages if m.get("playbook_style") in styles]

        for det in present_detectors:
            det_msgs = [m for m in panel_msgs if m.get(det) is not None]
            pos_scores = [
                float(m[det]) for m in det_msgs if bool(m.get("l1") or m.get("l2"))
            ]
            neg_scores = [
                float(m[det]) for m in det_msgs if not bool(m.get("l1") or m.get("l2"))
            ]

            if pos_scores and neg_scores:
                auc_val = auroc(pos_scores, neg_scores)
                label = f"{det.upper()} (AUROC={auc_val:.3f})"
            else:
                label = f"{det.upper()} (N/A)"

            fprs, tprs = _compute_empirical_roc(pos_scores, neg_scores)
            color = DETECTOR_COLORS.get(det, "#000000")
            ax.plot(fprs, tprs, label=label, color=color, linewidth=1.5)

        # Reference diagonal line
        ax.plot(
            [0.0, 1.0],
            [0.0, 1.0],
            linestyle="--",
            color="gray",
            linewidth=1.0,
            alpha=0.7,
        )
        # Vertical dashed reference line at FPR = 0.005
        ax.axvline(
            x=0.005,
            linestyle="--",
            color="gray",
            linewidth=1.0,
            alpha=0.7,
        )

        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.set_xlabel("False Positive Rate (FPR)", fontsize=9)
        ax.set_ylabel("True Positive Rate (TPR)", fontsize=9)
        ax.set_title(title, fontsize=10)
        ax.legend(loc="lower right", fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    return out_png


def plot_gating_tradeoff(analysis_dir: Path, out_png: Path, dpi: int = 300) -> Path:
    """Plot online gating frontier and reproduction number comparisons across defenses.

    Panel 1 displays exfiltration reduction versus utility preservation.
    Panel 2 displays grouped bars comparing R0 and LLM call share.
    """
    analysis_dir = Path(analysis_dir)
    out_png = Path(out_png)

    comparisons_path = analysis_dir / "paired_comparisons.csv"
    comparisons_rows: list[dict[str, str]] = []
    if comparisons_path.is_file():
        with open(comparisons_path, encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames:
                comparisons_rows = list(reader)

    panel_b_path = analysis_dir / "panel_b.csv"
    panel_b_rows: list[dict[str, str]] = []
    if panel_b_path.is_file():
        with open(panel_b_path, encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames:
                panel_b_rows = list(reader)

    arm_summary_path = analysis_dir / "arm_summary.csv"
    arm_summary_rows: list[dict[str, str]] = []
    if arm_summary_path.is_file():
        with open(arm_summary_path, encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames:
                arm_summary_rows = list(reader)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.8))

    # Panel 1: Online Gating Frontier
    valid_comparisons = [
        r
        for r in comparisons_rows
        if r.get("defense")
        and r.get("exfiltration_reduction") not in (None, "", "null")
        and r.get("utility_loss") not in (None, "", "null")
    ]

    if valid_comparisons:
        for idx, row in enumerate(valid_comparisons):
            defense = row["defense"].upper()
            exfil_red = _safe_float(row["exfiltration_reduction"])
            u_loss = _safe_float(row["utility_loss"])
            preservation = 1.0 - u_loss

            eff_lo = _safe_float(row.get("effect_ci_lo"), exfil_red)
            eff_hi = _safe_float(row.get("effect_ci_hi"), exfil_red)
            yerr_lo = max(0.0, exfil_red - eff_lo)
            yerr_hi = max(0.0, eff_hi - exfil_red)

            u_lo = _safe_float(row.get("utility_loss_ci_lo"), u_loss)
            u_hi = _safe_float(row.get("utility_loss_ci_hi"), u_loss)
            xerr_lo = max(0.0, u_hi - u_loss)
            xerr_hi = max(0.0, u_loss - u_lo)

            color = DEFENSE_COLORS.get(
                defense, OKABE_ITO_PALETTE[idx % len(OKABE_ITO_PALETTE)]
            )
            ax1.errorbar(
                preservation,
                exfil_red,
                xerr=[[xerr_lo], [xerr_hi]],
                yerr=[[yerr_lo], [yerr_hi]],
                fmt="o",
                color=color,
                ecolor=color,
                elinewidth=1.5,
                capsize=3.0,
                markersize=7,
                label=defense,
            )
            ax1.annotate(
                defense,
                (preservation, exfil_red),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=9,
                fontweight="bold",
            )

        # Check for A3c benign workload summary in arm_summary.csv
        for r in arm_summary_rows:
            if r.get("arm") == "A3c" and r.get("utility_mean") not in (None, "", "null"):
                benign_util = _safe_float(r.get("utility_mean"), 1.0)
                ax1.axvline(
                    x=benign_util,
                    linestyle=":",
                    color="gray",
                    alpha=0.6,
                    label=f"A3c Utility ({benign_util:.2f})",
                )
                break

        ax1.set_xlabel("Benign Utility Preservation (1 - Utility Loss)", fontsize=9)
        ax1.set_ylabel("Exfiltration Reduction vs No Defense", fontsize=9)
        ax1.set_title("Online Gating Frontier", fontsize=10)
        ax1.grid(True, alpha=0.3)
    else:
        ax1.text(
            0.5,
            0.5,
            "No gating comparison data available",
            ha="center",
            va="center",
            fontsize=10,
            color="gray",
        )
        ax1.set_title("Online Gating Frontier", fontsize=10)

    # Panel 2: Reproduction Number & LLM Call Share by Defense
    defense_source_rows = panel_b_rows if panel_b_rows else comparisons_rows
    target_defenses = ["D1", "D2", "D3", "D5"]

    present_defenses: list[str] = []
    for d in target_defenses:
        if any(r.get("defense", "").upper() == d for r in defense_source_rows):
            present_defenses.append(d)

    if not present_defenses:
        present_defenses = list(
            dict.fromkeys(
                r["defense"].upper()
                for r in defense_source_rows
                if r.get("defense")
            )
        )

    if present_defenses:
        r0_values: list[float] = []
        llm_shares: list[float] = []

        for d in present_defenses:
            matching = [
                r
                for r in defense_source_rows
                if r.get("defense", "").upper() == d
            ]
            if matching:
                row = matching[0]
                r0_val = _safe_float(
                    row.get("r0") or row.get("offspring_mean_recruitment")
                )
                llm_val = _safe_float(row.get("llm_call_share"))
            else:
                r0_val = 0.0
                llm_val = 0.0
            r0_values.append(r0_val)
            llm_shares.append(llm_val)

        x_coords = np.arange(len(present_defenses))
        bar_width = 0.35

        ax2.bar(
            x_coords - bar_width / 2.0,
            r0_values,
            width=bar_width,
            label=r"$R_{0,\mathrm{rec}}$",
            color="#0072B2",
        )
        ax2.bar(
            x_coords + bar_width / 2.0,
            llm_shares,
            width=bar_width,
            label="LLM Call Share",
            color="#D55E00",
        )

        ax2.set_xticks(x_coords)
        ax2.set_xticklabels(present_defenses, fontsize=9)
        ax2.set_ylabel("Metric Value", fontsize=9)
        ax2.set_title(
            r"Reproduction Number ($R_{0,\mathrm{rec}}$) & LLM Call Share", fontsize=10
        )
        ax2.legend(fontsize=9)
        ax2.grid(True, alpha=0.3, axis="y")
    else:
        ax2.text(
            0.5,
            0.5,
            "No defense summary data available",
            ha="center",
            va="center",
            fontsize=10,
            color="gray",
        )
        ax2.set_title(
            r"Reproduction Number ($R_{0,\mathrm{rec}}$) & LLM Call Share", fontsize=10
        )

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    return out_png


def _find_candidate_episodes(results_dir: Path) -> list[dict[str, Any]]:
    """Scan results_dir for completed infected episodes with valid manifest, gt, and events."""
    candidates: list[dict[str, Any]] = []
    manifest_paths = sorted(results_dir.rglob("manifest.json"))

    for manifest_path in manifest_paths:
        ep_dir = manifest_path.parent
        gt_path = ep_dir / "gt.json"
        events_path = ep_dir / "events.jsonl"
        if not (gt_path.is_file() and events_path.is_file()):
            continue

        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        status = manifest_data.get("status")
        initial_inf = manifest_data.get("initial_infection") or manifest_data.get(
            "extra", {}
        ).get("initial_infection", False)

        if status != "complete" or not bool(initial_inf):
            continue

        candidates.append(
            {
                "directory": ep_dir,
                "manifest": manifest_data,
                "gt_path": gt_path,
                "events_path": events_path,
            }
        )

    return candidates


def plot_infection_cascade(results_dir: Path, out_png: Path, dpi: int = 300) -> Path:
    """Plot network cascade diagram of infection progression in the highest-spread episode."""
    results_dir = Path(results_dir)
    out_png = Path(out_png)

    candidates = _find_candidate_episodes(results_dir)
    a1_candidates = [
        c for c in candidates if c["manifest"].get("arm") == "A1"
    ]
    eligible = a1_candidates if a1_candidates else candidates

    scored_episodes: list[dict[str, Any]] = []
    for ep in eligible:
        try:
            gt = GroundTruth.from_json(ep["gt_path"].read_text(encoding="utf-8"))
            events = read_events(ep["events_path"])
            state = infection_state(events, gt, initial_infection=True)
            n_infected = len(state)
            scored_episodes.append(
                {
                    "n_infected": n_infected,
                    "episode_id": ep["manifest"].get("episode_id", ep["directory"].name),
                    "gt": gt,
                    "events": events,
                    "state": state,
                    "manifest": ep["manifest"],
                }
            )
        except Exception:
            continue

    if not scored_episodes:
        fig, ax = plt.subplots(figsize=(8.5, 5.5))
        ax.text(
            0.5,
            0.5,
            "No infected episodes found",
            ha="center",
            va="center",
            fontsize=14,
            color="gray",
        )
        ax.axis("off")
        fig.tight_layout()
        out_png.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_png, dpi=dpi, bbox_inches="tight")
        plt.close(fig)
        return out_png

    best_episode = sorted(
        scored_episodes, key=lambda e: (-e["n_infected"], e["episode_id"])
    )[0]

    gt = best_episode["gt"]
    state = best_episode["state"]
    episode_id = best_episode["episode_id"]
    n_agents = max(gt.n_agents, 1)
    topology = gt.topology
    harm = gt.harm
    total_infected = best_episode["n_infected"]

    fig, ax = plt.subplots(figsize=(8.5, 5.5))

    # Compute node coordinates on a circle of radius 1.0 starting at top (12 o'clock)
    node_coords: dict[int, tuple[float, float]] = {}
    for i in range(n_agents):
        angle = (np.pi / 2.0) - (2.0 * np.pi * i / n_agents)
        x = float(np.cos(angle))
        y = float(np.sin(angle))
        node_coords[i] = (x, y)

    # Draw directed arrows from parent to child
    for agent_id, info in state.items():
        parent = info.get("parent")
        inf_round = info.get("infected_round")
        if (
            parent is not None
            and parent in node_coords
            and agent_id in node_coords
        ):
            xp, yp = node_coords[parent]
            xc, yc = node_coords[agent_id]
            ax.annotate(
                "",
                xy=(xc, yc),
                xytext=(xp, yp),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color="#000000",
                    lw=1.5,
                    mutation_scale=15,
                    shrinkA=16,
                    shrinkB=16,
                ),
                zorder=2,
            )
            xm = 0.5 * (xp + xc)
            ym = 0.5 * (yp + yc)
            ax.text(
                xm,
                ym,
                f"r={inf_round}",
                fontsize=8,
                ha="center",
                va="center",
                bbox=dict(
                    boxstyle="round,pad=0.2",
                    facecolor="white",
                    edgecolor="#CCCCCC",
                    alpha=0.9,
                ),
                zorder=4,
            )

    # Draw nodes with role-based colors
    for i in range(n_agents):
        xi, yi = node_coords[i]
        is_patient_zero = (i == gt.patient_zero) or (
            i in state and state[i].get("infected_round") == 0
        )
        is_infected = (
            i in state and state[i].get("infected_round", math.inf) < math.inf
        )

        if is_patient_zero:
            color = ROLE_COLORS["patient_zero"]
        elif is_infected:
            color = ROLE_COLORS["recruited"]
        elif i in gt.holders:
            color = ROLE_COLORS["holder"]
        else:
            color = ROLE_COLORS["standard"]

        circle = plt.Circle(
            (xi, yi),
            radius=0.10,
            facecolor=color,
            edgecolor="black",
            linewidth=1.5,
            zorder=5,
        )
        ax.add_patch(circle)

        text_color = "white" if color in ("#D55E00", "#000000") else "black"
        ax.text(
            xi,
            yi,
            str(i),
            fontsize=10,
            fontweight="bold",
            ha="center",
            va="center",
            color=text_color,
            zorder=6,
        )

    ax.set_aspect("equal")
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.35, 1.35)
    ax.axis("off")

    legend_elements = [
        Patch(facecolor=ROLE_COLORS["patient_zero"], edgecolor="black", label="Patient Zero"),
        Patch(facecolor=ROLE_COLORS["recruited"], edgecolor="black", label="Recruited/Breached"),
        Patch(facecolor=ROLE_COLORS["holder"], edgecolor="black", label="Fragment Holder"),
        Patch(facecolor=ROLE_COLORS["standard"], edgecolor="black", label="Standard Agent"),
    ]
    ax.legend(
        handles=legend_elements,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        fontsize=9,
        frameon=True,
    )

    title = (
        f"Infection Cascade: {episode_id} ({topology}, {harm}) | "
        f"Total Infected: {total_infected}/{n_agents}"
    )
    ax.set_title(title, fontsize=11, pad=15)

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    return out_png


def generate_all_figures(
    results_dir: Path, output_dir: Path, dpi: int = 300
) -> dict[str, Path]:
    """Generate all five publication figures if corresponding inputs are available.

    Returns dictionary mapping figure names to their output Paths.
    """
    results_dir = Path(results_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated: dict[str, Path] = {}

    central_and_kinetics = ensure_central_and_kinetics(output_dir)
    for p in central_and_kinetics:
        if p.name == "central.png":
            generated["central"] = p
        elif p.name == "kinetics.png":
            generated["kinetics"] = p

    scores_candidate = results_dir / "scores.json"
    if not scores_candidate.is_file() and (output_dir / "scores.json").is_file():
        scores_candidate = output_dir / "scores.json"

    if scores_candidate.is_file():
        roc_png = output_dir / "roc_comparison.png"
        plot_roc_comparison(scores_candidate, roc_png, dpi=dpi)
        generated["roc_comparison"] = roc_png

    comparisons_csv = output_dir / "paired_comparisons.csv"
    if comparisons_csv.is_file():
        gating_png = output_dir / "gating_tradeoff.png"
        plot_gating_tradeoff(output_dir, gating_png, dpi=dpi)
        generated["gating_tradeoff"] = gating_png

    cascade_png = output_dir / "infection_cascade.png"
    plot_infection_cascade(results_dir, cascade_png, dpi=dpi)
    generated["infection_cascade"] = cascade_png

    return generated


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for publication figures generator."""
    parser = argparse.ArgumentParser(
        description="Generate publication figures for swarm contagion results."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/campaign"),
        help="Path to campaign results directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/campaign/analysis"),
        help="Path to analysis output directory.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Output resolution in dots per inch (default: 300).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for CLI execution."""
    args = parse_args(argv)
    generate_all_figures(
        results_dir=args.results_dir,
        output_dir=args.output_dir,
        dpi=args.dpi,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
