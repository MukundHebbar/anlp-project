#!/usr/bin/env python3
"""Arm B, one round of 8 steps, in one 4-GPU job: the Qwen3.8-27B reward judge on the last two GPUs, Dr. GRPO
(24 SOLVE + 8 auxiliary prompts per step) on the first two. Same recipe as round 1 and arm A.

    bash phase2/failure_driven/scripts/env.sh python phase2/failure_driven/run_armB.py --round 2

Round 2 = steps 9-16 from the shared round-1 step-8 adapter; round 3 = steps 17-24 from arm B's step 16.
The judge is served exactly as scripts/turing/qwen_judge_run.py serves it (tensor parallel over 2 L40S); the
trainer's QwenJudge client reads the JUDGE explanation and RECONSTRUCT scores from it (reward_judge "qwen").
"""

import argparse
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from anlp_project.opd_train import serve, wait_ready  # noqa: E402
from anlp_project.qwen_judging import MODEL  # noqa: E402

RUNS = Path(f"/scratch/{os.environ['USER']}/failure-driven/runs")
DATA = REPO / "phase2" / "failure_driven" / "data" / "armB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True, choices=[2, 3])
    a = ap.parse_args()
    start = 8 if a.round == 2 else 16
    resume = RUNS / "r1" / "adapters" / "step8" if a.round == 2 else RUNS / "armB" / "adapters" / "step16"
    prompts, rows = DATA / f"prompts-B-r{a.round}.jsonl", DATA / "reward_rows.jsonl"
    for p in (resume, prompts, rows):
        if not p.exists():
            raise SystemExit(f"missing {p}")
    gpus = os.environ.get("CUDA_VISIBLE_DEVICES", "0,1,2,3").split(",")
    if len(gpus) < 4:
        raise SystemExit(f"need 4 GPUs, have {gpus}")
    out = RUNS / "armB"
    out.mkdir(parents=True, exist_ok=True)
    with socket.socket() as sk:
        sk.bind(("127.0.0.1", 0))
        port = sk.getsockname()[1]
    from huggingface_hub import snapshot_download
    judge_gpus = ",".join(gpus[2:4])
    proc = serve(snapshot_download(MODEL, local_files_only=True), "judge", port, judge_gpus,
                 ["--tensor-parallel-size", "2", "--max-model-len", "40960",
                  "--gpu-memory-utilization", "0.90", "--max-logprobs", "20", "--enable-prefix-caching"], out, {})
    try:
        print(f"reward judge ready in {wait_ready(port, proc, 'judge', out)} s on GPUs {judge_gpus}, "
              f"port {port}", flush=True)
        cmd = [sys.executable, str(REPO / "scripts" / "turing" / "opd_run.py"), "--task", "mixed", "--config", "grpo",
               "--start-step", str(start), "--steps", "8", "--resume-from", str(resume), "--prompts-file", str(prompts),
               "--out", str(out), "--set", "prompts_per_step=32", "--set", "optimizer.lr=1e-5",
               "--set", "optimizer.warmup_steps=5", "--set", "async_rollouts=true",
               "--set", 'reward_judge="qwen"', "--set", f"reward_judge_port={port}",
               "--set", f"extra_reward_rows={json.dumps(str(rows))}"]
        subprocess.run(cmd, cwd=REPO, env={**os.environ, "CUDA_VISIBLE_DEVICES": ",".join(gpus[:2]),
                                           "PYTHONFAULTHANDLER": "1"}, check=True)
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
