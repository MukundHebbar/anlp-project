#!/bin/bash
# Four independent Qwen3-4B vLLM workers on node07. Scratch is job-local only.
#SBATCH --job-name=qwen3-4b-witness
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --constraint=l40s
#SBATCH --nodelist=node07
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=192G
#SBATCH --gres=gpu:4
#SBATCH --time=08:00:00
#SBATCH --output=logs/slurm-%x-%j.out
#SBATCH --error=logs/slurm-%x-%j.err

set -euo pipefail
PROJECT_DIR="${PROJECT_DIR:-$HOME/anlp-project}"
RUN_ROOT="${RUN_ROOT:-/scratch/mukund.hebbar/qwen3-4b-witness-v1-112}"
ENV_DIR="${ENV_DIR:-$RUN_ROOT/venv}"
HF_HOME="${HF_HOME:-$RUN_ROOT/hf_cache}"
WHEELHOUSE_DIR="${WHEELHOUSE_DIR:-$PROJECT_DIR/wheelhouse/qwen3-4b-py312-cu126-full}"
MODEL_PATH="${MODEL_PATH:-Qwen/Qwen3-4B}"
INPUT_FILE="${INPUT_FILE:-$PROJECT_DIR/artifacts/deepseek-v4-flash/witness/v1-113/results.json}"
PROMPT_FILE="${PROMPT_FILE:-$PROJECT_DIR/data/prompts/witness/witness_student.txt}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$PROJECT_DIR/artifacts/qwen3-4b/witness/v1-112}"
RUN_WORKERS=4; BATCH_SIZE=5; MAX_TOKENS=16384; MAX_MODEL_LEN=32768; MAX_NUM_SEQS=5
UV_BIN="${UV_BIN:-$HOME/.local/bin/uv}"

[[ "$(id -un)" == "mukund.hebbar" && "${USER:-}" == "mukund.hebbar" ]] || { echo "unexpected user" >&2; exit 10; }
[[ "${SLURMD_NODENAME:-}" == "node07" ]] || { echo "run must land on node07" >&2; exit 11; }
[[ "$RUN_ROOT" == /scratch/mukund.hebbar/qwen3-4b-witness-* ]] || { echo "invalid scratch root" >&2; exit 12; }
[[ -f "$INPUT_FILE" && -f "$PROMPT_FILE" ]] || { echo "input or prompt missing" >&2; exit 13; }

module load u22/cuda/12.4
module load u22/python/3.12.4
mkdir -p "$RUN_ROOT" "$RUN_ROOT/shards" "$RUN_ROOT/results" "$RUN_ROOT/logs" "$HF_HOME" "$RUN_ROOT/uv_cache" "$RUN_ROOT/xdg_cache" "$ARTIFACT_DIR"
[[ "$(stat -c '%U' "$RUN_ROOT")" == "mukund.hebbar" ]] || { echo "scratch ownership check failed" >&2; exit 14; }
printf '%s\n' "$(hostname)" > "$RUN_ROOT/node-record.txt"
GPU_COUNT="$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)"
GPU_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1 | sed 's/^ *//;s/ *$//')"
[[ "$GPU_COUNT" -eq 4 && "$GPU_NAME" == *L40S* ]] || { echo "expected four L40S GPUs" >&2; exit 15; }
[[ -x "$UV_BIN" ]] || { echo "uv missing: $UV_BIN" >&2; exit 16; }
[[ -d "$WHEELHOUSE_DIR" ]] || { echo "wheelhouse missing: $WHEELHOUSE_DIR" >&2; exit 17; }

export HF_HOME TRANSFORMERS_CACHE="$HF_HOME" HF_DATASETS_CACHE="$RUN_ROOT/hf_datasets"
export UV_CACHE_DIR="$RUN_ROOT/uv_cache" XDG_CACHE_HOME="$RUN_ROOT/xdg_cache" VLLM_CACHE_ROOT="$RUN_ROOT/vllm_cache"
export TORCHINDUCTOR_CACHE_DIR="$RUN_ROOT/torchinductor_cache" TRITON_CACHE_DIR="$RUN_ROOT/triton_cache"
export PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" UV_CONCURRENT_DOWNLOADS=1 UV_CONCURRENT_BUILDS=1 UV_CONCURRENT_INSTALLS=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

