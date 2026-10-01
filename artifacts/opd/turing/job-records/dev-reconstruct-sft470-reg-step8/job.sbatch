#!/bin/bash
#SBATCH --job-name=dev-reconstruct-sft470-reg-step8
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodelist=node07
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=00:30:00
#SBATCH --output=/home/mukund.hebbar/anlp-project-v3/runs/dev-reconstruct-sft470-reg-step8/slurm-%j.out

set -euo pipefail
ROOT=/scratch/$USER/anlp-opd
export HF_HOME=$ROOT/hf_cache HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export VLLM_CACHE_ROOT=$ROOT/vllm_cache TRITON_CACHE_DIR=$ROOT/triton_cache TORCHINDUCTOR_CACHE_DIR=$ROOT/inductor_cache
export XDG_CACHE_HOME=$ROOT/xdg_cache FLASHINFER_WORKSPACE_BASE=$ROOT/flashinfer
export PATH=$ROOT/venv/bin:$PATH
cd /home/mukund.hebbar/anlp-project-v3
mkdir -p /scratch/$USER/anlp-opd/runs/dev-reconstruct-sft470-reg-step8
echo "job $SLURM_JOB_ID on $(hostname) gpus $CUDA_VISIBLE_DEVICES start $(date -u +%FT%TZ)"
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader
timeout --signal=TERM --kill-after=120 1500s python scripts/turing/dev_generate.py --task reconstruct --adapter /scratch/$USER/anlp-opd/runs/opd-reconstruct-sft470-plain-anchor0.5-ol1.0-tprompt/adapters/step8 --out /scratch/$USER/anlp-opd/runs/dev-reconstruct-sft470-reg-step8
echo "end $(date -u +%FT%TZ)"
