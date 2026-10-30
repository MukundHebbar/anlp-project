"""Predicted CAV gain on the REAL answer structure, with a simulated judge of known strength (CPU).

    python phase3/semisynth.py --graded phase3/runs/graded --sets dev

Real data: the 16 attempts per question, their correctness and answer groups. Simulated: a judge score per attempt,
P(incorrect) = 1 - Phi(c0 + d Z + eta), eta ~ N(0, 1) shared with weight rho_s inside an answer group. For each d the
script reports the measured within-question AUROC of that simulated judge, the CAV accuracy (N1 = 16, m = 8, beta
tuned on the same pool) and majority at the same average unit cost. Run before any real judging, it turns the
theory into a numeric prediction: given the real judge's within-question AUROC, read off the predicted gain.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import stats

import analyze as A


def simulate_judge(qs, d, c0, rho_s, seed):
    rng = np.random.default_rng(seed)
    out = []
    for q in qs:
        n = q["n"]
        shared = {g: rng.standard_normal() for g in set(q["group"].tolist())}
        eta = np.array([np.sqrt(rho_s) * shared[g] + np.sqrt(1 - rho_s) * rng.standard_normal() for g in q["group"]])
        u = c0 + d * q["correct"] + eta
        p = np.full((n, 4), np.nan)
        p[:, 0] = np.where(q["answered"], 1 - stats.norm.cdf(u), np.nan)
        out.append({**q, "p": p, "pdir": p[:, 0].copy(), "jtok": np.zeros((n, 4))})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graded", default="phase3/runs/graded")
    ap.add_argument("--sets", default="dev")
    ap.add_argument("--out", default="phase3/runs/semisynth.json")
    a = ap.parse_args()
    empty = Path("/nonexistent-judge-dir")
    qs = [q for s in a.sets.split(",") for q in A.load(Path(a.graded), empty, s)]
    res = []
    print(f"{len(qs)} questions | d | rho_s | within AUROC | contested within | CAV acc | cost | majority@cost | gain")
    for rho_s in (0.3, 0.6):
        for d in (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0):
            sq = simulate_judge(qs, d, 1.0, rho_s, seed=int(100 * d) + int(10 * rho_s))
            w = A.boot_ratio(A.within_pairs(sq, lambda q: q["p"][:, 0]), B=200)[0]
            wc = A.boot_ratio(A.within_pairs(sq, lambda q: q["p"][:, 0], contested_only=True), B=200)[0]
            best = None
            for beta in np.arange(-4.0, 3.01, 1.0):
                acc, cost = A.evaluate(sq, 0.0, [(16, 8, float(beta), "chain")], [], [8, 10, 12, 14, 16], seed=3)
                k = f"cav-chain@16,8,{float(beta)}"
                if best is None or acc[k].mean() > best[0]:
                    maj = A.matched_majority(acc, cost, cost[k].mean())
                    best = (acc[k].mean(), cost[k].mean(), maj.mean(), beta)
            row = {"d": d, "rho_s": rho_s, "within_auroc": w, "contested_within_auroc": wc, "cav_acc": best[0],
                   "cost": best[1], "majority_at_cost": best[2], "gain": best[0] - best[2], "beta": best[3]}
            res.append(row)
            print(f"  {d:4.2f} | {rho_s} | {w:.3f} | {wc:.3f} | {100*best[0]:.1f} | {best[1]:.1f} | {100*best[2]:.1f} | "
                  f"{100*row['gain']:+.1f}", flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=float) + "\n")


if __name__ == "__main__":
    main()
