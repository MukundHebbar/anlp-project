#!/usr/bin/env python3
"""Figures for the LaTeX GRPO transfer report (docs/reports/latex/figures/*.pdf).

    uv run python scripts/make_report_figures.py
"""

import importlib.util
import json
import statistics as st
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "reports" / "latex" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
EV = ROOT / "artifacts" / "opd" / "evals"
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.3, "savefig.bbox": "tight"})

spec = importlib.util.spec_from_file_location("rm", ROOT / "scripts" / "report_grpo_matrix.py")
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)


def load(p):
    return [json.loads(line) for line in open(p)]


def rolling(xs, w=8):
    return [st.mean(xs[max(0, i - w + 1):i + 1]) for i in range(len(xs))]


# ---------------------------------------------------------------- 1. transfer heatmap (Δ vs untrained, primary metrics)
arms = [("SOLVE only", "v3-grpo-lr1e-5-solve-step66"), ("JUDGE only", "v3-drgrpo-judge-step26"),
        ("RECONSTRUCT only", "v3-drgrpo-reconstruct-step104"), ("Mixed (1/3 each)", "v3-grpo-mixed-lr2e-5-step75")]
cols = [("solve_acc", "SOLVE acc", 100), ("judge_step", "JUDGE step %", 100), ("judge_j", "JUDGE Youden J", 100),
        ("recon_score", "RECON PC-v4", 1)]
base = rm.per_question(rm.TEST / "v3-pass4-2b")
grid = []
for _, d in arms:
    v = rm.per_question(rm.TEST / d)
    grid.append([scale * st.mean(v[m][u] - base[m][u] for u in set(v[m]) & set(base[m])) for m, _, scale in cols])
fig, ax = plt.subplots(figsize=(5.6, 2.6))
im = ax.imshow(grid, cmap="RdBu", vmin=-45, vmax=45)
ax.set_xticks(range(len(cols)), [c[1] for c in cols], rotation=25, ha="right")
ax.set_yticks(range(len(arms)), [a[0] for a in arms])
ax.grid(False)
for i, row in enumerate(grid):
    for j, x in enumerate(row):
        ax.text(j, i, f"{x:+.1f}", ha="center", va="center", fontsize=9, color="white" if abs(x) > 25 else "black")
ax.set_xlabel("measured on (test, Δ vs untrained 2B, points)")
ax.set_ylabel("trained on")
fig.colorbar(im, ax=ax, fraction=0.04)
fig.savefig(FIG / "transfer_heatmap.pdf")
plt.close(fig)

# ---------------------------------------------------------------- 2. single-task training curves
runs = [("SOLVE (lr 1e-5, 32x8)", EV / "solve-p1-lr1e-5" / "train-metrics.jsonl"),
        ("SOLVE first recipe (lr 5e-5, 8x8)", EV / "v3-drgrpo-dev" / "train-metrics-solve.jsonl"),
        ("JUDGE (lr 5e-5, 8x8)", EV / "v3-drgrpo-dev" / "train-metrics-judge.jsonl"),
        ("RECONSTRUCT (lr 5e-5, 8x8)", EV / "v3-drgrpo-dev" / "train-metrics-reconstruct.jsonl")]
fig, axes = plt.subplots(1, 3, figsize=(10, 2.8))
for name, p in runs:
    m = load(p)
    steps = [r["step"] for r in m]
    axes[0].plot(steps, rolling([r["reward_mean"] for r in m]), label=name)
    axes[1].plot(steps, rolling([r["mean_len"] / 1000 for r in m]), label=name)
    axes[2].plot(steps, rolling([100 * r["truncation_rate"] for r in m]), label=name)
axes[0].set_title("training reward (8-step rolling)")
axes[1].set_title("mean answer length (k tokens)")
axes[2].set_title("truncated at 16k (%)")
for a in axes:
    a.set_xlabel("step")
axes[0].legend(fontsize=7)
fig.savefig(FIG / "curves_single.pdf")
plt.close(fig)

# ---------------------------------------------------------------- 3. mixed run per-task curves
m = load(EV / "mixed-lr2e-5" / "train-metrics.jsonl")
steps = [r["step"] for r in m]
fig, axes = plt.subplots(1, 3, figsize=(10, 2.8))
for t, c in (("solve", "C0"), ("judge", "C1"), ("reconstruct", "C2")):
    axes[0].plot(steps, rolling([r["per_task"][t]["reward_mean"] for r in m]), c, label=t.upper())
    axes[1].plot(steps, rolling([r["per_task"][t]["mean_len"] / 1000 for r in m]), c, label=t.upper())
    axes[2].plot(steps, rolling([r["per_task"][t]["adv_abs_mean"] for r in m]), c, label=t.upper())
for k in (72, 75):
    axes[0].axvline(k, color="grey", ls=":", lw=0.8)
axes[0].set_title("reward per task (8-step rolling)")
axes[1].set_title("mean answer length (k tokens)")
axes[2].set_title("mean |advantage|")
for a in axes:
    a.set_xlabel("step")
axes[0].legend(fontsize=7)
fig.savefig(FIG / "curves_mixed.pdf")
plt.close(fig)

# ---------------------------------------------------------------- 4. gap to 9B on each own task
nine = rm.per_question(rm.TEST / "v3-pass4-9b")
spec_dirs = {"solve_acc": "v3-grpo-lr1e-5-solve-step66", "judge_step": "v3-drgrpo-judge-step26",
             "recon_score": "v3-drgrpo-reconstruct-step104"}
mixed = rm.per_question(rm.TEST / "v3-grpo-mixed-lr2e-5-step75")
labels = {"solve_acc": "SOLVE acc", "judge_step": "JUDGE step %", "recon_score": "RECON PC-v4"}
fig, ax = plt.subplots(figsize=(6, 2.6))
w = 0.2
for i, (mkey, d) in enumerate(spec_dirs.items()):
    sc = 1 if mkey == "recon_score" else 100
    vals = [sc * st.mean(base[mkey].values()), sc * st.mean(rm.per_question(rm.TEST / d)[mkey].values()),
            sc * st.mean(mixed[mkey].values()), sc * st.mean(nine[mkey].values())]
    for j, (v, lab) in enumerate(zip(vals, ["untrained 2B", "single-task GRPO", "mixed GRPO", "Qwen3.5-9B"])):
        ax.bar(i + (j - 1.5) * w, v, w, color=f"C{j}", label=lab if i == 0 else None)
        ax.text(i + (j - 1.5) * w, v + 1, f"{v:.0f}", ha="center", fontsize=7)
ax.set_xticks(range(3), [labels[k] for k in spec_dirs])
ax.set_ylim(0, 100)
ax.legend(fontsize=7, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.22))
fig.savefig(FIG / "own_task_vs_9b.pdf")
plt.close(fig)
print("figures written to", FIG)
