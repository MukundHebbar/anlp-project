#!/usr/bin/env python3
"""SOLVE checkpoint selection and dev early stopping for a GRPO run.

    python3 scripts/select_solve_step.py <dev dir> <base dev eval dir> [--patience 3] [--min-delta 0.5]

<dev dir>/step<k>/s*/scores.jsonl are the dev evals of the run's checkpoints (eval_matrix layout, 4 samples).
Prints per-step dev accuracy and the paired Δ against the untrained model (95% bootstrap CI), then writes
<dev dir>/selection.json:
- selected_step: best dev accuracy; ties go to the later step;
- early_stop: true when the last `patience` checks (in step order, no gaps) have not beaten the best earlier
  check by at least `min_delta` points.
"""

import argparse
import json
import random
import statistics as st
from pathlib import Path


def accuracy(d: Path) -> dict[str, float]:
    by: dict[str, list[bool]] = {}
    for s in sorted(d.glob("s*/scores.jsonl")):
        for line in s.open():
            x = json.loads(line)
            if x["task"] == "solve":
                by.setdefault(x["uid"], []).append(bool(x["correct_strict"]))
    return {u: st.mean(v) for u, v in by.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dev")
    ap.add_argument("base")
    ap.add_argument("--patience", type=int, default=3)
    ap.add_argument("--min-delta", type=float, default=0.5, help="points of dev accuracy")
    a = ap.parse_args()
    base = accuracy(Path(a.base))
    steps = sorted(int(p.name[4:]) for p in Path(a.dev).glob("step*") if any(p.glob("s*/scores.jsonl")))
    if not steps:
        raise SystemExit("no dev evaluations found")
    rows = {}
    print(f"untrained: {100 * st.mean(base.values()):.1f}% (n={len(base)})")
    for k in steps:
        acc = accuracy(Path(a.dev) / f"step{k}")
        diff = [acc[u] - base[u] for u in acc if u in base]
        rng = random.Random(0)
        boot = sorted(st.mean(rng.choices(diff, k=len(diff))) for _ in range(2000))
        rows[k] = {"dev_acc": 100 * st.mean(acc.values()), "delta": 100 * st.mean(diff),
                   "ci": [100 * boot[49], 100 * boot[1949]], "n": len(acc)}
        r = rows[k]
        print(f"step {k:3d}: {r['dev_acc']:.1f}%  Δ {r['delta']:+.1f} [{r['ci'][0]:+.1f}, {r['ci'][1]:+.1f}]  n={r['n']}")
    best = max(steps, key=lambda k: (round(rows[k]["dev_acc"], 6), k))
    # Early stop: the last `patience` checks all fail to beat the best check before them by min_delta.
    stop = False
    if len(steps) > a.patience:
        before = steps[:-a.patience]
        best_before = max(rows[k]["dev_acc"] for k in before)
        stop = all(rows[k]["dev_acc"] < best_before + a.min_delta for k in steps[-a.patience:])
    out = {"rule": "best dev accuracy, ties -> later step", "selected_step": best, "early_stop": stop,
           "patience": a.patience, "min_delta": a.min_delta, "base_dev_acc": 100 * st.mean(base.values()),
           "steps": rows}
    (Path(a.dev) / "selection.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"selected step {best}; early stop: {stop}")


if __name__ == "__main__":
    main()
