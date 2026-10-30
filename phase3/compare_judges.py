"""Stage 2: untrained vs trained self-judges on the same cached attempts, all from the first chain (CPU).

    python phase3/compare_judges.py --graded runs/graded --judges untrained=runs/main/judge,global=runs/main/judge-global,perq=runs/main/judge-perq

Per judge, on test ∪ extra:
- criterion: share of "incorrect" verdicts, hit and false-alarm rates, d′ (one sampled verdict per attempt);
- AUROC of one sampled verdict, of the chain probability and of the direct probability;
- pooled, within-question and contested within-question AUROC (chain, direct), with bootstrap CIs;
- CAV accuracy for (16, 8) and (8, 4) with β tuned on that judge's dev judgments, against majority at the same cost.
Writes runs/compare_judges.json and paper/tables/judges.tex.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import stats

import analyze as A


def measure(graded: Path, jdir: Path) -> dict:
    data = {s: A.load(graded, jdir, s) for s in ("dev", "test", "extra")}
    ev = data["test"] + data["extra"]
    rng = np.random.default_rng(3)
    lab, pc, pd = [], [], []
    for q in ev:
        m = q["answered"] & ~np.isnan(q["p"][:, 0])
        lab += (~q["correct"][m]).tolist()
        pc += q["p"][m, 0].tolist()
        pd += q["pdir"][m].tolist()
    lab, pc, pd = np.array(lab), np.array(pc), np.array(pd)
    s1 = rng.random(len(pc)) < pc
    h, f = s1[lab].mean(), s1[~lab].mean()
    out = {"attempts": int(len(lab)), "incorrect_share": float(s1.mean()), "hit": float(h), "false_alarm": float(f),
           "dprime": float(stats.norm.ppf(h) - stats.norm.ppf(f)),
           "auroc_sampled1": float(A.auroc(s1.astype(float), lab)), "auroc_chain": float(A.auroc(pc, lab)),
           "auroc_direct": float(A.auroc(pd, lab))}
    for name, fn in (("chain", lambda q: q["p"][:, 0]), ("direct", lambda q: q["pdir"])):
        out[f"within_{name}"] = A.boot_ratio(A.within_pairs(ev, fn))
        out[f"contested_{name}"] = A.boot_ratio(A.within_pairs(ev, fn, contested_only=True))
    betas = [float(b) for b in np.arange(-4.0, 3.01, 0.5)]
    cfgs = [(n1, m, b, src) for (n1, m) in ((16, 8), (8, 4)) for b in betas for src in ("chain", "direct")]
    dacc, _ = A.evaluate(data["dev"], 0.0, cfgs, [], [16], seed=2)
    acc, cost = A.evaluate(ev, 0.0, [(n1, m, max(betas, key=lambda b: dacc[f"cav-{src}@{n1},{m},{b}"].mean()), src)
                                     for (n1, m) in ((16, 8), (8, 4)) for src in ("chain", "direct")],
                           [], [1, 2, 4, 6, 8, 10, 12, 14, 16], seed=11)
    for k in [k for k in acc if k.startswith("cav")]:
        maj = A.matched_majority(acc, cost, cost[k].mean())
        src, rest = k[4:].split("@")
        n1m = ",".join(rest.split(",")[:2])
        out[f"cav_{src}_{n1m}"] = {"acc": float(acc[k].mean()), "cost": float(cost[k].mean()),
                                    "majority": float(maj.mean()), "diff": A.boot_mean(acc[k] - maj)}
    return out


def table(res: dict) -> str:
    f3 = lambda x: f"{x[0]:.3f}"
    fd = lambda d: f"{100*d['diff'][0]:+.1f} [{100*d['diff'][1][0]:+.1f}, {100*d['diff'][1][1]:+.1f}]"
    rows = []
    for name, r in res.items():
        rows.append(f"{name} & {r['incorrect_share']:.2f} & {r['dprime']:.2f} & {r['auroc_sampled1']:.3f} & "
                    f"{r['auroc_chain']:.3f} / {r['auroc_direct']:.3f} & {f3(r['within_chain'])} / {f3(r['within_direct'])} & "
                    f"{f3(r['contested_chain'])} / {f3(r['contested_direct'])} & {fd(r['cav_chain_16,8'])} & "
                    f"{fd(r['cav_direct_8,4'])} \\\\")
    return ("\\begin{table*}[t]\n\\centering\\small\n\\resizebox{\\linewidth}{!}{\\begin{tabular}{@{}lcccccccc@{}}\n"
            "\\toprule\nJudge & ``Incorrect'' & $d'$ & AUROC (1 sampled) & Pooled (chain / direct) & "
            "Within (chain / direct) & Contested (chain / direct) & CAV chain $16,8$ & CAV direct $8,4$ \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}}\n\\caption{Untrained and trained self-judges on the "
            "same test $\\cup$ extra attempts (first chain). CAV columns: gain in points over majority vote at the same "
            "cost, $\\beta$ tuned on each judge's dev judgments, 95\\% CI.}\n\\label{tab:judges}\n\\end{table*}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graded", default="runs/graded")
    ap.add_argument("--judges", required=True)
    ap.add_argument("--out", default="runs/compare_judges.json")
    ap.add_argument("--table", default="../paper/tables/judges.tex")
    a = ap.parse_args()
    res = {}
    for spec in a.judges.split(","):
        name, d = spec.split("=")
        res[name] = measure(Path(a.graded), Path(d))
        r = res[name]
        print(f"{name}: incorrect {r['incorrect_share']:.3f} d' {r['dprime']:.2f} | AUROC sampled {r['auroc_sampled1']:.3f} "
              f"chain {r['auroc_chain']:.3f} direct {r['auroc_direct']:.3f} | within {r['within_chain'][0]:.3f}/"
              f"{r['within_direct'][0]:.3f} contested {r['contested_chain'][0]:.3f}/{r['contested_direct'][0]:.3f} | "
              f"CAV chain16,8 {100*r['cav_chain_16,8']['diff'][0]:+.2f} direct8,4 {100*r['cav_direct_8,4']['diff'][0]:+.2f}",
              flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=float) + "\n")
    Path(a.table).write_text(table(res))


if __name__ == "__main__":
    main()
