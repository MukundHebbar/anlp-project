"""LaTeX tables and the real compute-frontier figure for the paper, from phase3/analyze.py's report.json.

    python phase3/paper_tables.py --report phase3/runs/analysis/report.json --paper paper
Writes paper/tables/{stage0,pools,configs,selection}.tex and paper/figures/real_frontier.png.
"""

import argparse
import json
from pathlib import Path

# Model predictions quoted next to the measurements (docs/research/verification-theory, m3/m10)
MODEL = {"auroc_1_sampled": 0.526, "auroc_4_sampled_share": 0.568, "latent": 0.715, "p4of4_wrong": 0.005,
         "configs": {"majority right": 0.717, "unwinnable": 0.172, "tie": 0.080, "overturn": 0.030}}


def boxed(tex: str) -> str:
    """Fit every tabular to the line width (columns of a two-column page, or the page for table*)."""
    tex = tex.replace("\\begin{tabular}", "\\resizebox{\\linewidth}{!}{\\begin{tabular}")
    return tex.replace("\\end{tabular}", "\\end{tabular}}")


def ci(x, nd=3):
    return f"{x[0]:.{nd}f} [{x[1][0]:.{nd}f}, {x[1][1]:.{nd}f}]"


def stage0(rep):
    j = rep["test"]["judge_first4"]
    rows = [
        ("Share of ``incorrect'' verdicts (sampled)", f"{j['incorrect_share_sampled']:.3f}", "0.04 (Phase 2 dev)"),
        ("Hit rate $H$ / false-alarm rate $F$", f"{j['hit_rate']:.3f} / {j['false_alarm_rate']:.3f}", "0.074 / 0.022"),
        ("$d'=z(H)-z(F)$", f"{j['dprime']:.2f}", "0.57"),
        ("AUROC, 1 sampled verdict", f"{j['auroc_1_sampled']:.3f}", f"{MODEL['auroc_1_sampled']:.3f}"),
        ("AUROC, share of 4 sampled verdicts", f"{j['auroc_4_sampled_share']:.3f}", f"{MODEL['auroc_4_sampled_share']:.3f}"),
        ("AUROC, verdict probability, 1 chain", f"{j['auroc_prob_1chain']:.3f}", "--"),
        ("AUROC, verdict probability, mean of 4 chains", f"{j['auroc_prob_mean4']:.3f}", f"$\\le${MODEL['latent']:.3f}"),
        ("AUROC, direct probability (no reasoning)", f"{j['auroc_direct']:.3f}", "--"),
        ("$P$(4 of 4 ``incorrect'' $\\mid$ wrong), observed", f"{j['observed_p4of4_wrong']:.4f}", f"{MODEL['p4of4_wrong']:.3f}"),
        ("\\quad same, if verdicts were independent", f"{j['binomial_p4of4_wrong']:.5f}", "0.00003"),
        ("Chains reaching a verdict", f"{j['reached_label_rate']:.3f}", "0.89 (Phase 2)"),
    ]
    body = "\n".join(f"{a} & {b} & {c} \\\\" for a, b, c in rows)
    return ("\\begin{table}[t]\n\\centering\\small\n\\begin{tabular}{@{}lcc@{}}\n\\toprule\n"
            "Test attempts 0--3, 4 chains each & Measured & Model \\\\\n\\midrule\n" + body +
            f"\n\\bottomrule\n\\end{{tabular}}\n\\caption{{Stage 0: the untrained mixed judge on its own test attempts "
            f"({j['n_attempts']} answered attempts, {100*j['share_wrong']:.1f}\\% wrong). ``Model'' is the latent judge fitted "
            "to Phase-2 single-verdict flag rates (\\S\\ref{sec:lenient}).}\n\\label{tab:stage0}\n\\end{table}\n")


def pools(rep):
    lines = []
    for s in ("dev", "test", "extra"):
        if s not in rep:
            continue
        r, au = rep[s], rep[s]["auroc"]
        lines.append(f"{s} & {r['single_attempt']:.3f} & chain & {au['global_auroc_prob']:.3f} & "
                     f"{ci(au['within_auroc_prob'])} & {ci(au['contested_within_auroc_prob'])} \\\\")
        lines.append(f" & & direct & {au['global_auroc_direct']:.3f} & {ci(au['within_auroc_direct'])} & "
                     f"{ci(au['contested_within_auroc_direct'])} \\\\")
        lines.append(f" & & length & {au['global_auroc_length']:.3f} & {ci(au['within_auroc_length'])} & -- \\\\")
    return ("\\begin{table*}[t]\n\\centering\\small\n\\begin{tabular}{@{}lcclccc@{}}\n\\toprule\n"
            "Set & Single attempt & Score & Pooled AUROC & Within-question AUROC & Contested within-question AUROC \\\\\n"
            "\\midrule\n" + "\n".join(lines) +
            "\n\\bottomrule\n\\end{tabular}\n\\caption{Judging own attempts (16 per question; first chain). ``Length'' "
            "scores an attempt by its token count. Brackets: 95\\% question-cluster bootstrap intervals.}\n"
            "\\label{tab:pools}\n\\end{table*}\n")


