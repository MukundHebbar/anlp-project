#!/bin/bash
# Tutor and drift experiments (phase2/scripts/functional.py) on one node with 4 GPUs:
# The last two GPUs serve Qwen3.8-27B (tensor parallel) as the comparator; the others run the 2B adapters (one shard each).
#   sbatch phase2/scripts/functional.sbatch            (from the repository copy in $HOME on Turing)
#SBATCH --job-name=p2-functional
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodelist=node07
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=32
#SBATCH --mem=192G
#SBATCH --time=06:00:00
#SBATCH --output=phase2/runs/slurm-%x-%j.out

set -euo pipefail
ENVROOT=${ENVROOT:-/scratch/$USER/anlp-env}   # built by phase2/scripts/setup_env.sbatch
MINE=/scratch/$USER/phase2
mkdir -p "$MINE"
export PATH=$ENVROOT/venv/bin:$PATH HF_HOME=$MINE/hf_home HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export VLLM_CACHE_ROOT=$MINE/vllm_cache TRITON_CACHE_DIR=$MINE/triton_cache TORCHINDUCTOR_CACHE_DIR=$MINE/inductor_cache
export XDG_CACHE_HOME=$MINE/xdg_cache FLASHINFER_WORKSPACE_BASE=$MINE/flashinfer
BASE=$(ls -d $ENVROOT/hf_cache/hub/models--Qwen--Qwen3.5-2B/snapshots/*/ | head -1)
BIG=$(ls -d $ENVROOT/hf_cache/hub/models--Qwen--Qwen3.8-27B/snapshots/*/ | head -1)
OUT=${OUT:-phase2/runs/functional}   # smoke: OUT=phase2/runs/functional-smoke LIMIT=4 sbatch --time=01:00:00 ...
GPUS=(${CUDA_VISIBLE_DEVICES//,/ })
SMALL=("${GPUS[@]:0:${#GPUS[@]}-2}")   # every GPU except the last two, which serve the 27B
BIGGPUS=${GPUS[-2]},${GPUS[-1]}
P="python phase2/scripts/functional.py --out $OUT --base $BASE --big-path $BIG --port 8002 --limit ${LIMIT:-0}"
mkdir -p $OUT/logs
echo "job $SLURM_JOB_ID on $(hostname) gpus $CUDA_VISIBLE_DEVICES start $(date -u +%FT%TZ)"

CUDA_VISIBLE_DEVICES=$BIGGPUS vllm serve $BIG --served-model-name big --port 8002 --dtype bfloat16 \
  --language-model-only --generation-config vllm --seed 0 --tensor-parallel-size 2 --gpu-memory-utilization 0.90 \
  --max-model-len 16384 --max-num-seqs 64 --max-logprobs 20 > $OUT/logs/big-server.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT

shards() {  # $1 = stage: one process per small GPU
  local pids=() i=0
  for g in "${SMALL[@]}"; do
    CUDA_VISIBLE_DEVICES=$g $P $1 --shard $i --nshards ${#SMALL[@]} > $OUT/logs/$1-$i.log 2>&1 &
    pids+=($!); i=$((i+1))
  done
  for p in "${pids[@]}"; do wait $p; done
}
wait_big() {
  for i in $(seq 1 180); do curl -sf http://127.0.0.1:8002/health >/dev/null && return 0
    kill -0 $SERVER 2>/dev/null || { echo "27B server died"; tail -40 $OUT/logs/big-server.log; exit 1; }; sleep 10; done
  echo "27B server not ready"; exit 1
}
once() { [ -f $OUT/logs/$1.done ] || { "${@:2}"; touch $OUT/logs/$1.done; }; echo "$1 done $(date -u +%FT%TZ)"; }

# The 27B builds the tutor items while the 2B solver writes the drift attempts.
( wait_big; once tutor-build $P tutor-build > $OUT/logs/tutor-build.log 2>&1 ) &
BUILD=$!
once drift-attempts shards drift-attempts
wait $BUILD
once tutor-run shards tutor-run
once drift-critics shards drift-critics
once tutor-compare $P tutor-compare > $OUT/logs/tutor-compare.log 2>&1
once drift-compare $P drift-compare > $OUT/logs/drift-compare.log 2>&1
once drift-repair shards drift-repair
$P report > $OUT/logs/report.log 2>&1
echo "end $(date -u +%FT%TZ)"
