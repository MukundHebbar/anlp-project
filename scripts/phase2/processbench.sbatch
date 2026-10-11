#!/bin/bash
# JUDGE on synthetic vs natural errors (scripts/phase2/processbench_eval.py): base 2B, the three specialists, the
# mixed model and Qwen3.5-9B on ProcessBench and the FINAL-v3 JUDGE test set. Needs data/external/processbench/*.json
# and Qwen3.5-9B in our model cache (REPOS=Qwen/Qwen3.5-9B sbatch scripts/phase2/setup_env.sbatch).
#SBATCH --job-name=p2-processbench
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodelist=node07
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:3
#SBATCH --cpus-per-task=24
#SBATCH --mem=160G
#SBATCH --time=05:00:00
#SBATCH --output=runs-out/slurm-%x-%j.out

set -euo pipefail
ENVROOT=${ENVROOT:-/scratch/$USER/anlp-env}
MINE=/scratch/$USER/phase2
export PATH=$ENVROOT/venv/bin:$PATH HF_HOME=$MINE/hf_home HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export VLLM_CACHE_ROOT=$MINE/vllm_cache TRITON_CACHE_DIR=$MINE/triton_cache TORCHINDUCTOR_CACHE_DIR=$MINE/inductor_cache
export XDG_CACHE_HOME=$MINE/xdg_cache FLASHINFER_WORKSPACE_BASE=$MINE/flashinfer
BASE=$(ls -d $ENVROOT/hf_cache/hub/models--Qwen--Qwen3.5-2B/snapshots/*/ | head -1)
BIG9=$(ls -d $ENVROOT/hf_cache/hub/models--Qwen--Qwen3.5-9B/snapshots/*/ | head -1)
OUT=${OUT:-runs-out/processbench}
P="python scripts/phase2/processbench_eval.py --out $OUT --base $BASE --big9 $BIG9"
mkdir -p $OUT/logs
echo "job $SLURM_JOB_ID on $(hostname) gpus $CUDA_VISIBLE_DEVICES start $(date -u +%FT%TZ)"
[ -f $OUT/items.jsonl ] || $P prepare --pb-dir data/external/processbench
GPUS=(${CUDA_VISIBLE_DEVICES//,/ })
# Three GPUs: two 2B models each on the first two; RECONSTRUCT then the 9B (own process) on the third.
CUDA_VISIBLE_DEVICES=${GPUS[0]} $P run --models base,judge > $OUT/logs/run-0.log 2>&1 &
A=$!
CUDA_VISIBLE_DEVICES=${GPUS[1]} $P run --models solve,mixed > $OUT/logs/run-1.log 2>&1 &
B=$!
( CUDA_VISIBLE_DEVICES=${GPUS[2]} $P run --models reconstruct > $OUT/logs/run-2.log 2>&1 && \
  CUDA_VISIBLE_DEVICES=${GPUS[2]} $P run --models qwen3.5-9b > $OUT/logs/run-3.log 2>&1 ) &
C=$!
wait $A; wait $B; wait $C
$P report > $OUT/logs/report.log 2>&1
echo "end $(date -u +%FT%TZ)"
