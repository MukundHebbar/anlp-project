#!/usr/bin/env python3
"""Decision rule for the mixed-run control, fixed on 2026-10-25 before any control result existed (README).

Arms (all step 75, evaluated with eval_matrix.py: 4 samples, T 1.0, 16k then 32k continuation):
  mixed    the Phase-1 mixed-task adapter (mixed75: 750 SOLVE + 750 JUDGE + 750 RECONSTRUCT prompts)
  ctrl-s0  SOLVE-only control: the same 750 SOLVE prompts, same steps and recipe, seed 0
  ctrl-s1  the same control, seed 1 (rollout sampling seeds)
Validation: SOLVE dev (200) + phase2/failure_driven/data/val_uids.json (200), minus the 750 SOLVE questions both
trained on (51 of val200) and minus the reworded test duplicates (failure_driven/data/eval_duplicates.json).
avg@4 and pass@4 per question; paired 95% bootstrap intervals over questions (10,000 resamples, seed 0).

Primary question: did the JUDGE / RECONSTRUCT data help SOLVE?
  YES if mixed - mean(ctrl-s0, ctrl-s1) > 0 with the interval above 0 on avg@4, AND mixed is above each control seed
  on avg@4 (a single seed can be off by about 3 points: failure_driven README, D2 repeated).
  NO (no evidence) otherwise; if the controls are at or above mixed, the mixed run's SOLVE accuracy is explained by
  its steps and learning rate.
Also reported: ctrl-s1 - ctrl-s0 (seed spread), pass@4, per split. The SOLVE test set is evaluated once, after.

    python phase2/mix_control/decide.py
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
E = REPO / "local" / "mix-control" / "evals"
EXCLUDE = (set(json.loads((REPO / "phase2/failure_driven/data/eval_duplicates.json").read_text()))
           | set(json.loads((HERE / "data" / "mixed_solve_uids.json").read_text())))
RUNS = {"mixed": "mixed75", "ctrl-s0": "ctrl-s0", "ctrl-s1": "ctrl-s1"}
SPLITS = {"dev": "dev-{run}-step75", "val200": "val200-{run}-step75"}


def per_question(run: str) -> dict[str, list[bool]]:
    out: dict[str, list[bool]] = {}
    for split, pattern in SPLITS.items():
        for s in sorted((E / pattern.format(run=run)).glob("s[0-9]*")):
            for line in open(s / "scores.jsonl"):
                x = json.loads(line)
                if x["task"] == "solve" and x["uid"] not in EXCLUDE:
                    out.setdefault(f"{split}:{x['uid']}", []).append(bool(x["correct_strict"]))
    return out


def interval(d: list[float], n: int = 10000) -> tuple[float, float, float]:
    rng = random.Random(0)
    boots = sorted(sum(d[rng.randrange(len(d))] for _ in d) / len(d) for _ in range(n))
    return sum(d) / len(d), boots[int(0.025 * n)], boots[int(0.975 * n)]


def main() -> None:
    arms = {a: per_question(r) for a, r in RUNS.items()}
    qs = sorted(set.intersection(*(set(v) for v in arms.values())))
    if any(len(arms[a][q]) != 4 for a in arms for q in qs):
        raise SystemExit("every question needs 4 samples in every arm")
    metric = {"avg@4": lambda v: sum(v) / 4, "pass@4": lambda v: float(any(v))}
    print(f"{len(qs)} validation questions ({sum(q.startswith('dev:') for q in qs)} dev), step 75")
    score = {a: {m: 100 * sum(f(arms[a][q]) for q in qs) / len(qs) for m, f in metric.items()} for a in arms}
    for a in arms:
        print(f"  {a:8s} " + "  ".join(f"{m} {v:.1f}" for m, v in score[a].items()))
    for m, f in metric.items():
        mean, lo, hi = interval([f(arms["mixed"][q]) - (f(arms["ctrl-s0"][q]) + f(arms["ctrl-s1"][q])) / 2 for q in qs])
        print(f"  mixed - mean(controls) {m}: {100 * mean:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]")
        if m == "avg@4":
            primary = lo > 0 and all(score["mixed"][m] > score[c][m] for c in ("ctrl-s0", "ctrl-s1"))
        for c in ("ctrl-s0", "ctrl-s1"):
            mean, lo, hi = interval([f(arms["mixed"][q]) - f(arms[c][q]) for q in qs])
            print(f"  mixed - {c} {m}: {100 * mean:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]")
        mean, lo, hi = interval([f(arms["ctrl-s1"][q]) - f(arms["ctrl-s0"][q]) for q in qs])
        print(f"  ctrl-s1 - ctrl-s0 {m}: {100 * mean:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]  (seed spread)")
    print(f"JUDGE / RECONSTRUCT data helped SOLVE: {'YES' if primary else 'no evidence'}")


if __name__ == "__main__":
    main()