LOCAL_WHEELHOUSE="$RUN_ROOT/wheelhouse"
rsync -a --delete "$WHEELHOUSE_DIR/" "$LOCAL_WHEELHOUSE/"
if [[ ! -x "$ENV_DIR/bin/python" ]]; then "$UV_BIN" venv --python "$(command -v python3.12)" --seed "$ENV_DIR"; fi
if ! "$ENV_DIR/bin/python" -c 'import vllm, transformers, torch' >/dev/null 2>&1; then
    UV_OFFLINE=1 "$UV_BIN" pip sync --python "$ENV_DIR/bin/python" --no-index --find-links "$LOCAL_WHEELHOUSE" --only-binary=:all: "$LOCAL_WHEELHOUSE/requirements.lock.txt"
fi
UV_OFFLINE=1 "$UV_BIN" pip check --python "$ENV_DIR/bin/python"

START_EPOCH="$(date +%s)"
echo "job_id=$SLURM_JOB_ID host=$(hostname) model=$MODEL_PATH batch_size=$BATCH_SIZE max_tokens=$MAX_TOKENS start_time=$(date --iso-8601=seconds)"
nvidia-smi
(
    while true; do date --iso-8601=seconds; nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader; sleep 10; done
) > "$RUN_ROOT/logs/gpu-utilization.csv" 2>&1 &
GPU_LOG_PID=$!; trap 'kill "$GPU_LOG_PID" 2>/dev/null || true' EXIT

"$ENV_DIR/bin/python" -m anlp_project.qwen3_witness_parallel shard "$INPUT_FILE" "$RUN_ROOT/shards" --count "$RUN_WORKERS"
mapfile -t GPU_IDS < <(echo "${CUDA_VISIBLE_DEVICES:-0,1,2,3}" | tr ',' '\n')
(( ${#GPU_IDS[@]} >= RUN_WORKERS )) || { echo "fewer than four visible GPUs" >&2; exit 18; }
pids=()
for ((worker=0; worker<RUN_WORKERS; worker++)); do
    worker_root="$RUN_ROOT/worker-$worker"; mkdir -p "$worker_root/vllm_cache" "$worker_root/xdg_cache"
    (
        export CUDA_VISIBLE_DEVICES="${GPU_IDS[$worker]}" VLLM_CACHE_ROOT="$worker_root/vllm_cache" XDG_CACHE_HOME="$worker_root/xdg_cache" OMP_NUM_THREADS=8 MKL_NUM_THREADS=8
        "$ENV_DIR/bin/python" -m anlp_project.qwen3_turing_eval --mode witness --model "$MODEL_PATH" \
            --input "$RUN_ROOT/shards/shard-$(printf '%02d' "$worker").json" --witness-prompt "$PROMPT_FILE" \
            --witness-output "$RUN_ROOT/results/shard-$worker-results.json" --report "$RUN_ROOT/results/shard-$worker-report.txt" \
            --batch-size "$BATCH_SIZE" --max-tokens "$MAX_TOKENS" --max-model-len "$MAX_MODEL_LEN" --max-num-seqs "$MAX_NUM_SEQS" \
            --gpu-memory-utilization 0.90 --dtype auto --temperature 0.7 --top-p 0.8 --top-k 20 --seed 42
    ) > "$RUN_ROOT/logs/worker-$worker.out" 2> "$RUN_ROOT/logs/worker-$worker.err" &
    pids+=("$!")
done
failed=0; for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
(( failed == 0 )) || { echo "worker failure; partial results preserved" >&2; exit 19; }

"$ENV_DIR/bin/python" -m anlp_project.qwen3_witness_parallel merge "$INPUT_FILE" "$RUN_ROOT/results" "$ARTIFACT_DIR" --start-epoch "$START_EPOCH"
cp "$RUN_ROOT/logs/gpu-utilization.csv" "$ARTIFACT_DIR/gpu-utilization.csv"
echo "end_time=$(date --iso-8601=seconds)"
