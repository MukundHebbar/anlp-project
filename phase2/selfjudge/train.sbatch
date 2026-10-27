#!/bin/bash
# Self-judge GRPO: the mixed adapter trained to give the right verdict on the mixed model's own attempts
# (verdict-only reward, no external judge). 2 GPUs: vLLM rollouts + trainer.
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --output=phase2/runs/slurm-%x-%j.out
set -euo pipefail
source phase2/next/env.sh
# Build the dataset (deterministic; the generation job's build step did not run after node14 GPU 3 failed).
python phase2/selfjudge/build.py build --out phase2/runs/selfjudge --steps 32 --per-step 32
export HF_HOME=$ENVROOT/hf_cache   # the trainer finds Qwen3.5-2B through snapshot_download(local_files_only)
D=$PWD/phase2/runs/selfjudge
OUT=/scratch/$USER/phase2/selfjudge-run
PYTHONFAULTHANDLER=1 python scripts/turing/opd_run.py --task judge --config grpo --steps 32 \
  --init-adapter $HOME/anlp-final-adapters/mixed-step75 --prompts-file $D/prompts.jsonl --out $OUT \
  --set prompts_per_step=32 --set optimizer.lr=1e-5 --set optimizer.warmup_steps=5 --set async_rollouts=true \
  --set "extra_reward_rows=\"$D/reward_rows.jsonl\"" --set 'reward_judge="none"' --set rollout_max_tokens.judge=8192 --set prompt_max_tokens=17408 \
  > $D/train.log 2>&1
mkdir -p $D/adapters && for s in 16 32; do [ -d $OUT/adapters/step$s ] && cp -r $OUT/adapters/step$s $D/adapters/; done
echo "end $(date -u +%FT%TZ)"
