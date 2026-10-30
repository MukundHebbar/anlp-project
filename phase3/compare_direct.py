"""Compare direct verdict probabilities from several adapters on the same attempts (CPU).

    python phase3/compare_direct.py --graded phase3/runs/graded --root phase3/runs/main --names base,solve,judge,mixed

For each name, reads <root>/direct-<name>/<set>/*.jsonl ("mixed" falls back to the judge run's p_direct). Reports
pooled, within-question and contested within-question AUROC on test, and CAV with the direct score (N1 = 16, m = 8;
beta tuned on dev) against majority vote at the same average cost.
"""

import argparse
import json
from pathlib import Path

import numpy as np

import analyze as A


def with_direct(qs, d: Path, s: str):
    vals = {}
    for f in sorted((d / s).glob("[0-9][0-9][0-9].jsonl")):
        for line in f.open():
            r = json.loads(line)
            vals[(r["uid"], r["k"])] = r["p_direct"]
    out = []
    for q in qs:
        pd = np.array([vals.get((q["uid"], k), np.nan) if q["answered"][k] else np.nan for k in range(q["n"])], float)
        p = np.full((q["n"], 4), np.nan)
        p[:, 0] = pd
        out.append({**q, "pdir": pd, "p": p, "jtok": np.zeros((q["n"], 4))})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graded", default="phase3/runs/graded")
    ap.add_argument("--root", default="phase3/runs/main")
    ap.add_argument("--names", default="base,solve,judge,mixed")
    ap.add_argument("--out", default="phase3/runs/compare_direct.json")
    a = ap.parse_args()
    root = Path(a.root)
    res = {}
    for name in a.names.split(","):
        d = root / f"direct-{name}"
        if name == "mixed" and not d.exists():
            src = {s: A.load(Path(a.graded), root / "judge", s) for s in ("dev", "test")}
        else:
            src = {s: with_direct(A.load(Path(a.graded), Path("/nonexistent"), s), d, s) for s in ("dev", "test")}
        test = [q for q in src["test"] if not np.isnan(q["pdir"]).all()]
        dev = [q for q in src["dev"] if not np.isnan(q["pdir"]).all()]
        if not test or not dev:
            print(f"{name}: no scores yet")
            continue
        lab = np.concatenate([~q["correct"][q["answered"]] for q in test])
        sc = np.concatenate([q["pdir"][q["answered"]] for q in test])
        w = A.boot_ratio(A.within_pairs(test, lambda q: q["pdir"]))
        wc = A.boot_ratio(A.within_pairs(test, lambda q: q["pdir"], contested_only=True))
        betas = [float(b) for b in np.arange(-4.0, 3.01, 0.5)]
        dacc, _ = A.evaluate(dev, 0.0, [(16, 8, b, "direct") for b in betas], [], [16], seed=2)
        beta = max(betas, key=lambda b: dacc[f"cav-direct@16,8,{b}"].mean())
        acc, cost = A.evaluate(test, 0.0, [(16, 8, beta, "direct")], [], [1, 2, 4, 6, 8, 10, 12, 14, 16], seed=4)
        k = f"cav-direct@16,8,{beta}"
        maj = A.matched_majority(acc, cost, cost[k].mean())
        res[name] = {"questions": len(test), "pooled_auroc": float(A.auroc(sc, lab)), "within_auroc": w,
                     "contested_within_auroc": wc, "beta": beta, "cav_acc": float(acc[k].mean()),
                     "cav_cost": float(cost[k].mean()), "majority_matched": float(maj.mean()),
                     "diff_vs_majority": A.boot_mean(acc[k] - maj), "majority16": float(acc["majority@16"].mean())}
        r = res[name]
        print(f"{name:7s} pooled {r['pooled_auroc']:.3f} within {w[0]:.3f} [{w[1][0]:.3f}, {w[1][1]:.3f}] contested "
              f"{wc[0]:.3f} | CAV {100*r['cav_acc']:.1f} at {r['cav_cost']:.1f} vs majority {100*r['majority_matched']:.1f}: "
              f"{100*r['diff_vs_majority'][0]:+.1f} [{100*r['diff_vs_majority'][1][0]:+.1f}, {100*r['diff_vs_majority'][1][1]:+.1f}]")
    Path(a.out).write_text(json.dumps(res, indent=1, default=float) + "\n")


if __name__ == "__main__":
    main()
