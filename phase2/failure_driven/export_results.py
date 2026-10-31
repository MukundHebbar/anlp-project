#!/usr/bin/env python3
"""Write the curated results of the failure-driven pilot to phase2/results/failure-driven/ from the local run
outputs (local/failure-driven/, git-ignored). Generated texts (rollouts, attempts, raw DeepSeek outputs) are left
out, as for the other Phase-2 results folders.

    python phase2/failure_driven/export_results.py
"""
import gzip
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
W = REPO / "local" / "failure-driven"
OUT = REPO / "phase2" / "results" / "failure-driven"
BASE = REPO / "artifacts" / "opd" / "evals" / "v3-pass4-2b-dev"
sys.path.insert(0, str(HERE))
import dev_compare as dc  # noqa: E402

DEV = {"untrained": BASE, "step8": W / "evals/dev-r1-step8",
       **{f"{arm}{s}": W / f"evals/dev-arm{arm}-step{s}" for arm in "ABD" for s in (16, 24)}}
PAIRS = [("A16", "B16"), ("A16", "D16"), ("B16", "D16"), ("A24", "B24"), ("A24", "D24"), ("B24", "D24"),
         ("A24", "B16"), ("untrained", "A24"), ("untrained", "B24"), ("untrained", "D24")]
RECHECKS = [f"recheck-r1-arm{arm}-step{s}" for arm in "ABD" for s in (16, 24)]
BUFFERS = {"r1 steps 1-8 (shared)": "buffer-r1-1-8", "arm B steps 9-16": "buffer-armB-9-16",
           "arm D steps 9-16": "buffer-armD-9-16"}
RUNS = {"r1": "shared round 1, steps 1-8", "armA": "arm A, steps 9-24", "armB": "arm B, steps 9-24",
        "armD": "arm D, steps 9-24"}


