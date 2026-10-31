#!/usr/bin/env python3
"""Dr. GRPO transfer matrix: each trained arm on all three test sets, paired against the untrained 2B.

    python3 scripts/report_grpo_matrix.py          # writes artifacts/baselines/final-v3/v3-report/grpo-matrix.md

Eval folders (eval_matrix.py layout, s0 ... s<K-1>) under artifacts/baselines/final-v3/test/:
  v3-pass4-2b                  the untrained 2B (4 samples on every task)
  v3-drgrpo-<task>-step<k>     trained arms (SOLVE 4 samples, JUDGE and RECONSTRUCT 1)
Which step is "selected" comes from artifacts/opd/evals/v3-drgrpo-dev/selection.json; step 104 is the fixed
endpoint. JUDGE headline: step % (on a solution with an error, verdict "incorrect" AND the exact first wrong step;
always answering one verdict cannot score), false alarm % (a correct solution called incorrect; lower is better)
and Youden's J (verdict accuracy on incorrect keys + on correct keys - 100; 0 for a one-verdict model; on this
balanced 200/200 test set it equals 2 x verdict accuracy - 100).
Per question, a model's value is the mean over its samples (pass@1), so a 4-sample baseline and a
1-sample checkpoint estimate the same expected single-sample score. Deterministic metrics use the strict gates;
JUDGE V/L/E/M and RECONSTRUCT PC-v4 use the Qwen3.8-27B judge (judged-scores.qwen.jsonl). Δ is paired on the
same questions; 95% bootstrap intervals over questions (2,000 resamples).
"""

import gzip
import json
import os
import random
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "artifacts" / "baselines" / "final-v3" / "test"
SEL = ROOT / "artifacts" / "opd" / "evals" / "v3-drgrpo-dev" / "selection.json"
OUT = ROOT / "artifacts" / "baselines" / "final-v3" / "v3-report" / "grpo-matrix.md"
METRICS = [("solve_acc", "SOLVE acc %", True), ("solve_pass4", "SOLVE pass@4 %", True),
           ("judge_verdict", "JUDGE verdict %", True), ("judge_step", "JUDGE step %", True),
           ("judge_false_alarm", "JUDGE false alarm % (lower better)", True), ("judge_j", "JUDGE Youden J %", True),
           ("judge_score", "JUDGE V/L/E/M", False), ("recon_score", "RECON PC-v4", False),
           ("recon_same", "RECON same Q %", True)]
OWN = {"solve": ("solve_acc",), "judge": ("judge_step", "judge_false_alarm", "judge_j", "judge_score"),
       "reconstruct": ("recon_score", "recon_same")}


def load(p):
    if not p.exists():
        p = p.with_name(p.name + ".gz")
    if not p.exists():
        return []
    with (gzip.open(p, "rt") if p.suffix == ".gz" else p.open()) as stream:
        return [json.loads(line) for line in stream]


def per_question(d: Path) -> dict[str, dict[str, float]]:
    vals = {m: {} for m, _, _ in METRICS}
    vals["_label"], vals["judge_combined"] = {}, {}
    acc = {}
    for s in sorted(p for p in d.glob("s*") if p.is_dir()):
        judged = {x["uid"]: x for x in load(s / "judged-scores.qwen.jsonl")}
        for x in load(s / "scores.jsonl"):
            a = acc.setdefault(x["uid"], {"task": x["task"], "label": x.get("label"), "rows": []})
            a["rows"].append((x, judged.get(x["uid"])))
    for u, a in acc.items():
        rows = a["rows"]
        if a["task"] == "solve":
            vals["solve_acc"][u] = st.mean(float(x["correct_strict"]) for x, _ in rows)
            if len(rows) > 1:
                vals["solve_pass4"][u] = float(any(x["correct_strict"] for x, _ in rows))
        elif a["task"] == "judge":
            vals["_label"][u] = a["label"]
            vals["judge_verdict"][u] = st.mean(float(x["verdict_correct_strict"]) for x, _ in rows)
            # Combined: verdict and first wrong step both right ("none" for a correct solution), all questions.
            vals["judge_combined"][u] = st.mean(float(x["step_correct_strict"]) for x, _ in rows)
            if a["label"] == "correct":  # a correct solution called incorrect (or gated)
                vals["judge_false_alarm"][u] = 1 - vals["judge_verdict"][u]
            if a["label"] == "incorrect":
                vals["judge_step"][u] = st.mean(float(x["step_correct_strict"]) for x, _ in rows)
            js = [j["score_100"] for _, j in rows if j]
            if len(js) == len(rows):
                vals["judge_score"][u] = st.mean(js)
        else:
            js = [j for _, j in rows if j]
            if len(js) == len(rows):
                vals["recon_score"][u] = st.mean(j["score_100"] for j in js)
                vals["recon_same"][u] = st.mean(float(bool(j.get("semantic_equivalent"))) for j in js)
    # Youden's J = verdict accuracy on incorrect keys + on correct keys - 1 (0 for a model that always gives the
    # same verdict). Written per question so it bootstraps and pairs like the other metrics: with n_label
    # questions of that label out of N, question q contributes N * verdict_q / n_label(q) - 1.
    labels = vals["_label"]
    count = {lab: sum(1 for u in vals["judge_verdict"] if labels.get(u) == lab) for lab in ("correct", "incorrect")}
    n = sum(count.values())
    if all(count.values()):
        vals["judge_j"] = {u: n * x / count[labels[u]] - 1 for u, x in vals["judge_verdict"].items()}
    return vals