def configs(rep):
    keys = ["majority right", "tie", "overturn", "unwinnable"]
    lines = [f"{s} & " + " & ".join(f"{rep[s]['configs_n4'].get(k, 0):.3f}" for k in keys) + " \\\\"
             for s in ("dev", "test", "extra") if s in rep]
    lines.append("model (test calibration) & " + " & ".join(f"{MODEL['configs'][k]:.3f}" for k in keys) + " \\\\")
    return ("\\begin{table}[t]\n\\centering\\small\n\\begin{tabular}{@{}lcccc@{}}\n\\toprule\n"
            "& Majority right & Tie & Overturn & Unwinnable \\\\\n\\midrule\n" + "\n".join(lines) +
            "\n\\bottomrule\n\\end{tabular}\n\\caption{Shares of 4-attempt configurations (random 4-subsets of the 16 "
            "attempts). Only ties and overturns can be won by a judge.}\n\\label{tab:configs}\n\\end{table}\n")


def selection(rep):
    rules = rep["eval"]["rules"]
    pick = lambda prefix: sorted(((k, v) for k, v in rules.items() if k.startswith(prefix)), key=lambda kv: kv[1]["cost"])
    show = []
    for k, v in pick("majority@"):
        if int(k.split("@")[1]) in (4, 8, 12, 16):
            show.append((f"Majority, $N={k.split('@')[1]}$", v))
    for k, v in pick("oracle@"):
        if int(k.split("@")[1]) == 16:
            show.append(("pass@16 (oracle)", v))
    for k, v in pick("ac@"):
        if k.split("@")[1] in ("0.8", "0.9", "0.99"):
            show.append((f"Adaptive-consistency, $t={k.split('@')[1]}$", v))
    for k, v in pick("bayes@"):
        if int(k.split("@")[1]) in (4, 16):
            show.append((f"Bayes aggregation, $N={k.split('@')[1]}$", v))
    for k, v in pick("argmax@"):
        if int(k.split("@")[1]) in (4, 16):
            show.append((f"Best-of-$N$ argmax, $N={k.split('@')[1]}$", v))
    keep = {"chain:16,8", "chain:12,8", "chain:8,4", "direct:8,4", "direct:12,4", "direct:16,4", "combo:16,8",
            "combo-cheap:8,4"}
    for name, c in rep["secondary"].items():
        if name not in keep:
            continue
        src, nm = name.split(":")
        n1, m = nm.split(",")
        star = "$^\\star$" if c["rule"] == rep["primary"]["rule"] else ""
        show.append((f"CAV ({src}), $N_1={n1}$, $m={m}${star}", rules[c["rule"]]))
    body = "\n".join(f"{n} & {100*v['acc']:.1f} & {v['cost']:.2f} & {v['tokens']/1000:.1f}k \\\\" for n, v in show)
    p = rep["primary"]
    return ("\\begin{table}[t]\n\\centering\\small\n\\begin{tabular}{@{}lccc@{}}\n\\toprule\n"
            "Rule & Acc. (\\%) & Cost & Tokens \\\\\n\\midrule\n" + body +
            f"\n\\bottomrule\n\\end{{tabular}}\n\\caption{{Selection on test $\\cup$ extra ({rep['eval']['questions']} "
            "questions), settings tuned on dev. Cost: attempt $=1$, judge chain $=0.3$, direct read $=0.05$; tokens: "
            "decoded tokens per question. $^\\star$: pre-registered primary rule.}\n\\label{tab:selection}\n\\end{table}\n")


