#!/usr/bin/env python3
"""Compute spent per arm of the failure-driven pilot, for the matched-compute comparison.

- GPU-hours: Slurm-charged hours of the training jobs that produced each arm (launch.py ledger), cumulative from the
  shared round 1. Arm B's jobs hold 4 GPUs (trainer + student vLLM + the 27B reward judge on two). Failed attempts
  (setup errors, no training step completed) are listed separately, not charged to an arm.
- Student rollout tokens: generated tokens in the training rollouts, split SOLVE / auxiliary.
- Conversion: DeepSeek V4.1 Flash calls and tokens (diagnosis + RECONSTRUCT pipeline), arm B only.

    python phase2/failure_driven/compute.py
"""
import collections
import json
from pathlib import Path

W = Path(__file__).resolve().parents[2] / "local" / "failure-driven"
LEDGER = W / "turing_budget.json"
TRAIN_JOBS = {"shared round 1 (steps 1-8)": ["fd-r1"], "arm A (steps 9-24)": ["fd-armA"],
              "arm B round 2 (steps 9-16)": ["fd-armB-r2e"], "arm B round 3 (steps 17-24)": ["fd-armB-r3"],
              "arm D (steps 9-24)": ["fd-armD-r2", "fd-armD-r3"]}
ROLLOUTS = {"shared round 1": ("r1", range(1, 9)), "arm A": ("armA", range(9, 25)), "arm B": ("armB", range(9, 25)),
            "arm D": ("armD", range(9, 25))}
CONVERSIONS = ["buffer-r1-1-8", "buffer-armB-9-16"]


def main() -> None:
    jobs = {j["name"]: j for j in json.loads(LEDGER.read_text())["jobs"] if j["name"].startswith("fd-")}
    print("GPU-hours (Slurm-charged)")
    gh = {}
    for label, names in TRAIN_JOBS.items():
        h = [jobs[n].get("charged_gpu_hours") for n in names if n in jobs]
        gh[label] = sum(x for x in h if x) if all(h) else None
        print(f"  {label:32s} {gh[label] if gh[label] is not None else 'not finished'}")
    failed = [(n, j["charged_gpu_hours"]) for n, j in jobs.items() if j["status"] == "failed"]
    print(f"  failed setup attempts (not charged to an arm): {failed}")
    r1 = gh["shared round 1 (steps 1-8)"]
    b2 = gh["arm B round 2 (steps 9-16)"]
    print(f"  cumulative: arm A step 24 = {r1 + gh['arm A (steps 9-24)']:.2f}; arm B step 16 = {r1 + b2:.2f}"
          + (f"; arm B step 24 = {r1 + b2 + gh['arm B round 3 (steps 17-24)']:.2f}"
             if gh["arm B round 3 (steps 17-24)"] else "")
          + (f"; arm D step 24 = {r1 + gh['arm D (steps 9-24)']:.2f}" if gh["arm D (steps 9-24)"] else ""))
    print("Student rollout tokens (generated)")
    for label, (run, steps) in ROLLOUTS.items():
        tok, n = collections.Counter(), collections.Counter()
        for s in steps:
            p = W / run / "rollouts" / f"step{s}.jsonl"
            if not p.exists():
                continue
            for line in open(p):
                x = json.loads(line)
                t = x.get("task") or ("solve" if x["uid"].startswith("solvej-") else "aux")
                t = "solve" if t == "solve" else "aux"
                tok[t] += x["tokens"]
                n[t] += 1
        print(f"  {label:16s} " + ", ".join(f"{t}: {tok[t] / 1e6:.2f}M tokens in {n[t]} rollouts" for t in sorted(tok)))
    print("Conversion (DeepSeek V4.1 Flash, arm B)")
    calls = tok_in = tok_out = 0
    for d in CONVERSIONS:
        for line in open(W / d / "calls.jsonl"):
            c = json.loads(line)
            calls += 1
            u = c.get("usage") or {}
            tok_in += u.get("prompt_tokens", 0)
            tok_out += u.get("completion_tokens", 0)
    print(f"  {calls} calls, {tok_in / 1e6:.2f}M prompt + {tok_out / 1e6:.2f}M completion tokens")


if __name__ == "__main__":
    main()
