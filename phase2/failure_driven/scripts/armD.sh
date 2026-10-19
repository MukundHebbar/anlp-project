#!/bin/bash
# Arm D (same-form retry): SOLVE-only Dr. GRPO, 24 fresh SOLVE + 8 replayed failed SOLVE questions per step.
# Round 2 = steps 9-16 from the shared step-8 adapter; round 3 = steps 17-24 from arm D's step 16. 2 GPUs, no judge.
# Same recipe as arm A. Run inside a 2-GPU job:
#   bash phase2/failure_driven/scripts/env.sh bash phase2/failure_driven/scripts/armD.sh 2
set -euo pipefail
R=/scratch/$USER/failure-driven/runs
D=phase2/failure_driven/data
if [ "$1" = 2 ]; then START=8; FROM=$R/r1/adapters/step8; else START=16; FROM=$R/armD/adapters/step16; fi
PYTHONFAULTHANDLER=1 python scripts/turing/opd_run.py --task solve --config grpo --start-step $START --steps 8 \
  --resume-from $FROM --prompts-file $D/armD/prompts-D-r$1.jsonl --out $R/armD \
  --set prompts_per_step=32 --set optimizer.lr=1e-5 --set optimizer.warmup_steps=5 --set async_rollouts=true \
  --set "extra_reward_rows=\"$PWD/$D/solve_rows.jsonl\""