def frontier(rep, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    BLUE, ORANGE, AQUA, GRAY, SURF, INK2, GRID = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984", "#fcfcfb", "#52514e", "#e6e5e1"
    plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID, "axes.grid": True,
                         "grid.color": GRID, "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
                         "lines.linewidth": 2, "xtick.color": INK2, "ytick.color": INK2, "axes.labelcolor": INK2})
    rules = rep["eval"]["rules"]
    fig, ax = plt.subplots(figsize=(6.4, 4))

    def series(prefix, col, lab, key=lambda k: True):
        pts = sorted((v["tokens"] / 1000, 100 * v["acc"]) for k, v in rules.items() if k.startswith(prefix) and key(k))
        if pts:
            x, y = zip(*pts)
            ax.plot(x, y, color=col, marker="o", markersize=7, markeredgecolor=SURF, markeredgewidth=2, label=lab)
    series("majority@", GRAY, "majority vote")
    series("ac@", AQUA, "adaptive-consistency")
    series("cav-chain@", ORANGE, "CAV, chain probability")
    series("cav-direct@", BLUE, "CAV, direct probability")
    ax.set_xlabel("decoded tokens per question (thousands)")
    ax.set_ylabel("accuracy (%)")
    ax.set_title("Own attempts of Qwen3.5-2B: accuracy vs compute", fontweight="bold")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.savefig(path, dpi=160, bbox_inches="tight")


def judges(reports: dict) -> str:
    """One row per judge (untrained, Stage-2 arms): criterion, sampled vs probability AUROC, within-question AUROC, CAV."""
    lines = []
    for name, rep in reports.items():
        j, au = rep["test"]["judge_first4"], rep["test"]["auroc"]
        cav = {k: v for k, v in rep.get("secondary", {}).items()}
        cc, cd = cav.get("chain:16,8"), cav.get("direct:16,8")
        lines.append(f"{name} & {j['incorrect_share_sampled']:.2f} & {j['dprime']:.2f} & {j['auroc_4_sampled_share']:.3f} & "
                     f"{j['auroc_prob_mean4']:.3f} & {j['auroc_direct']:.3f} & {au['global_auroc_prob']:.3f} & "
                     f"{au['within_auroc_prob'][0]:.3f} & {au['contested_within_auroc_prob'][0]:.3f} & "
                     + (f"{100*cc['acc']:.1f}" if cc else "--") + " & " + (f"{100*cd['acc']:.1f}" if cd else "--") + " \\\\")
    return ("\\begin{table*}[t]\n\\centering\\small\n\\begin{tabular}{@{}lcccccccccc@{}}\n\\toprule\n"
            "Judge & ``Incorrect'' share & $d'$ & AUROC (4 sampled) & AUROC (prob., 4 chains) & AUROC (direct) & "
            "Pooled AUROC & Within & Contested within & CAV chain & CAV direct \\\\\n\\midrule\n" + "\n".join(lines) +
            "\n\\bottomrule\n\\end{tabular}\n\\caption{Untrained and trained self-judges on the same test attempts. "
            "The first six columns use attempts 0--3 of each test question; within-question columns use all 16. CAV: "
            "$N_1=16$, $m=8$, accuracy (\\%) on test $\\cup$ extra.}\n\\label{tab:judges}\n\\end{table*}\n")


def scaling(rep, model_curves, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    BLUE, ORANGE, SURF, INK2, GRID = "#2a78d6", "#eb6834", "#fcfcfb", "#52514e", "#e6e5e1"
    plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID, "axes.grid": True,
                         "grid.color": GRID, "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
                         "lines.linewidth": 2, "xtick.color": INK2, "ytick.color": INK2, "axes.labelcolor": INK2})
    splits = [s for s in ("dev", "test") if s in rep and "curves" in rep[s]]
    fig, axes = plt.subplots(1, len(splits), figsize=(4.6 * len(splits), 3.6), sharey=True, squeeze=False)
    for ax, s in zip(axes[0], splits):
        obs, mod = rep[s]["curves"], model_curves[s]
        for key, col, lab in (("majority", BLUE, "majority vote"), ("pass", ORANGE, "pass@N")):
            ax.plot(obs["N"], [100 * x for x in obs[key]], color=col, marker="o", markersize=7, markeredgecolor=SURF,
                    markeredgewidth=2, label=f"{lab}, observed")
            ax.plot(mod["N"], [100 * x for x in mod[key]], color=col, linestyle=(0, (3, 2)), linewidth=1.5,
                    label=f"{lab}, model")
        ax.axhline(100 * mod["majority_limit"], color=INK2, linewidth=0.8, linestyle=":")
        ax.set_title(f"{s}: model fitted to Phase-2 N=4 only", fontweight="bold", fontsize=10)
        ax.set_xlabel("attempts per question N")
    axes[0][0].set_ylabel("accuracy (%)")
    axes[0][-1].legend(frameon=False, fontsize=8, loc="lower right")
    fig.savefig(path, dpi=160, bbox_inches="tight")


