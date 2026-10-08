#!/usr/bin/env python3
"""Paired dev-slice comparison of two eval folders under artifacts/opd/evals/ (same metrics as report_matrix.py).

    python3 scripts/compare_dev.py matrix-dev-jr-base matrix-dev-reconstruct-sft4k [--judge deepseek]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_matrix import JUDGED, boot, fmt, per_question  # noqa: E402

EVALS = Path(__file__).resolve().parents[1] / "artifacts" / "opd" / "evals"


def load(key, name):
    p = EVALS / key / name
    return {x["uid"]: x for x in map(json.loads, p.open())} if p.exists() else {}


def main():
    a, b = [x for x in sys.argv[1:] if not x.startswith("--") and x not in ("jev", "deepseek")][:2]
    ma, mb = (per_question(load(k, "scores.jsonl"), load(k, JUDGED)) for k in (a, b))
    for k, pct in (("solve_acc", True), ("judge_verdict", True), ("judge_step", True), ("judge_score", False),
                   ("recon_score", False), ("recon_same", True)):
        both = sorted(set(ma[k]) & set(mb[k]))
        if not both:
            continue
        print(f"{k:14s} n={len(both):3d}  {a}: {fmt(boot([ma[k][u] for u in both]), pct)}  "
              f"{b}: {fmt(boot([mb[k][u] for u in both]), pct)}  Δ {fmt(boot([mb[k][u] - ma[k][u] for u in both]), pct, True)}")


if __name__ == "__main__":
    main()
