#!/usr/bin/env python3
"""pass@1 / pass@K report for evaluations with K samples per question (eval_matrix.py --samples K).

    python3 scripts/report_passk.py artifacts/baselines/final-v3/test/v3-base-2b [more eval dirs ...]

Each eval dir holds s0 ... s<K-1>, one answer per question each. Deterministic metrics use the strict-gated
scores in s<k>/scores.jsonl:
- SOLVE: correct (single agreeing final answer, verifier v2).
- JUDGE: verdict, and verdict + first wrong step on incorrect-label questions.
Judged metrics use s<k>/judged-scores.jev.jsonl (Jev) or judged-scores.qwen.jsonl (27B) when present:
- JUDGE V/L/E/M /100 and RECONSTRUCT PC-v4 /100: mean over samples, and the best of K per question.
- RECONSTRUCT same question: in any of K samples.
pass@1 is the mean over all K samples (the expected single-sample score); pass@K is the share of questions with
at least one success among the K. "16k budget" counts answers that needed the continuation past 16k as wrong.
95% bootstrap intervals over questions (2,000 resamples).
"""

import json
import random
import statistics as st
import sys
from pathlib import Path


def boot(vals, seed=0):
    if not vals:
        return None
    rng = random.Random(seed)
    means = sorted(st.mean(rng.choices(vals, k=len(vals))) for _ in range(2000))
    return st.mean(vals), means[49], means[1949]


def fmt(ci, pct=True):
    if ci is None:
        return "—"
    s = 100 if pct else 1
    return f"{ci[0] * s:.1f} [{ci[1] * s:.1f}, {ci[2] * s:.1f}]"


def load(path):
    return [json.loads(l) for l in path.open()] if path.exists() else []


def report(d: Path) -> list[str]:
    samples = sorted(p for p in d.glob("s*") if p.is_dir() and p.name[1:].isdigit())
    K = len(samples)
    meta = json.loads((d / "metadata.json").read_text())
    by = {}  # (task, uid) -> list of per-sample dicts
    for p in samples:
        resp = {x["uid"]: x for x in load(p / "responses.jsonl")}
        judged = {x["uid"]: x for x in load(p / "judged-scores.qwen.jsonl") or load(p / "judged-scores.jev.jsonl")}
        for sc in load(p / "scores.jsonl"):
            by.setdefault((sc["task"], sc["uid"]), []).append({**sc, "continued": resp[sc["uid"]].get("continued", False),
                                                              "judged": judged.get(sc["uid"])})
    judge_name = "27B" if (samples[0] / "judged-scores.qwen.jsonl").exists() else (
        "Jev" if (samples[0] / "judged-scores.jev.jsonl").exists() else None)
    L = [f"## {d.name}: {meta['model']}, {meta['split']}, {K} samples per question", "",
         "| Metric | pass@1 (mean of samples) | pass@%d | 16k budget pass@1 |" % K, "|---|---:|---:|---:|"]

    def row(name, task, ok, cond=lambda s: True, pct=True):
        qs = [v for (t, _), v in by.items() if t == task and cond(v[0])]
        if not qs:
            return
        k = max(len(v) for v in qs)  # samples per question for this task (e.g. 4 for SOLVE, 1 for the others)
        p1 = boot([st.mean(ok(s) for s in v) for v in qs])
        pk = boot([float(any(ok(s) for s in v)) for v in qs]) if k > 1 else None
        b16 = boot([st.mean(ok(s) and not s["continued"] for s in v) for v in qs])
        L.append(f"| {name} (n={len(qs)}, {k} sample{'s' if k > 1 else ''}) | {fmt(p1, pct)} | {fmt(pk, pct)} | {fmt(b16, pct)} |")

    row("SOLVE accuracy (%)", "solve", lambda s: s["correct_strict"])
    row("JUDGE verdict (%)", "judge", lambda s: s["verdict_correct_strict"])
    row("JUDGE first wrong step, incorrect solutions (%)", "judge", lambda s: s["step_correct_strict"],
        cond=lambda s: s["label"] == "incorrect")
    if judge_name:
        L.append("")
        L.append(f"Judged by {judge_name}; mean over samples and best of {K} per question:")
        L.append("")
        L.append("| Metric | mean | best of %d |" % K)
        L.append("|---|---:|---:|")
        for task, name in (("judge", "JUDGE V/L/E/M /100"), ("reconstruct", "RECONSTRUCT PC-v4 /100")):
            qs = [v for (t, _), v in by.items() if t == task and all(s["judged"] for s in v)]
            if qs:
                L.append(f"| {name} (n={len(qs)}) | {fmt(boot([st.mean(s['judged']['score_100'] for s in v) for v in qs]), False)} | "
                         f"{fmt(boot([max(s['judged']['score_100'] for s in v) for v in qs]), False)} |")
        qs = [v for (t, _), v in by.items() if t == "reconstruct" and all(s["judged"] for s in v)]
        if qs:
            L.append(f"| RECONSTRUCT same question (%) | {fmt(boot([st.mean(bool(s['judged'].get('semantic_equivalent')) for s in v) for v in qs]))} | "
                     f"{fmt(boot([float(any(s['judged'].get('semantic_equivalent') for s in v)) for v in qs]))} |")
    L += ["", "| Task | gate failures (% of answers) | mean tokens | continued past 16k (%) | still capped at 32k (%) |",
          "|---|---:|---:|---:|---:|"]
    for task in ("solve", "judge", "reconstruct"):
        xs = [s for (t, _), v in by.items() if t == task for s in v]
        if xs:
            L.append(f"| {task} | {100 * st.mean(bool(s['gate']) for s in xs):.1f} | "
                     f"{st.mean(s['completion_tokens'] or 0 for s in xs):.0f} | {100 * st.mean(s['continued'] for s in xs):.1f} | "
                     f"{100 * st.mean(s['hit_token_cap'] for s in xs):.1f} |")
    return L + [""]


def main():
    L = ["# pass@k report", "", __doc__.split("\n\n")[2].strip(), "",
         "Note: JUDGE verdict is a binary choice, so pass@K saturates even by chance (0.5 per sample gives "
         "pass@4 = 94%); read pass@1 for the verdict.", ""]
    for d in sys.argv[1:]:
        L += report(Path(d))
    print("\n".join(L))


if __name__ == "__main__":
    main()
