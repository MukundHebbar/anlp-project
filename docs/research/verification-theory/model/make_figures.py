"""Figures for theory-and-plan.md. Fig 1 is recomputed; figs 2-5 use the numbers printed in m5/m7/m8/m9 *.out."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from m2_selection import run

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")
os.makedirs(OUT, exist_ok=True)
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID,
                     "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
                     "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlecolor": INK, "lines.linewidth": 2})
fits = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fits.npy"), allow_pickle=True).item()


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=160, bbox_inches="tight")
    plt.close(fig)


# ---- Fig 1: picking gain vs global AUROC and vs within AUROC ----
a, b, rho = fits["test"]
pts = []
for gamma in [0.0, 0.3, 0.6, 1.0]:
    for d in [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
        o = run(a, b, rho, gamma, d, 0.6, Q=60_000)
        pts.append((o["g_auc"], o["w_auc"], 100 * (o["bayes"] - o["maj"])))
pts = np.array(pts)
fig, ax = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
ax[0].scatter(pts[:, 0], pts[:, 2], s=64, color=BLUE, edgecolor=SURF, linewidth=2, zorder=3)
ax[0].set_xlabel("global AUROC (what Phase 2 reported)")
ax[0].set_ylabel("picking gain over majority (points)")
ax[0].set_title("Global AUROC does not predict picking")
o = np.argsort(pts[:, 1])
ax[1].plot(pts[o, 1], pts[o, 2], color=ORANGE, alpha=0.35, zorder=2)
ax[1].scatter(pts[:, 1], pts[:, 2], s=64, color=ORANGE, edgecolor=SURF, linewidth=2, zorder=3)
ax[1].set_xlabel("within-question AUROC")
ax[1].set_title("Within-question AUROC does")
for x in ax:
    x.axhline(0, color=INK2, linewidth=1)
fig.text(0.01, -0.04, "Model of the test split, N = 4, Bayes picking rule; each point is one (difficulty signal, "
         "within signal) setting.", color=INK2, fontsize=8.5)
save(fig, "fig1_auroc_vs_gain.png")

# ---- Fig 2: compute frontier (m8_adaptive.out) ----
maj = [(4, 74.0), (6, 76.6), (8, 77.7), (12, 78.2), (16, 78.1), (24, 78.3), (32, 78.2)]
cav05 = [(4, 74.0), (6.8, 78.1), (11.2, 80.4), (19.5, 82.3)]
cav10 = [(4, 74.0), (6.8, 79.7), (11.2, 83.3), (19.5, 86.3)]
fig, ax = plt.subplots(figsize=(6.4, 4))
for data, col, lab in [(maj, GRAY, "majority vote"), (cav05, BLUE, "CAV, within AUROC 0.64"),
                       (cav10, ORANGE, "CAV, within AUROC 0.76")]:
    x, y = zip(*data)
    ax.plot(x, y, color=col, marker="o", markersize=8, markeredgecolor=SURF, markeredgewidth=2, label=lab)
    ax.annotate(lab, (x[-1], y[-1]), xytext=(6, 0), textcoords="offset points", va="center", color=INK, fontsize=9)
ax.axhline(78.3, color=GRAY, linestyle=(0, (2, 3)), linewidth=1)
ax.annotate("majority limit 78.3", (4.2, 78.6), color=INK2, fontsize=8.5)
ax.axhline(82.8, color=INK2, linestyle=(0, (2, 3)), linewidth=1)
ax.annotate("pass@4 = 82.8", (4.2, 83.1), color=INK2, fontsize=8.5)
ax.set_xlabel("average cost per question (attempt = 1, judge pass = 0.3)")
ax.set_ylabel("accuracy (%)")
ax.set_title("Contest-adaptive verification passes the majority plateau")
ax.set_xlim(3, 33)
ax.legend(loc="lower right", frameon=False, fontsize=8.5)
save(fig, "fig2_compute_frontier.png")

# ---- Fig 3: length law and liveness (m5_length.out) ----
fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.6))
T = np.logspace(0, np.log10(300), 100)
for A, col in [(0.8, BLUE), (0.9, ORANGE)]:
    L = A / (1 - A)
    ax[0].plot(T, (T - 1 + L) / (2 * T - 1 + L), color=col, label=f"step AUROC {A}")
ax[0].axhspan(0.50, 0.53, xmin=0.78, xmax=0.95, color=GRAY, alpha=0.25)
ax[0].annotate("error feature on own\nattempts: 0.50–0.53", (60, 0.555), fontsize=8.5, color=INK2)
ax[0].set_xscale("log"); ax[0].set_xlabel("steps per solution (T)"); ax[0].set_ylabel("solution-level AUROC")
ax[0].set_title("Max-pooled detector: (T−1+L)/(2T−1+L)")
ax[0].legend(frameon=False, fontsize=8.5, loc="upper right")
Tl = [5, 10, 25, 50, 100, 200]
perfect = [0.995, 0.979, 0.898, 0.752, 0.594, 0.513]
maxp = [0.617, 0.566, 0.523, 0.507, 0.510, 0.502]
filt = [0.645, 0.591, 0.569, 0.558, 0.564, 0.567]
for y, col, lab in [(perfect, GRAY, "perfect detector, max-pooled"), (maxp, BLUE, "0.80 detector, max-pooled"),
                    (filt, ORANGE, "0.80 detector, liveness filter")]:
    ax[1].plot(Tl, y, color=col, marker="o", markersize=8, markeredgecolor=SURF, markeredgewidth=2, label=lab)
ax[1].set_xscale("log"); ax[1].set_xlabel("steps per solution (T)"); ax[1].set_ylim(0.47, 1.03)
ax[1].set_title("With retractions, existence ≠ liveness")
ax[1].legend(frameon=False, fontsize=8.5, loc="upper right")
save(fig, "fig3_length_liveness.png")

# ---- Fig 4: training regimes (m9_training.out) ----
regimes = ["natural", "globally balanced\n(Phase 2)", "per-question\nbalanced, N=4", "per-question\nbalanced, N=16",
           "pairwise, N=16"]
glob = [0.864, 0.867, 0.732, 0.740, 0.755]
within = [0.670, 0.670, 0.730, 0.740, 0.739]
y = np.arange(len(regimes))
fig, ax = plt.subplots(figsize=(6.6, 3.8))
ax.barh(y - 0.19, glob, height=0.36, color=BLUE, label="global AUROC", edgecolor=SURF, linewidth=2)
ax.barh(y + 0.19, within, height=0.36, color=ORANGE, label="within-question AUROC", edgecolor=SURF, linewidth=2)
for i in range(len(y)):
    ax.text(glob[i] + 0.004, y[i] - 0.19, f"{glob[i]:.2f}", va="center", fontsize=8.5, color=INK)
    ax.text(within[i] + 0.004, y[i] + 0.19, f"{within[i]:.2f}", va="center", fontsize=8.5, color=INK)
ax.set_yticks(y, regimes); ax.invert_yaxis(); ax.set_xlim(0.5, 1.0)
ax.set_xlabel("AUROC on fresh questions (model, 1,024 training examples)")
ax.set_title("The right data lowers global AUROC and raises within")
ax.legend(frameon=False, fontsize=8.5, loc="lower right"); ax.grid(axis="y", visible=False)
save(fig, "fig4_training_regimes.png")

# ---- Fig 5: where pairs and headroom live (m7_analytic.out) ----
mid = np.arange(0.05, 1.0, 0.1)
pairs = [4.4, 7.5, 9.4, 10.7, 11.3, 12.0, 12.2, 12.1, 11.4, 9.1]
head = [13.3, 18.5, 18.4, 16.2, 12.8, 9.4, 6.2, 3.4, 1.5, 0.3]
fig, ax = plt.subplots(figsize=(6.4, 3.6))
ax.plot(mid, pairs, color=BLUE, marker="o", markersize=8, markeredgecolor=SURF, markeredgewidth=2)
ax.plot(mid, head, color=ORANGE, marker="o", markersize=8, markeredgecolor=SURF, markeredgewidth=2)
ax.annotate("within-question pairs (what AUROC averages)", (mid[6], pairs[6]), xytext=(-40, 10),
            textcoords="offset points", fontsize=8.5, color=INK)
ax.annotate("picking headroom", (mid[3], head[3]), xytext=(10, 2), textcoords="offset points", fontsize=8.5, color=INK)
ax.set_xlabel("question solve rate p"); ax.set_ylabel("share (%)")
ax.set_title("Headroom sits on hard questions (mean p 0.33 vs 0.54)")
save(fig, "fig5_headroom_by_difficulty.png")
print("figures written to", os.path.abspath(OUT))