def boot(v, seed=0):
    rng = random.Random(seed)
    means = sorted(st.mean(rng.choices(v, k=len(v))) for _ in range(2000))
    return st.mean(v), means[49], means[1949]


def fmt(ci, pct, sign=False):
    if ci is None:
        return "—"
    s = 100 if pct else 1
    f = (lambda x: f"{x * s:+.1f}") if sign else (lambda x: f"{x * s:.1f}")
    return f"{f(ci[0])} [{f(ci[1])}, {f(ci[2])}]"


def main():
    sel = json.loads(SEL.read_text()) if SEL.exists() else {}
    base = per_question(TEST / "v3-pass4-2b")
    rows = [("Untrained 2B", base, None)]
    for task in ("solve", "judge", "reconstruct"):
        steps = []
        if task in sel:
            steps.append(("dev-selected", sel[task]["selected_step"]))
        steps.append(("fixed endpoint", 104))
        seen = set()
        for kind, k in steps:
            d = TEST / f"v3-drgrpo-{task}-step{k}"
            if k in seen or not d.exists():
                continue
            seen.add(k)
            rows.append((f"Dr. GRPO on {task.upper()}, step {k} ({kind})", per_question(d), task))
    # The 2026-10-07 SOLVE recipe (lr 1e-5, 32 x 8, overlapped rollouts, checker v3): scripts/solve_grpo_pipeline.sh.
    run2 = os.environ.get("SOLVE_RUN", "v3-grpo-lr1e-5-solve")
    sel2 = os.environ.get("SOLVE_SEL", "")
    for d in sorted(TEST.glob(f"{run2}-step*"), key=lambda p: int(p.name.rsplit("step", 1)[1])):
        k = d.name.rsplit("step", 1)[1]
        kind = "selected by training reward, dev-checked" if k == sel2 else "last step"
        rows.append((f"Dr. GRPO on SOLVE, lr 1e-5 recipe, step {k} ({kind})", per_question(d), "solve"))
    # Mixed-task run (equal thirds, lr 2e-5, 30 x 8): scripts/mixed_grpo_pipeline.sh. No own task: nothing in bold.
    sel3 = os.environ.get("MIXED_SEL", "")
    for d in sorted(TEST.glob("v3-grpo-mixed-lr2e-5-step*"), key=lambda p: int(p.name.rsplit("step", 1)[1])):
        k = d.name.rsplit("step", 1)[1]
        rows.append((f"Dr. GRPO on the 1/3-1/3-1/3 mixture, lr 2e-5, step {k}" + (" (best by training reward)" if k == sel3 else ""),
                     per_question(d), None))
    L = ["# Dr. GRPO transfer matrix (Qwen3.5-2B, FINAL-v3 test)", "", __doc__.split("\n\n")[2].strip(), "",
         "## Scores (pass@1 unless noted)", "",
         "| Model | " + " | ".join(n for _, n, _ in METRICS) + " |", "|---|" + "---:|" * len(METRICS)]
    for name, v, _ in rows:
        L.append(f"| {name} | " + " | ".join(fmt(boot(list(v[m].values())), pct) if v[m] else "—"
                                             for m, _, pct in METRICS) + " |")
    L += ["", "## Δ against the untrained 2B (paired; **bold** = own task)", "",
          "| Model | " + " | ".join(n for _, n, _ in METRICS) + " |", "|---|" + "---:|" * len(METRICS)]
    for name, v, task in rows[1:]:
        cells = []
        for m, _, pct in METRICS:
            both = sorted(set(v[m]) & set(base[m]))
            c = fmt(boot([v[m][u] - base[m][u] for u in both]), pct, sign=True) if both else "—"
            cells.append(f"**{c}**" if task and m in OWN[task] else c)
        L.append(f"| {name} | " + " | ".join(cells) + " |")
    L += ["", "## JUDGE by answer-key label (pass@1, 200 questions each)", "",
          "Combined accuracy favours a model that answers \"correct\": on a correct solution \"correct, none\" "
          "earns full credit, while on an incorrect one the first wrong step must also be found. Read it with "
          "this split.", "",
          "| Model | verdict, key correct % | verdict, key incorrect % | combined, key correct % | "
          "combined, key incorrect % |", "|---|---:|---:|---:|---:|"]
    for name, v, _ in rows:
        cells = []
        for m in ("judge_verdict", "judge_combined"):
            for lab in ("correct", "incorrect"):
                xs = [v[m][u] for u in v[m] if v["_label"].get(u) == lab]
                cells.append(f"{100 * st.mean(xs):.1f}" if xs else "—")
        L.append(f"| {name} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
