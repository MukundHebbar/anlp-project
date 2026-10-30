"""Figure: CAV gain predicted before judging (semi-synthetic, real dev answer structure) vs the observed gain.

    python phase3/fig_prediction.py --semisynth phase3/runs/semisynth_dev.json --report phase3/runs/analysis/report.json
"""
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semisynth", default="phase3/runs/semisynth_dev.json")
    ap.add_argument("--report", default="phase3/runs/analysis/report.json")
    ap.add_argument("--out", default="paper/figures/prediction_vs_outcome.png")
    a = ap.parse_args()
    ss, rep = json.load(open(a.semisynth)), json.load(open(a.report))
    BLUE, ORANGE, GRAY, SURF, INK2, GRID = "#2a78d6", "#eb6834", "#8a8984", "#fcfcfb", "#52514e", "#e6e5e1"
    plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID, "axes.grid": True,
                         "grid.color": GRID, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9.5,
                         "lines.linewidth": 2, "xtick.color": INK2, "ytick.color": INK2, "axes.labelcolor": INK2})
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for rho, col, lab in ((0.3, BLUE, "predicted, shared judge error 0.3"), (0.6, GRAY, "predicted, shared judge error 0.6")):
        pts = sorted((r["within_auroc"], 100 * r["gain"]) for r in ss if r["rho_s"] == rho)
        ax.plot(*zip(*pts), color=col, marker="o", markersize=6, markeredgecolor=SURF, markeredgewidth=1.5, label=lab)
    w_dev = rep["dev"]["auroc"]["within_auroc_prob"][0]
    p = rep["primary"]
    d, lo, hi = (100 * x for x in (p["diff_vs_majority"][0], *p["diff_vs_majority"][1]))
    ax.errorbar([w_dev], [d], yerr=[[d - lo], [hi - d]], fmt="s", color=ORANGE, markersize=8, capsize=4,
                label="observed (test+extra), at dev within-AUROC")
    ax.axhline(0, color=INK2, linewidth=0.8)
    ax.set_xlabel("judge's within-question AUROC")
    ax.set_ylabel("CAV gain over majority (points)")
    ax.set_title("Registered prediction vs outcome", fontweight="bold", fontsize=10)
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")
    fig.savefig(a.out, dpi=160, bbox_inches="tight")
    print("wrote", a.out, "dev within", round(w_dev, 3), "observed", round(d, 2))


if __name__ == "__main__":
    main()
