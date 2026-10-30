#!/bin/bash
# Stage-2 self-judge arm (2 GPUs: vLLM rollouts + trainer). Phase-2 recipe: Dr. GRPO, 32 steps x 32 prompts x 8
# samples, lr 1e-5 with 5 warm-up steps, verdict-only reward, judge cap 8,192, from mixed-step75.
#   bash phase3/turing/train_selfjudge.sh <arm: global|perq> <prompts dir> <out> [student port]
# Two arms on one node need different ports (vLLM rollout server).
set -euo pipefail
arm=$1; prompts=$2; out=$3; port=${4:-8000}
export VLLM_USE_FLASHINFER_SAMPLER=0
python scripts/turing/opd_run.py --task selfjudge --config grpo --prompts-file "$prompts/$arm.jsonl" --out "$out" \
    --steps 32 --init-adapter final-adapters/mixed-step75 --keep-steps 8,16,24,32 --student-port "$port" \
    --set optimizer.lr=1e-5 --set optimizer.warmup_steps=5 --set prompts_per_step=32 --set samples_per_prompt=8 \
    --set norm_tokens=8192
