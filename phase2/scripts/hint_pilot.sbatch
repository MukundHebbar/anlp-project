#!/bin/bash
# Phase-2 hint pilot on one node with 4 GPUs: census (4 shards) -> agents (1 GPU) -> test (4 shards) -> report.
#   sbatch phase2/scripts/hint_pilot.sbatch            (from the repository copy in $HOME on Turing)
#SBATCH --job-name=p2-hint-pilot
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodelist=node07
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=32
#SBATCH --mem=192G
#SBATCH --time=04:00:00
#SBATCH --output=phase2/runs/slurm-%x-%j.out

set -euo pipefail
ENVROOT=${ENVROOT:-/scratch/$USER/anlp-env}   # built by phase2/scripts/setup_env.sbatch
MINE=/scratch/$USER/phase2
mkdir -p "$MINE"
export PATH=$ENVROOT/venv/bin:$PATH HF_HOME=$MINE/hf_home HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export VLLM_CACHE_ROOT=$MINE/vllm_cache TRITON_CACHE_DIR=$MINE/triton_cache TORCHINDUCTOR_CACHE_DIR=$MINE/inductor_cache
export XDG_CACHE_HOME=$MINE/xdg_cache FLASHINFER_WORKSPACE_BASE=$MINE/flashinfer
BASE=$(ls -d $ENVROOT/hf_cache/hub/models--Qwen--Qwen3.5-2B/snapshots/*/ | head -1)
OUT=${OUT:-phase2/runs/hint-pilot}   # smoke: OUT=phase2/runs/hint-smoke POOL=6 AGENT_ARGS=--any-wrong sbatch --gres=gpu:1 ...
POOL=${POOL:-750}
GPUS=(${CUDA_VISIBLE_DEVICES//,/ })
P="python phase2/scripts/hint_pilot.py --out $OUT --base $BASE --pool $POOL"
mkdir -p $OUT/logs
echo "job $SLURM_JOB_ID on $(hostname) gpus $CUDA_VISIBLE_DEVICES start $(date -u +%FT%TZ) base $BASE"
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader

shards() {  # $1 = stage: one process per GPU
  local pids=() i=0
  for g in "${GPUS[@]}"; do
    CUDA_VISIBLE_DEVICES=$g $P $1 --shard $i --nshards ${#GPUS[@]} > $OUT/logs/$1-$i.log 2>&1 &
    pids+=($!); i=$((i+1))
  done
  for p in "${pids[@]}"; do wait $p; done
}

[ -f $OUT/census/done ] || { shards census; touch $OUT/census/done; }
echo "census done $(date -u +%FT%TZ)"
[ -f $OUT/agents.jsonl ] || CUDA_VISIBLE_DEVICES=${GPUS[0]} $P agents ${AGENT_ARGS:-} > $OUT/logs/agents.log 2>&1
echo "agents done $(date -u +%FT%TZ)"
[ -f $OUT/test/done ] || { shards test; touch $OUT/test/done; }
echo "test done $(date -u +%FT%TZ)"
if [ -n "${FOLLOWUP:-}" ]; then  # FOLLOWUP=1: JUDGE with a 16k cap and the wrong-answer-only control
  [ -f $OUT/agents_followup.jsonl ] || CUDA_VISIBLE_DEVICES=${GPUS[0]} $P followup-agents > $OUT/logs/followup-agents.log 2>&1
  echo "followup agents done $(date -u +%FT%TZ)"
  [ -f $OUT/test_followup/done ] || { shards followup-test; touch $OUT/test_followup/done; }
  echo "followup test done $(date -u +%FT%TZ)"
fi
$P report > $OUT/logs/report.log 2>&1
echo "end $(date -u +%FT%TZ)"
