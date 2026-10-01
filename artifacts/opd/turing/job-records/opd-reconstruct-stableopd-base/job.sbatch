#!/bin/bash
#SBATCH --job-name=opd-reconstruct-stableopd-base
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodelist=node07
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:3
#SBATCH --cpus-per-task=24
#SBATCH --mem=144G
#SBATCH --time=01:45:00
#SBATCH --output=/home/mukund.hebbar/anlp-project-v3/runs/opd-reconstruct-stableopd-base/slurm-%j.out

set -euo pipefail
ROOT=/scratch/$USER/anlp-opd
export HF_HOME=$ROOT/hf_cache HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export VLLM_CACHE_ROOT=$ROOT/vllm_cache TRITON_CACHE_DIR=$ROOT/triton_cache TORCHINDUCTOR_CACHE_DIR=$ROOT/inductor_cache
export XDG_CACHE_HOME=$ROOT/xdg_cache FLASHINFER_WORKSPACE_BASE=$ROOT/flashinfer
export PATH=$ROOT/venv/bin:$PATH
cd /home/mukund.hebbar/anlp-project-v3
mkdir -p /scratch/$USER/anlp-opd/runs/opd-reconstruct-stableopd-base
echo "job $SLURM_JOB_ID on $(hostname) gpus $CUDA_VISIBLE_DEVICES start $(date -u +%FT%TZ)"
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader
timeout --signal=TERM --kill-after=120 6000s python scripts/turing/opd_run.py --task reconstruct --steps 16 --prompts warmup --set optimizer.warmup_steps=3 --set kl_anchor_beta=0.5 --sft-mix /home/mukund.hebbar/anlp-opd-shared/teacher-warmup-470.jsonl --sft-paired --sft-keep /home/mukund.hebbar/anlp-opd-shared/golden-uids.json --sft-weight 1.0 --out /scratch/$USER/anlp-opd/runs/opd-reconstruct-stableopd-base
echo "end $(date -u +%FT%TZ)"
