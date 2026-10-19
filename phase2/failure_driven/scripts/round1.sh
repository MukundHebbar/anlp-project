#!/bin/bash
# Round 1 (shared by arms A and B): SOLVE-only Dr. GRPO, steps 1-8, on the pool's first 256 questions.
# Aryama's recipe (scripts/solve_grpo_pipeline.sh): 32 prompts x 8 samples, lr 1e-5, 5 warm-up steps, async rollouts.
# Run inside a 2-GPU node07 job:  bash phase2/failure_driven/scripts/env.sh bash phase2/failure_driven/scripts/round1.sh
set -euo pipefail
OUT=/scratch/$USER/failure-driven/runs/r1
D=phase2/failure_driven/data
PYTHONFAULTHANDLER=1 python scripts/turing/opd_run.py --task solve --config grpo --start-step 0 --steps 8 \
  --prompts-file $D/prompts-r1.jsonl --out "$OUT" \
  --set prompts_per_step=32 --set optimizer.lr=1e-5 --set optimizer.warmup_steps=5 --set async_rollouts=true \
  --set "extra_reward_rows=\"$PWD/$D/solve_rows.jsonl\""
