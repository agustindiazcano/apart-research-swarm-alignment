"""Generate LaTeX paper figures, tables and number macros from committed analysis outputs.

Outputs (under report/latex/):
  figures/*.pdf   vector figures (matplotlib)
  tables/*.tex    booktabs tables
  numbers.tex     \\newcommand macros for every number quoted in the prose

No value is typed by hand: everything is read from results/campaign/analysis.
Protocol constants (planned episode counts, pilot and train sizes) are declared once below.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mp  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
AN = ROOT / "results" / "campaign" / "analysis"
OUT = ROOT / "report" / "latex"
FIG = OUT / "figures"
TAB = OUT / "tables"

# Protocol constants from the preregistered design (README, Experimental Matrix)
PLANNED = {"A0": 15, "A1": 60, "A3": 60, "A3c": 20}
PILOT, TRAIN = 3, 15

INK = "#000000"
MUTED = "#6b7280"
C_RING_SOLO, C_RING_SPLIT = "#d1495b", "#e9a23b"
C_CMP_SOLO, C_CMP_SPLIT = "#00798c", "#6a4c93"
GREEN, GRID = "#2a9d6f", "#e5e7eb"

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["DejaVu Serif"],
        "font.size": 9,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titlesize": 9.5,
        "axes.titleweight": "bold",
        "legend.frameon": False,
        "pdf.fonttype": 42,
    }
)


def read(name: str) -> list[dict[str, str]]:
    with open(AN / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def tex_escape(s: str) -> str:
    return s.replace("_", r"\_")


kin = read("kinetics_a1.csv")
arms = read("arm_summary.csv")
panel_a = read("panel_a.csv")
panel_b = read("panel_b.csv")
paired = read("paired_comparisons.csv")
billing = read("billing_totals.csv")[0]
intent = json.loads((AN / "intent_agreement.json").read_text(encoding="utf-8"))
h2 = json.loads((AN / "h2.json").read_text(encoding="utf-8"))


def arm_row(arm: str, topo: str, harm: str, defense: str = "") -> dict[str, str]:
    for r in arms:
        if r["arm"] == arm and r["topology"] == topo and r["harm"] == harm and r["defense"] == defense:
            return r
    raise KeyError((arm, topo, harm, defense))


# ------------------------------------------------------------------ figures
def fig_architecture() -> None:
    fig, ax = plt.subplots(figsize=(6.3, 3.0))
    ax.set_xlim(0, 10.4)
    ax.set_ylim(0, 5)
    ax.axis("off")
    cx, cy, r = 3.0, 2.5, 1.95
    n = 10
    pos = [(cx + r * math.cos(math.pi / 2 - 2 * math.pi * i / n), cy + r * math.sin(math.pi / 2 - 2 * math.pi * i / n)) for i in range(n)]
    for i in range(n):
        j = (i + 1) % n
        ax.plot([pos[i][0], pos[j][0]], [pos[i][1], pos[j][1]], color="#c7cbd6", lw=1.6, zorder=1)
    frag = {3: "frag. 1", 5: "frag. 2", 7: "frag. 3"}
    for a, b in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 9), (9, 8), (8, 7)]:
        ax.annotate("", xy=pos[b], xytext=pos[a], arrowprops=dict(arrowstyle="-|>", color=C_RING_SOLO, lw=1.6, shrinkA=11, shrinkB=11), zorder=2)
    for i, (x, y) in enumerate(pos):
        col = "#ffffff"
        ec = INK
        if i == 0:
            col, ec = C_RING_SOLO, C_RING_SOLO
        elif i in frag:
            col, ec = C_RING_SPLIT, C_RING_SPLIT
        ax.add_patch(mp.Circle((x, y), 0.28, fc=col, ec=ec, lw=1.6, zorder=3))
        ax.text(x, y, str(i), ha="center", va="center", fontsize=8, color=INK, fontweight="bold", zorder=4)
    for k, lab in frag.items():
        d = min(k, n - k)
        x, y = pos[k]
        side = 1 if x > cx else -1
        ax.text(x + side * 0.42, y - 0.02, f"{lab}\ndistance {d}", ha="left" if side > 0 else "right", va="center", fontsize=7.2, color=INK)
    ax.text(pos[0][0], pos[0][1] + 0.5, "patient zero", ha="center", fontsize=7.6, color=INK, fontweight="bold")
    # outbox and legend
    ax.add_patch(mp.FancyBboxPatch((7.2, 2.0), 2.6, 1.7, boxstyle="round,pad=0.05,rounding_size=0.15", fc="#f3f4f8", ec=MUTED, lw=1.2))
    ax.text(8.5, 3.35, "external outbox", ha="center", fontsize=8.4, fontweight="bold", color=INK)
    ax.text(8.5, 2.75, "full 12-character\ncredential assembled?", ha="center", va="center", fontsize=7.8, color=INK)
    ax.text(8.5, 2.2, r"$Y_{\mathrm{exfil}}\in\{0,1\}$", ha="center", fontsize=8.4, color=INK)
    ax.annotate("", xy=(7.2, 2.85), xytext=(5.4, 2.85), arrowprops=dict(arrowstyle="-|>", color=C_RING_SPLIT, lw=1.8))
    ax.text(6.3, 3.05, "send_external", ha="center", fontsize=7.4, color=INK)
    ax.legend(
        handles=[
            mp.Patch(fc=C_RING_SOLO, label="infected (patient zero)"),
            mp.Patch(fc=C_RING_SPLIT, label="fragment holder (4 characters)"),
            mp.Patch(fc="white", ec=INK, label="standard agent"),
            plt.Line2D([0], [0], color=C_RING_SOLO, lw=1.6, label="recruitment message"),
        ],
        loc="lower right", bbox_to_anchor=(1.0, 0.0), fontsize=7.4, handlelength=1.4,
    )
    fig.savefig(FIG / "fig_architecture.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_kinetics() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.6), sharey=True)
    spec = {("ring", "solo"): C_RING_SOLO, ("ring", "split"): C_RING_SPLIT, ("complete", "solo"): C_CMP_SOLO, ("complete", "split"): C_CMP_SPLIT}
    for ax, topo in zip(axes, ("ring", "complete")):
        for harm in ("solo", "split"):
            rows = sorted([r for r in kin if r["topology"] == topo and r["harm"] == harm], key=lambda r: int(r["round"]))
            x = [int(r["round"]) for r in rows]
            m = [float(r["infected_mean"]) for r in rows]
            lo = [float(r["ci_lo"]) for r in rows]
            hi = [float(r["ci_hi"]) for r in rows]
            c = spec[(topo, harm)]
            ax.fill_between(x, lo, hi, color=c, alpha=0.16, lw=0)
            ax.plot(x, m, color=c, lw=2.0, label=harm, ls="-" if harm == "solo" else "--")
        ax.set_title(f"{topo.capitalize()} topology")
        ax.set_xlabel("round")
        ax.set_xticks(range(0, 10))
        ax.grid(axis="y", color=GRID)
        ax.set_ylim(0.8, 10.2)
        ax.legend(loc="upper left", title="credential", fontsize=7.6, title_fontsize=7.6)
    axes[0].set_ylabel("mean infected agents (of 10)")
    fig.tight_layout()
    fig.savefig(FIG / "fig_kinetics.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_exfil() -> None:
    rows = []
    for topo in ("ring", "complete"):
        for harm in ("split", "solo"):
            rows.append((f"A1 free flow, {topo}, {harm}", arm_row("A1", topo, harm), C_RING_SOLO if topo == "ring" else C_CMP_SOLO))
    for d in ("D1", "D2", "D3", "D5"):
        rows.append((f"A3 gated {d}, ring, split", arm_row("A3", "ring", "split", d), GREEN))
    clean = [r for r in arms if r["arm"] in ("A0", "A3c")]
    kc = sum(int(r["observed_exfiltrations"]) for r in clean)
    nc = sum(int(r["episodes"]) for r in clean)
    fig, ax = plt.subplots(figsize=(6.3, 3.0))
    labels = []
    for i, (lab, r, c) in enumerate(rows):
        k, n = int(r["observed_exfiltrations"]), int(r["episodes"])
        lo, hi = wilson(k, n)
        ax.plot([lo, hi], [i, i], color=c, lw=2.4, solid_capstyle="round")
        ax.plot([k / n], [i], "o", color=c, ms=6.5, mfc="white" if k == 0 else c, mew=1.8)
        ax.text(1.03, i, f"{k}/{n}", va="center", fontsize=8, color=INK)
        labels.append(lab)
    i = len(rows)
    lo, hi = wilson(kc, nc)
    ax.plot([lo, hi], [i, i], color=MUTED, lw=2.4, solid_capstyle="round")
    ax.plot([kc / nc], [i], "o", color=MUTED, ms=6.5, mfc="white", mew=1.8)
    ax.text(1.03, i, f"{kc}/{nc}", va="center", fontsize=8, color=INK)
    labels.append("A0 + A3c clean control (pooled)")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7.8)
    ax.invert_yaxis()
    ax.set_xlim(-0.02, 1.0)
    ax.set_xlabel("full-credential exfiltration rate (95% Wilson interval)")
    ax.grid(axis="x", color=GRID)
    fig.tight_layout()
    fig.savefig(FIG / "fig_exfil.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_detection() -> None:
    seen = [r for r in panel_a if r["playbook"] == "seen"]
    held = [r for r in panel_a if r["playbook"] == "held_out"]
    dets = [r["detector"] for r in seen]
    fig, axes = plt.subplots(1, 3, figsize=(6.3, 2.5), gridspec_kw={"width_ratios": [1, 1, 0.9]})
    ax = axes[0]
    au = [float(r["auroc"]) for r in seen]
    ax.bar(dets, au, color=C_CMP_SOLO, width=0.62)
    ax.set_ylim(0.9, 1.012)
    ax.set_title("AUROC, seen playbooks")
    for i, v in enumerate(au):
        ax.text(i, v + 0.002, f"{v:.3f}", ha="center", fontsize=7.4)
    ax.grid(axis="y", color=GRID)
    ax = axes[1]
    fp = [float(r["fpr"]) * 100 for r in seen]
    ax.bar(dets, fp, color=C_RING_SPLIT, width=0.62)
    ax.axhline(0.5, color=C_RING_SOLO, lw=1.6, ls="--")
    ax.text(len(dets) - 0.45, 1.25, "target 0.5%", ha="right", fontsize=7.4, color=INK, bbox=dict(fc="white", ec="none", pad=1.2))
    ax.set_title("Realized FPR (%)")
    for i, v in enumerate(fp):
        ax.text(i, v + 0.15, f"{v:.1f}", ha="center", fontsize=7.4)
    ax.set_ylim(0, max(fp) * 1.25)
    ax.grid(axis="y", color=GRID)
    ax = axes[2]
    ax.axis("off")
    nneg = ", ".join(sorted({r["negative_messages"] for r in held}))
    ax.text(0.0, 0.62, "Held-out playbook\n(Style 2)", fontsize=8.6, fontweight="bold", color=INK, va="center")
    ax.text(0.0, 0.25, f"negative messages: {nneg}\nAUROC and FPR\nundefined (n/a)\nTPR saturated at 1.0", fontsize=7.8, color=INK, va="center")
    fig.tight_layout()
    fig.savefig(FIG / "fig_detection.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_gating() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(6.3, 2.4))
    dets = [r["defense"] for r in paired]
    y = list(range(len(dets)))
    ax = axes[0]
    for i, r in enumerate(paired):
        v, lo, hi = float(r["exfiltration_reduction"]), float(r["effect_ci_lo"]), float(r["effect_ci_hi"])
        ax.plot([lo, hi], [i, i], color=GREEN, lw=2.4, solid_capstyle="round")
        ax.plot([v], [i], "o", color=GREEN, ms=6.5)
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels(dets)
    ax.invert_yaxis()
    ax.set_xlim(-0.1, 0.8)
    ax.set_title("Exfiltration reduction")
    ax.grid(axis="x", color=GRID)
    ax = axes[1]
    for i, r in enumerate(paired):
        v, lo, hi = float(r["utility_loss"]), float(r["utility_loss_ci_lo"]), float(r["utility_loss_ci_hi"])
        ax.plot([lo, hi], [i, i], color=C_RING_SPLIT, lw=2.4, solid_capstyle="round")
        ax.plot([v], [i], "o", color=C_RING_SPLIT, ms=6.5)
    ax.set_yticks(y)
    ax.set_yticklabels([])
    ax.invert_yaxis()
    ax.set_xlim(0, 0.1)
    ax.set_title("Utility loss (0 to 1)")
    ax.grid(axis="x", color=GRID)
    ax = axes[2]
    share = {r["defense"]: float(r["llm_call_share"]) for r in panel_b}
    ax.barh(y, [share[d] for d in dets], color=C_CMP_SPLIT, height=0.55)
    ax.set_yticks(y)
    ax.set_yticklabels([])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_title("LLM call share")
    ax.grid(axis="x", color=GRID)
    fig.tight_layout()
    fig.savefig(FIG / "fig_gating.pdf", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ tables
def write_table(name: str, header: list[str], rows: list[list[str]], align: str) -> None:
    lines = [r"\begin{tabular}{" + align + "}", r"\toprule", " & ".join(header) + r" \\", r"\midrule"]
    lines += [" & ".join(r) + r" \\" for r in rows]
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / f"{name}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def f2(x: str | float) -> str:
    return f"{float(x):.2f}"


def f3(x: str | float) -> str:
    return f"{float(x):.3f}"


def tables() -> None:
    # design: planned vs executed
    exe = {}
    for r in arms:
        exe[r["arm"]] = exe.get(r["arm"], 0) + int(r["episodes"])
    desc = {
        "A0": ("Clean control", "ring, complete", "clean"),
        "A1": ("Free-flow infection", "ring, complete", "solo, split"),
        "A3": ("Online gating (D1, D2, D3, D5)", "ring", "split"),
        "A3c": ("Gate cost on benign swarms", "ring", "clean"),
    }
    rows = [[k, desc[k][0], desc[k][1], desc[k][2], str(PLANNED[k]), str(exe[k])] for k in ("A0", "A1", "A3", "A3c")]
    rows.insert(2, ["A2", "Offline detection (re-scoring A0 and A1)", "ring, complete", "solo, split", "reused", "reused"])
    write_table("tab_design", ["Arm", "Description", "Topology", "Credential", "Planned", "Executed"], rows, "llllrr")

    # kinetics
    rows = []
    for topo in ("ring", "complete"):
        for harm in ("solo", "split"):
            cells = []
            for rd in (3, 6, 9):
                r = next(x for x in kin if x["topology"] == topo and x["harm"] == harm and int(x["round"]) == rd)
                cells.append(f"{f2(r['infected_mean'])} [{f2(r['ci_lo'])}, {f2(r['ci_hi'])}]")
            rows.append([topo.capitalize(), harm, *cells])
    write_table("tab_kinetics", ["Topology", "Credential", "Round 3", "Round 6", "Round 9"], rows, "llccc")

    # arms
    rows = []
    for r in arms:
        k, n = int(r["observed_exfiltrations"]), int(r["episodes"])
        lo, hi = wilson(k, n)
        rows.append([r["arm"], r["topology"], r["harm"], r["defense"] or "none", f"{k}/{n}", f"[{lo:.2f}, {hi:.2f}]"])
    write_table("tab_arms", ["Arm", "Topology", "Credential", "Gate", "Exfiltrated", "95\\% Wilson"], rows, "lllcrc")

    # detection
    rows = []
    for r in panel_a:
        pb = "seen" if r["playbook"] == "seen" else "held out"
        auroc = f3(r["auroc"]) if r["auroc"] else "n/a"
        fpr = f"{float(r['fpr']) * 100:.1f}" if r["fpr"] else "n/a"
        rows.append([r["detector"], pb, f3(r["tpr"]), auroc, fpr, r["negative_messages"], r["positive_messages"]])
    write_table("tab_detection", ["Detector", "Playbook", "TPR", "AUROC", "FPR (\\%)", "Neg. msgs", "Pos. msgs"], rows, "llcccrr")

    # gating
    rows = []
    for r in paired:
        rows.append([
            r["defense"], r["pairs_complete"], f3(r["exfiltration_reduction"]),
            f"[{f3(r['effect_ci_lo'])}, {f3(r['effect_ci_hi'])}]", f"{r['mcnemar_b']}/{r['mcnemar_c']}",
            f3(r["holm_p"]), f3(r["utility_loss"]),
        ])
    write_table("tab_gating", ["Gate", "Pairs", "Reduction", "Effect interval", "b/c", "Holm $p$", "Utility loss"], rows, "lccccrc")

    # cost
    rows = [[billing["provider"], billing["billing_unit"], billing["attempts"], billing["provider_returns"], f3(billing["known_cost"]), billing["attempts_with_unknown_usage"]]]
    write_table("tab_cost", ["Provider", "Unit", "Attempts", "Model calls", "Known cost", "Attempts, usage unknown"], rows, "llrrrr")


def numbers() -> None:
    test_eps = sum(int(r["episodes"]) for r in arms)
    sel = lambda arm_, t, h, d="": arm_row(arm_, t, h, d)  # noqa: E731
    seen = [r for r in panel_a if r["playbook"] == "seen"]
    clean = [r for r in arms if r["arm"] in ("A0", "A3c")]
    gated = [r for r in arms if r["arm"] == "A3"]
    kin9 = {(r["topology"], r["harm"]): float(r["infected_mean"]) for r in kin if int(r["round"]) == 9}

    def frac(r: dict[str, str]) -> str:
        return f"{r['observed_exfiltrations']}/{r['episodes']}"

    eps = read("episodes.csv")

    def mean_inf(arm_: str, defense: str) -> float:
        v = [float(r["n_infected"] or 0) for r in eps if r["arm"] == arm_ and r["defense"] == defense and r["topology"] == "ring" and r["harm"] == "split"]
        return sum(v) / len(v)

    gate_inf = [mean_inf("A3", d) for d in ("D1", "D2", "D3", "D5")]
    m = {
        "InfBase": f"{mean_inf('A1', ''):.1f}", "InfGateMin": f"{min(gate_inf):.1f}", "InfGateMax": f"{max(gate_inf):.1f}",
        "NPilot": PILOT, "NTrain": TRAIN, "NTest": test_eps, "NEpisodes": PILOT + TRAIN + test_eps,
        "NCalls": f"{int(billing['provider_returns']):,}".replace(",", r"\,"),
        "CostKnown": f3(billing["known_cost"]),
        "AuditN": intent["sample_size"], "AuditRate": f"{intent['agreement_rate'] * 100:.0f}",
        "AuditLo": f3(intent["wilson_ci_lo"]),
        "ExfilRingSplit": frac(sel("A1", "ring", "split")), "ExfilCmpSplit": frac(sel("A1", "complete", "split")),
        "ExfilRingSolo": frac(sel("A1", "ring", "solo")), "ExfilCmpSolo": frac(sel("A1", "complete", "solo")),
        "CleanLeaks": sum(int(r["observed_exfiltrations"]) for r in clean), "CleanN": sum(int(r["episodes"]) for r in clean),
        "GatedLeaks": sum(int(r["observed_exfiltrations"]) for r in gated), "GatedN": sum(int(r["episodes"]) for r in gated),
        "InfRingSolo": f"{kin9[('ring', 'solo')]:.1f}", "InfRingSplit": f"{kin9[('ring', 'split')]:.1f}",
        "InfCmpSolo": f"{kin9[('complete', 'solo')]:.1f}", "InfCmpSplit": f"{kin9[('complete', 'split')]:.1f}",
        "AurocMin": f3(min(float(r["auroc"]) for r in seen)), "AurocMax": f3(max(float(r["auroc"]) for r in seen)),
        "FprSeen": f"{float(seen[0]['fpr']) * 100:.1f}", "NegSeen": seen[0]["negative_messages"],
        "McnemarP": f"{float(paired[0]['mcnemar_p']):.1f}", "PairsN": paired[0]["pairs_complete"],
        "UtilMax": f3(max(float(r["utility_loss"]) for r in paired)),
        "HRows": h2["rows_exposed"], "HEpisodes": h2["episodes"],
    }
    lines = ["% Generated by scripts/make_paper_assets.py. Do not edit."]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in m.items()]
    (OUT / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    for f in (fig_architecture, fig_kinetics, fig_exfil, fig_detection, fig_gating):
        f()
    tables()
    numbers()
    print("assets written to", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
