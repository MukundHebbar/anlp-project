#!/bin/bash
#SBATCH --job-name=x200-reconstruct-base
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodelist=node07
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=00:30:00
#SBATCH --output=/home/mukund.hebbar/anlp-project-v3/runs/x200-reconstruct-base/slurm-%j.out

set -euo pipefail
ROOT=/scratch/$USER/anlp-opd
export HF_HOME=$ROOT/hf_cache HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export VLLM_CACHE_ROOT=$ROOT/vllm_cache TRITON_CACHE_DIR=$ROOT/triton_cache TORCHINDUCTOR_CACHE_DIR=$ROOT/inductor_cache
export XDG_CACHE_HOME=$ROOT/xdg_cache FLASHINFER_WORKSPACE_BASE=$ROOT/flashinfer
export PATH=$ROOT/venv/bin:$PATH
cd /home/mukund.hebbar/anlp-project-v3
mkdir -p /scratch/$USER/anlp-opd/runs/x200-reconstruct-base
echo "job $SLURM_JOB_ID on $(hostname) gpus $CUDA_VISIBLE_DEVICES start $(date -u +%FT%TZ)"
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader
timeout --signal=TERM --kill-after=120 1500s python scripts/turing/dev_generate.py --task reconstruct --questions extra200 --out /scratch/$USER/anlp-opd/runs/x200-reconstruct-base
echo "end $(date -u +%FT%TZ)"
