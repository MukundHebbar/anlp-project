#!/bin/bash
# Arm A (control): SOLVE-only Dr. GRPO, steps 9-24, from the shared round-1 step-8 adapter (optimizer restored),
# 32 SOLVE prompts per step: the pool's next 512 questions. Same recipe as round 1.
# Run inside a 2-GPU node07 job:  bash phase2/failure_driven/scripts/env.sh bash phase2/failure_driven/scripts/armA.sh
set -euo pipefail
R=/scratch/$USER/failure-driven/runs
D=phase2/failure_driven/data
PYTHONFAULTHANDLER=1 python scripts/turing/opd_run.py --task solve --config grpo --start-step 8 --steps 16 \
  --resume-from $R/r1/adapters/step8 --prompts-file $D/prompts-A.jsonl --out $R/armA \
  --set prompts_per_step=32 --set optimizer.lr=1e-5 --set optimizer.warmup_steps=5 --set async_rollouts=true \
  --set "extra_reward_rows=\"$PWD/$D/solve_rows.jsonl\""