def trace_table(tf: dict) -> str:
    names = {"length": "Length (tokens)", "retractions": "Self-corrections (``wait'', ``actually'', \\dots)",
             "guesses": "Guess phrases (``let's assume'', \\dots)", "tags": "Final-answer tags"}
    lines = []
    for s in ("dev", "test"):
        if s not in tf:
            continue
        for k, lab in names.items():
            r = tf[s][k]
            lines.append(f"{s} & {lab} & {r['pooled_auroc']:.3f} & {r['within_auroc'][0]:.3f} & "
                         f"{r['contested_within_auroc'][0]:.3f} & {r['mean_right']:.1f} / {r['mean_wrong']:.1f} \\\\")
    return ("\\begin{table*}[t]\n\\centering\\small\n\\begin{tabular}{@{}llcccc@{}}\n\\toprule\n"
            "Set & Trace feature & Pooled AUROC & Within-question & Contested within & Mean (right / wrong) \\\\\n"
            "\\midrule\n" + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n\\caption{Judge-free trace "
            "features. They reach the pooled AUROC of the Phase-2 trained self-judge (0.665) because hard questions produce "
            "long, hesitant attempts, but are near chance on contested questions, where picking happens. Almost every right "
            "attempt contains self-corrections.}\n\\label{tab:trace}\n\\end{table*}\n")


def training_curves(metrics: dict, path):
    """Verdict reward, response length and truncation per GRPO step for each self-judge arm."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    COLS = {"global": "#2a78d6", "perq": "#eb6834"}
    LABS = {"global": "globally balanced (Phase-2 replica)", "perq": "per-question balanced"}
    SURF, INK2, GRID = "#fcfcfb", "#52514e", "#e6e5e1"
    plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID, "axes.grid": True,
                         "grid.color": GRID, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9,
                         "lines.linewidth": 2, "xtick.color": INK2, "ytick.color": INK2, "axes.labelcolor": INK2})
    fig, axes = plt.subplots(1, 3, figsize=(9.5, 2.8))
    for arm, path_m in metrics.items():
        rows = [json.loads(line) for line in open(path_m)]
        st = [r["step"] for r in rows]
        for ax, key, scale in ((axes[0], "reward_mean", 100), (axes[1], "mean_len", 1), (axes[2], "truncation_rate", 100)):
            ax.plot(st, [scale * r[key] for r in rows], color=COLS[arm], label=LABS[arm])
    for ax, t in zip(axes, ("verdict reward (%)", "judge response length (tokens)", "cut off at 8k (%)")):
        ax.set_title(t, fontsize=9, fontweight="bold")
        ax.set_xlabel("GRPO step")
    axes[2].legend(frameon=False, fontsize=7.5, loc="upper right")
    fig.savefig(path, dpi=160, bbox_inches="tight")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="phase3/runs/analysis/report.json")
    ap.add_argument("--paper", default="paper")
    ap.add_argument("--judges", default="", help="name=report.json,... for the judge comparison table")
    ap.add_argument("--model-curves", default="docs/research/verification-theory/model/model_curves.json")
    ap.add_argument("--train-metrics", default="", help="global=metrics.jsonl,perq=metrics.jsonl")
    a = ap.parse_args()
    rep = json.loads(Path(a.report).read_text())
    t = Path(a.paper) / "tables"
    t.mkdir(parents=True, exist_ok=True)
    (t / "stage0.tex").write_text(boxed(stage0(rep)))
    (t / "pools.tex").write_text(boxed(pools(rep)))
    (t / "configs.tex").write_text(boxed(configs(rep)))
    if "eval" in rep:
        (t / "selection.tex").write_text(boxed(selection(rep)))
        frontier(rep, Path(a.paper) / "figures" / "real_frontier.png")
    tf_path = Path(a.report).parent.parent / "trace_features.json"
    if tf_path.exists():
        (t / "trace.tex").write_text(boxed(trace_table(json.loads(tf_path.read_text()))))
    if a.judges:
        reps = {n: json.loads(Path(p).read_text()) for n, p in (x.split("=") for x in a.judges.split(","))}
        (t / "judges.tex").write_text(boxed(judges(reps)))
    if Path(a.model_curves).exists() and any("curves" in rep.get(s, {}) for s in ("dev", "test")):
        scaling(rep, json.loads(Path(a.model_curves).read_text()), Path(a.paper) / "figures" / "scaling_observed.png")
    if a.train_metrics:
        training_curves(dict(x.split("=") for x in a.train_metrics.split(",")), Path(a.paper) / "figures" / "training_curves.png")
    print("tables written to", t)


if __name__ == "__main__":
    main()
