#!/usr/bin/env python3
"""SOLVE dev comparison of eval_matrix outputs (s0..s3/scores.jsonl, strict checker-v3 correctness), paired over the
200 dev questions: mean pass@1 over the samples and pass@k, each with a 95% paired bootstrap CI of the difference
from the first folder (the reference, e.g. the untrained 2B).

    python phase2/failure_driven/dev_compare.py REF_DIR DIR [DIR ...]
"""
import json
import random
import sys
from pathlib import Path


def load(d: Path) -> dict[str, list[bool]]:
    out: dict[str, list[bool]] = {}
    for s in sorted(d.glob("s[0-9]*")):
        for line in open(s / "scores.jsonl"):
            x = json.loads(line)
            if x["task"] == "solve":
                out.setdefault(x["uid"], []).append(bool(x["correct_strict"]))
    return out


def stats(v: dict[str, list[bool]], uids: list[str]) -> tuple[list[float], list[float]]:
    return [sum(v[u]) / len(v[u]) for u in uids], [float(any(v[u])) for u in uids]


def ci(a: list[float], b: list[float], n: int = 10000) -> tuple[float, float, float]:
    rng, d = random.Random(0), [y - x for x, y in zip(a, b)]
    boots = sorted(sum(d[rng.randrange(len(d))] for _ in d) / len(d) for _ in range(n))
    return sum(d) / len(d), boots[int(0.025 * n)], boots[int(0.975 * n)]


def main() -> None:
    dirs = [Path(p) for p in sys.argv[1:]]
    runs = [load(d) for d in dirs]
    uids = sorted(set.intersection(*(set(r) for r in runs)))
    k = min(len(r[u]) for r in runs for u in uids)
    runs = [{u: r[u][:k] for u in uids} for r in runs]
    ref1, refk = stats(runs[0], uids)
    print(f"{len(uids)} questions, {k} samples each; differences are vs {dirs[0]}")
    for d, r in zip(dirs, runs):
        p1, pk = stats(r, uids)
        line = f"{str(d):60s} mean pass@1 {100 * sum(p1) / len(p1):5.1f}  pass@{k} {100 * sum(pk) / len(pk):5.1f}"
        if r is not runs[0]:
            m1, l1, h1 = ci(ref1, p1)
            mk, lk, hk = ci(refk, pk)
            line += f"  | d pass@1 {100 * m1:+.1f} [{100 * l1:+.1f}, {100 * h1:+.1f}]  d pass@{k} {100 * mk:+.1f} [{100 * lk:+.1f}, {100 * hk:+.1f}]"
        print(line)


if __name__ == "__main__":
    main()
