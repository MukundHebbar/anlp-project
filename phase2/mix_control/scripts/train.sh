#!/bin/bash
# SOLVE-only control for the mixed run: the mixed run's command (artifacts/opd/evals/mixed-lr2e-5/submits.log) with
# its JUDGE / RECONSTRUCT prompts removed: the same 750 SOLVE prompts in the same steps (build.py), 10 per step,
# lr 2e-5 with 5 warm-up steps (then constant), async rollouts, 8 samples, 16k cap, Dr. GRPO, LoRA r64; 75 steps
# (the mixed run's evaluated checkpoint). Adapters kept at steps 40 and 75. 2 GPUs.
#   bash phase2/failure_driven/scripts/env.sh bash phase2/mix_control/scripts/train.sh <run> <seed> <port> [lr]
# lr: 2e-5 (the mixed run's) by default; lower values test whether the mixed run's gain is the SOLVE step size.
set -euo pipefail
R=/scratch/$USER/mix-control/runs
PYTHONFAULTHANDLER=1 python scripts/turing/opd_run.py --task solve --config grpo --steps 75 --keep-steps 40,75 \
  --prompts-file phase2/mix_control/data/prompts-solve75.jsonl --student-port $3 --out $R/$1 \
  --set prompts_per_step=10 --set optimizer.lr=${4:-2e-5} --set optimizer.warmup_steps=5 --set async_rollouts=true \
  --set best_window=8 --set best_keep=3 --set seed=$2