def gz(name: str, rows) -> int:
    n = 0
    with gzip.open(OUT / name, "wt", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def score_rows(name: str, d: Path):
    for s in sorted(d.glob("s[0-9]*")):
        for line in open(s / "scores.jsonl"):
            x = json.loads(line)
            if x["task"] == "solve":
                yield {"eval": name, "sample": int(s.name[1:]), **{k: x[k] for k in (
                    "uid", "correct_strict", "answer_status", "finish_reason", "completion_tokens", "extracted_answer")}}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    runs = {k: dc.load(v) for k, v in DEV.items()}
    uids = sorted(set.intersection(*(set(r) for r in runs.values())))
    dev = {}
    for k, r in runs.items():
        p1, p4 = dc.stats(r, uids)
        dev[k] = {"mean_pass@1": round(100 * sum(p1) / len(p1), 1), "pass@4": round(100 * sum(p4) / len(p4), 1)}
    pairs = {}
    for a, b in PAIRS:
        a1, a4 = dc.stats(runs[a], uids)
        b1, b4 = dc.stats(runs[b], uids)
        pairs[f"{b} - {a}"] = {m: [round(100 * x, 1) for x in dc.ci(x_a, x_b)]
                               for m, x_a, x_b in (("mean_pass@1", a1, b1), ("pass@4", a4, b4))}
    recovery = {}
    for name in RECHECKS:
        r = json.loads((W / f"{name}.json").read_text())
        recovery[name.replace("recheck-r1-", "")] = {k: r[k] for k in ("questions", "still_failing", "recovered")}
    buffers = {}
    for label, d in BUFFERS.items():
        b = json.loads((W / d / "buffer.json").read_text())
        buffers[label] = {"rule": b["rule"], **b["summary"]}
        conv = W / d / "summary.json"
        if conv.exists():
            buffers[label]["conversion"] = json.loads(conv.read_text())
    compute = subprocess.run([sys.executable, str(HERE / "compute.py")], capture_output=True, text=True,
                             check=True).stdout
    summary = {"dev": {"questions": len(uids), "samples": 4, "split": "SOLVE dev (opd slice), 16k + 32k continuation",
                       "results": dev, "paired_differences_95ci": pairs},
               "recovery_of_round1_buffer": recovery, "buffers": buffers, "compute": compute.splitlines()}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    n_dev = gz("dev-scores.jsonl.gz", (r for k, d in DEV.items() if k != "untrained" for r in score_rows(k, d)))
    n_re = gz("recheck-scores.jsonl.gz", (r for name in RECHECKS for r in score_rows(name, W / "evals" / name)))
    n_buf = gz("buffers.jsonl.gz", ({"buffer": label, **{k: v for k, v in q.items() if k != "attempt"}}
                                    for label, d in BUFFERS.items()
                                    for q in json.loads((W / d / "buffer.json").read_text())["questions"]))
    n_conv = gz("conversion.jsonl.gz", (
        {"buffer": label, "uid": x["uid"], "judge_uid": x["judge_uid"], "diagnosis": x["diagnosis"],
         "reconstruct": {k: x["reconstruct"].get(k) for k in ("mode", "accepted", "accepted_by", "reason", "clues")}}
        for label, d in BUFFERS.items() if (W / d / "items.jsonl").exists()
        for x in map(json.loads, open(W / d / "items.jsonl"))))
    n_met = gz("train-metrics.jsonl.gz", ({"run": run, **json.loads(line)} for run in RUNS
                                          for line in open(W / run / "metrics.jsonl")))

    def row(label, k):
        d = dev[k]
        return f"| {label} | {d['mean_pass@1']} | {d['pass@4']} |"

    def pair(k):
        p = pairs[k]["mean_pass@1"]
        return f"{p[0]:+.1f} [{p[1]:+.1f}, {p[2]:+.1f}]"

    rec = lambda k: f"{recovery[k]['recovered']}/{recovery[k]['questions']}"
    report = f"""# Failure-driven cross-task GRPO pilot

Qwen3.5-2B, Dr. GRPO (Aryama's recipe: 32 prompts x 8 samples, lr 1e-5, 16k rollouts). SOLVE pool: 768
JUDGE-train questions (their JUDGE items reused as-is). Shared round 1 = steps 1-8 SOLVE-only; then three arms
for steps 9-24, with 32 prompts per step:

- **A**: 32 SOLVE.
- **B**: 24 SOLVE + 8 auxiliary: each buffered failure's JUDGE item and a RECONSTRUCT item (FINAL-v3 pipeline,
  clues targeted at the diagnosed mistake). Reward judge for these: Qwen3.8-27B.
- **D**: 24 SOLVE + 8 replayed failures as plain SOLVE (same buffer, schedule and refresh as B).

Buffer: <= 1/8 strictly correct and >= 5 verified-wrong, finished, ungated answers. Refreshed after step 16:
recheck (8 samples) with the arm's own step-16 adapter, plus the arm's new failures.

## SOLVE dev ({len(uids)} questions x 4 samples)

| Model | Mean pass@1 | pass@4 |
|---|---|---|
{row("Untrained 2B", "untrained")}
{row("Shared step 8", "step8")}
{row("A step 16", "A16")}
{row("B step 16", "B16")}
{row("D step 16", "D16")}
{row("A step 24", "A24")}
{row("B step 24", "B24")}
{row("D step 24", "D24")}

Paired differences in mean pass@1, 95% bootstrap CI over questions:

| | Step 16 | Step 24 |
|---|---|---|
| B - A | {pair("B16 - A16")} | {pair("B24 - A24")} |
| D - A | {pair("D16 - A16")} | {pair("D24 - A24")} |
| D - B | {pair("D16 - B16")} | {pair("D24 - B24")} |

Matched GPU-hours (B step 16 vs A step 24, about 7.6 GPU-h each): {pair("B16 - A24")}.

## Recovery of the 28 round-1 failures (secondary)

| Arm | Step 16 | Step 24 |
|---|---|---|
| A | {rec("armA-step16")} | {rec("armA-step24")} |
| B | {rec("armB-step16")} | {rec("armB-step24")} |
| D | {rec("armD-step16")} | {rec("armD-step24")} |

## Compute

```
{compute.rstrip()}
```

## Reading

Practising current failures (B or D) speeds up SOLVE gains early (step 16), but by step 24 no arm differs from
another beyond noise. Converting failures to JUDGE/RECONSTRUCT (B) gives no measurable benefit over replaying them as
SOLVE (D), and costs about 1.6x the GPU time (the 27B judge) plus DeepSeek conversion. One seed; 200 dev questions.

Records: `dev-scores.jsonl.gz` ({n_dev}), `recheck-scores.jsonl.gz` ({n_re}), `buffers.jsonl.gz` ({n_buf}),
`conversion.jsonl.gz` ({n_conv}), `train-metrics.jsonl.gz` ({n_met}). Code: `../../failure_driven/`.
"""
    (OUT / "report.md").write_text(report)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
