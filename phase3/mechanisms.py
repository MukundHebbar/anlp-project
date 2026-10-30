"""Mechanism checks on the cached judgments (CPU).

    python phase3/mechanisms.py --graded runs/graded --judge runs/main/judge --attempts runs/main/attempts

(a) Judge within-question AUROC and picking headroom by question solve rate (k/16): is verification weakest where the
    headroom is?
(b) Judge AUROC by attempt length (pairs of a wrong and a right attempt of the same question, binned by the pair's mean
    length): does judging degrade with length, as the length law predicts?
(c) Judge AUROC by self-correction count: lower on traces with many retractions (liveness)?
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import analyze as A
from trace_features import RETRACT


def pair_auroc(pairs):
    pairs = np.array(pairs)
    return (pairs[:, 0] > pairs[:, 1]).mean() + 0.5 * (pairs[:, 0] == pairs[:, 1]).mean() if len(pairs) else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graded", default="runs/graded")
    ap.add_argument("--judge", default="runs/main/judge")
    ap.add_argument("--attempts", default="runs/main/attempts")
    ap.add_argument("--sets", default="test,extra")
    ap.add_argument("--out", default="runs/mechanisms.json")
    a = ap.parse_args()
    qs = []
    for s in a.sets.split(","):
        part = A.load(Path(a.graded), Path(a.judge), s)
        texts = {}
        for f in sorted((Path(a.attempts) / s).glob("[0-9][0-9][0-9].jsonl")):
            for line in f.open():
                r = json.loads(line)
                texts[(r["uid"], r["k"])] = len(RETRACT.findall(r["text"]))
        for q in part:
            q["retr"] = np.array([texts[(q["uid"], k)] for k in range(q["n"])], float)
        qs += part
    out = {}
    # (a) by solve rate
    bins = [(0, 4), (4, 8), (8, 12), (12, 16)]
    rows = {}
    for lo, hi in bins:
        sel = [q for q in qs if lo <= q["correct"].sum() < hi and q["correct"].sum() > 0]
        res = {}
        for name, fn in (("chain", lambda q: q["p"][:, 0]), ("direct", lambda q: q["pdir"])):
            arr = A.within_pairs(sel, fn)
            res[name] = A.boot_ratio(arr, B=500) if len(arr) else (np.nan, (np.nan, np.nan))
        rows[f"{lo}-{hi - 1} right of 16"] = {"questions": len(sel), **res}
        print(f"(a) {lo:2d}-{hi - 1:2d} right/16: {len(sel):3d} q | chain {res['chain'][0]:.3f} | direct {res['direct'][0]:.3f}")
    out["by_solve_rate"] = rows
    # (b) by length and (c) by self-corrections: same-question wrong/right pairs
    for key, feat, edges in (("by_length", "tokens", [0, 4000, 8000, 12000, 1e9]),
                             ("by_retractions", "retr", [0, 10, 25, 50, 1e9])):
        acc = defaultdict(lambda: {"chain": [], "direct": []})
        for q in qs:
            m = q["answered"]
            w, r = np.where(m & ~q["correct"])[0], np.where(m & q["correct"])[0]
            for i in w:
                for j in r:
                    v = 0.5 * (q[feat][i] + q[feat][j])
                    b = int(np.searchsorted(edges, v, side="right") - 1)
                    for name, s in (("chain", q["p"][:, 0]), ("direct", q["pdir"])):
                        if not (np.isnan(s[i]) or np.isnan(s[j])):
                            acc[b][name].append((s[i], s[j]))
        rows = {}
        for b in sorted(acc):
            lab = f"{edges[b]:.0f}-{edges[b + 1]:.0f}" if edges[b + 1] < 1e9 else f">{edges[b]:.0f}"
            rows[lab] = {"pairs": len(acc[b]["chain"]), "chain": pair_auroc(acc[b]["chain"]),
                         "direct": pair_auroc(acc[b]["direct"])}
            print(f"({'b' if feat == 'tokens' else 'c'}) {key} {lab:>12s}: {rows[lab]['pairs']:5d} pairs | chain "
                  f"{rows[lab]['chain']:.3f} | direct {rows[lab]['direct']:.3f}")
        out[key] = rows
    Path(a.out).write_text(json.dumps(out, indent=1, default=float) + "\n")


if __name__ == "__main__":
    main()
