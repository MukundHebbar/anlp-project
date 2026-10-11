#!/usr/bin/env python3
"""Tutor: choose RECONSTRUCT's flag threshold on one half of the solutions and measure on the other half.

The tutor flags a solution as answering the wrong question when the 27B's probability that RECONSTRUCT's rebuilt
question contradicts the given problem exceeds a threshold. In the first report that threshold was read off the
test labels; here it is fixed on a tuning half (the score at which `--false-alarm` of the tuning half's correct and
false-step solutions are flagged) and evaluated on the other half. A correct solution and the wrong-question item
made from it share the same worked solution, so both stay in the same half. Repeated over `--splits` random 50/50
splits, both directions each; mean and spread are reported. CPU only, reads the curated results.

    python scripts/phase2/tutor_calibrate.py [--false-alarm 0.10] [--splits 50]
"""

from __future__ import annotations

import argparse
import gzip
import json
import random
import statistics as st
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RES = REPO / "artifacts" / "phase2" / "functional"
TEAMS = ("spec", "mixed")


def load():
    items = [json.loads(l) for l in gzip.open(RES / "tutor-agents.jsonl.gz", "rt")]
    contra = {}
    for l in gzip.open(RES / "tutor-compare.jsonl.gz", "rt"):
        c = json.loads(l)
        if c["against"] == "given":
            contra[(c["uid"], c["roleset"])] = 1.0 - c["p_same"]
    return items, contra


def evaluate(test, team, thr, contra) -> dict:
    """Rates on one half. JUDGE flags 'incorrect'; RECONSTRUCT flags score > thr (no rebuilt question = no flag)."""
    out = {}
    for lab in ("correct", "step", "misread"):
        s = [x for x in test if x["label"] == lab]
        judge = [x[f"{team}_judge"]["verdict"] == "incorrect" for x in s]
        recon = [contra.get((x["uid"], team), 0.0) > thr for x in s]
        out[lab] = {"n": len(s), "judge": sum(judge) / len(s), "recon": sum(recon) / len(s),
                    "judge_or_recon": sum(j or r for j, r in zip(judge, recon)) / len(s),
                    "recon_only": sum(r and not j for j, r in zip(judge, recon)) / len(s)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--false-alarm", type=float, default=0.10,
                    help="share of the tuning half's correct and false-step solutions RECONSTRUCT may flag")
    ap.add_argument("--splits", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20261011)
    a = ap.parse_args()
    items, contra = load()
    groups = sorted({x["source_uid"] for x in items})
    rng = random.Random(a.seed)
    runs = {t: [] for t in TEAMS}
    for _ in range(a.splits):
        rng.shuffle(groups)
        half = set(groups[: len(groups) // 2])
        parts = [[x for x in items if x["source_uid"] in half], [x for x in items if x["source_uid"] not in half]]
        for tune, test in (parts, parts[::-1]):
            for t in TEAMS:
                neg = sorted((contra.get((x["uid"], t), 0.0) for x in tune if x["label"] != "misread"), reverse=True)
                thr = neg[int(a.false_alarm * len(neg))]
                runs[t].append({"threshold": thr, **evaluate(test, t, thr, contra)})

    def agg(rs, lab, key):
        v = [r[lab][key] for r in rs]
        return {"mean": round(st.mean(v), 3), "sd": round(st.stdev(v), 3)}

    summary = {"false_alarm_target": a.false_alarm, "splits": a.splits, "evaluations_per_team": 2 * a.splits,
               "items": {lab: sum(x["label"] == lab for x in items) for lab in ("correct", "step", "misread")}}
    for t in TEAMS:
        rs = runs[t]
        summary[t] = {"threshold": {"mean": round(st.mean(r["threshold"] for r in rs), 3)},
                      **{lab: {k: agg(rs, lab, k) for k in ("judge", "recon", "judge_or_recon", "recon_only")}
                         for lab in ("correct", "step", "misread")}}
    out = RES / f"tutor-calibrated-fa{int(a.false_alarm * 100)}.json"
    out.write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
