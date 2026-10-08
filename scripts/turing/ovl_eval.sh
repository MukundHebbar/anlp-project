#!/bin/bash
# Run eval_matrix.py on a GPU that an existing job already holds (srun --overlap), on node07, whose shared
# Python install is damaged: uses a copy of the same CPython plus the venv's site-packages.
#
#   bash scripts/turing/ovl_eval.sh <job id> <gpu index in job> <eval name> <out dir> [eval_matrix args...]
set -euo pipefail
JOB=$1; GPU=$2; NAME=$3; OUT=$4; shift 4
R=/scratch/mukund.hebbar/anlp-opd
PY=$R/matrix-adapters/pyenv/cpython-3.12.13-linux-x86_64-gnu/bin/python3.12
mkdir -p "$OUT"
nohup srun --jobid="$JOB" --overlap -n1 --gres=gpu:3 bash -c "export CUDA_VISIBLE_DEVICES=$GPU PYTHONPATH=$R/venv/lib/python3.12/site-packages \
  HF_HOME=$R/hf_cache HF_HUB_OFFLINE=1 VLLM_CACHE_ROOT=$R/vllm_cache TRITON_CACHE_DIR=$R/triton_cache \
  TORCHINDUCTOR_CACHE_DIR=$R/inductor_cache XDG_CACHE_HOME=$R/xdg_cache FLASHINFER_WORKSPACE_BASE=$R/flashinfer \
  PATH=$R/venv/bin:/usr/bin:/bin TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1; cd ~/anlp-project; \
  $PY scripts/turing/eval_matrix.py --name $NAME --out $OUT $*" > "$OUT.ovl.log" 2>&1 &
echo "started $NAME on job $JOB GPU $GPU (log $OUT.ovl.log)"
