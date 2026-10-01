#!/bin/bash
#SBATCH --job-name=sft-reconstruct-n256
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodelist=node07
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=01:00:00
#SBATCH --output=/home/mukund.hebbar/anlp-project-v3/runs/sft-reconstruct-n256/slurm-%j.out

set -euo pipefail
ROOT=/scratch/$USER/anlp-opd
export HF_HOME=$ROOT/hf_cache HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export VLLM_CACHE_ROOT=$ROOT/vllm_cache TRITON_CACHE_DIR=$ROOT/triton_cache TORCHINDUCTOR_CACHE_DIR=$ROOT/inductor_cache
export XDG_CACHE_HOME=$ROOT/xdg_cache FLASHINFER_WORKSPACE_BASE=$ROOT/flashinfer
export PATH=$ROOT/venv/bin:$PATH
cd /home/mukund.hebbar/anlp-project-v3
mkdir -p /scratch/$USER/anlp-opd/runs/sft-reconstruct-n256
echo "job $SLURM_JOB_ID on $(hostname) gpus $CUDA_VISIBLE_DEVICES start $(date -u +%FT%TZ)"
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader
timeout --signal=TERM --kill-after=120 3300s python scripts/turing/sft.py --data /scratch/$USER/anlp-opd/runs/gen-reconstruct-w512/sft.jsonl --n 256 --out /scratch/$USER/anlp-opd/runs/sft-reconstruct-n256
echo "end $(date -u +%FT%TZ)"
