#!/usr/bin/env bash
set -euo pipefail

# End-to-end entry point for a cluster where the shell itself may be inside a
# CPU-only job. It launches the actual work as a task in a fresh allocation.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SHARE_ROOT="${JUDGE_SHARE_ROOT:-/share3/${USER:?USER is not set}}"
PARTITION="${JUDGE_PARTITION:-u22}"
ACCOUNT="${JUDGE_ACCOUNT:-research}"
QOS="${JUDGE_QOS:-medium}"
GPU_COUNT="${JUDGE_GPU_COUNT:-2}"
CPUS="${JUDGE_CPUS:-10}"
MEM_PER_CPU="${JUDGE_MEM_PER_CPU:-2G}"
TIME_LIMIT="${JUDGE_TIME_LIMIT:-06:00:00}"
TENSOR_PARALLEL_SIZE="${JUDGE_TENSOR_PARALLEL_SIZE:-$GPU_COUNT}"

if [[ "$GPU_COUNT" -lt 1 || "$TENSOR_PARALLEL_SIZE" -lt 1 ]]; then
    echo "JUDGE_GPU_COUNT and JUDGE_TENSOR_PARALLEL_SIZE must be positive" >&2
    exit 2
fi

salloc --immediate=60 \
    --partition="$PARTITION" \
    --account="$ACCOUNT" \
    --qos="$QOS" \
    --gres="gpu:${GPU_COUNT}" \
    --cpus-per-task="$CPUS" \
    --mem-per-cpu="$MEM_PER_CPU" \
    --time="$TIME_LIMIT" \
    srun --cpu-bind=none --ntasks=1 --cpus-per-task="$CPUS" --gres="gpu:${GPU_COUNT}" \
    env PROJECT_ROOT="$PROJECT_ROOT" SHARE_ROOT="$SHARE_ROOT" TENSOR_PARALLEL_SIZE="$TENSOR_PARALLEL_SIZE" \
    bash -lc '
        set -euo pipefail
        cd "$PROJECT_ROOT"
        if command -v module >/dev/null 2>&1; then
            module load u22/python/3.12.4
        fi
        export JUDGE_PYTHON_BIN="${JUDGE_PYTHON_BIN:-/home2/${USER}/CausalRepLearning/.venv/bin/python}"
        if [[ ! -x "$JUDGE_PYTHON_BIN" ]]; then
            JUDGE_PYTHON_BIN="$(command -v python3)"
            export JUDGE_PYTHON_BIN
        fi
        if [[ ! -d "$SHARE_ROOT" || ! -w "$SHARE_ROOT" ]]; then
            echo "Persistent share is missing or not writable: $SHARE_ROOT" >&2
            exit 3
        fi
        export JUDGE_SHARE_ROOT="$SHARE_ROOT"
        bash scripts/download_judge_models.sh
        "$JUDGE_PYTHON_BIN" scripts/smoke_test_judge_models.py --model-root "$SHARE_ROOT/models"
        JUDGE_TENSOR_PARALLEL_SIZE="$TENSOR_PARALLEL_SIZE" bash scripts/run_judge_prompt_pilot.sh
    '
