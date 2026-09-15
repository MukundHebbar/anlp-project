#!/bin/bash
#SBATCH --job-name=qwen3-4b-eval
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --constraint=l40s
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --time=04:00:00
#SBATCH --output=logs/slurm-%x-%j.out
#SBATCH --error=logs/slurm-%x-%j.err

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/anlp-project}"
TURING_SCRATCH="${TURING_SCRATCH:-/scratch/mukund.hebbar/qwen3-4b}"
ENV_DIR="${ENV_DIR:-$TURING_SCRATCH/venv}"
WHEELHOUSE_DIR="${WHEELHOUSE_DIR:-$PROJECT_DIR/wheelhouse/qwen3-4b-py312-cu126-full}"
LOCAL_WHEELHOUSE="$TURING_SCRATCH/wheelhouse"
OUTPUT_DIR="${OUTPUT_DIR:-$TURING_SCRATCH/outputs}"
MODEL_PATH="${MODEL_PATH:-Qwen/Qwen3-4B}"
EXPLAIN_INPUT="${EXPLAIN_INPUT:-$PROJECT_DIR/artifacts/deepseek-v4-flash/explain/v1-111/results.json}"
EXPLAIN_OUTPUT_FILE="${EXPLAIN_OUTPUT_FILE:-$OUTPUT_DIR/qwen3-4b-explain-v1-23-valid-medium-results.json}"
EXPLAIN_REPORT_FILE="${EXPLAIN_REPORT_FILE:-$OUTPUT_DIR/qwen3-4b-explain-v1-23-valid-medium-report.txt}"
STUDENT_EXPLAIN_PROMPT="${STUDENT_EXPLAIN_PROMPT:-$PROJECT_DIR/data/prompts/explain/student_explain.md}"
SOLVE_INPUT="${SOLVE_INPUT:-$PROJECT_DIR/data/manifests/deepmath/deepmath-pilot-146.json}"
SOLVE_OUTPUT_FILE="${SOLVE_OUTPUT_FILE:-$OUTPUT_DIR/qwen3-4b-solve-146-results.json}"
SOLVE_REPORT_FILE="${SOLVE_REPORT_FILE:-$OUTPUT_DIR/qwen3-4b-solve-146-report.txt}"
SETUP_ONLY="${SETUP_ONLY:-0}"
EVAL_MODE="${EVAL_MODE:-suite}"
UV_BIN="${UV_BIN:-$HOME/.local/bin/uv}"

export UV_CONCURRENT_DOWNLOADS=1
export UV_CONCURRENT_BUILDS=1
export UV_CONCURRENT_INSTALLS=1
export UV_LINK_MODE=copy
export UV_PYTHON_DOWNLOADS=never
export HF_HOME="$TURING_SCRATCH/hf_cache"
export PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
export TRANSFORMERS_CACHE="$TURING_SCRATCH/hf_cache"
export HF_DATASETS_CACHE="$TURING_SCRATCH/hf_datasets"
export UV_CACHE_DIR="$TURING_SCRATCH/uv_cache"
export XDG_CACHE_HOME="$TURING_SCRATCH/xdg_cache"
export VLLM_CACHE_ROOT="$TURING_SCRATCH/vllm_cache"
export TORCHINDUCTOR_CACHE_DIR="$TURING_SCRATCH/torchinductor_cache"
export TRITON_CACHE_DIR="$TURING_SCRATCH/triton_cache"

mkdir -p "$PROJECT_DIR/logs" "$TURING_SCRATCH" "$OUTPUT_DIR"

if [[ "$(id -un)" != "mukund.hebbar" || "${USER:-}" != "mukund.hebbar" ]]; then
    echo "refusing to run as unexpected user: $(id -un) / ${USER:-unset}" >&2
    exit 10
fi
if [[ "$TURING_SCRATCH" != /scratch/mukund.hebbar/qwen3-4b* ]]; then
    echo "scratch path is outside the permitted personal tree: $TURING_SCRATCH" >&2
    exit 11
fi
if [[ "$EXPLAIN_INPUT" != "$PROJECT_DIR"/* ]]; then
    echo "EXPLAIN_INPUT must remain inside the synced project tree: $EXPLAIN_INPUT" >&2
    exit 22
fi
if [[ "$STUDENT_EXPLAIN_PROMPT" != "$PROJECT_DIR"/* ]]; then
    echo "STUDENT_EXPLAIN_PROMPT must remain inside the synced project tree: $STUDENT_EXPLAIN_PROMPT" >&2
    exit 26
fi
if [[ "$SOLVE_INPUT" != "$PROJECT_DIR"/* ]]; then
    echo "SOLVE_INPUT must remain inside the synced project tree: $SOLVE_INPUT" >&2
    exit 24
fi
if [[ "$(stat -c '%U' "$TURING_SCRATCH")" != "mukund.hebbar" ]]; then
    echo "scratch directory is not owned by mukund.hebbar: $TURING_SCRATCH" >&2
    exit 12
fi
if [[ ! -x "$UV_BIN" ]]; then
    echo "existing user-local uv is missing; refusing online installation: $UV_BIN" >&2
    exit 13
fi

module load u22/cuda/12.4
module load u22/python/3.12.4
nvidia-smi
GPU_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1 | sed 's/^ *//;s/ *$//')"
case "$GPU_NAME" in
    *L40S*|*RTX\ 6000*) ;;
    *) echo "refusing unsupported GPU: $GPU_NAME" >&2; exit 14 ;;
esac
if [[ "$GPU_NAME" == *A100* ]]; then
    echo "A100 is explicitly forbidden: $GPU_NAME" >&2
    exit 15
fi

NODE_RECORD="$TURING_SCRATCH/setup-node.txt"
if [[ -f "$NODE_RECORD" ]]; then
    EXPECTED_NODE="$(sed -n '1p' "$NODE_RECORD")"
    if [[ "$EXPECTED_NODE" != "$(hostname)" ]]; then
        echo "persistent scratch belongs to $EXPECTED_NODE, but job landed on $(hostname)" >&2
        echo "resubmit with --nodelist=$EXPECTED_NODE or rebuild deliberately" >&2
        exit 16
    fi
else
    hostname > "$NODE_RECORD"
fi

if [[ ! -d "$WHEELHOUSE_DIR" ]] || ! find "$WHEELHOUSE_DIR" -maxdepth 1 -name '*.whl' -print -quit | grep -q .; then
    echo "Offline wheelhouse is missing or empty: $WHEELHOUSE_DIR" >&2
    exit 2
fi
mkdir -p "$LOCAL_WHEELHOUSE"
if [[ "$(stat -c '%U' "$LOCAL_WHEELHOUSE")" != "mukund.hebbar" ]]; then
    echo "local wheelhouse is not owned by mukund.hebbar: $LOCAL_WHEELHOUSE" >&2
    exit 17
fi
rsync -a --delete "$WHEELHOUSE_DIR/" "$LOCAL_WHEELHOUSE/"
(
    cd "$LOCAL_WHEELHOUSE"
    sha256sum -c wheelhouse.sha256
)

PYTHON312="${PYTHON312:-$(command -v python3.12 || true)}"
if [[ -z "$PYTHON312" ]] || ! "$PYTHON312" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)' >/dev/null 2>&1; then
    PYTHON_DIR="$TURING_SCRATCH/python"
    export UV_PYTHON_INSTALL_DIR="$PYTHON_DIR"
    export UV_PYTHON_BIN_DIR="$TURING_SCRATCH/bin"
    mkdir -p "$PYTHON_DIR" "$UV_PYTHON_BIN_DIR"
  UV_PYTHON_DOWNLOADS=auto "$UV_BIN" python install 3.12
    PYTHON312="$("$UV_BIN" python find 3.12 --managed-python)"
fi

if [[ ! -x "$ENV_DIR/bin/python" ]]; then
    "$UV_BIN" venv --python "$PYTHON312" --seed "$ENV_DIR"
fi
if [[ "${FORCE_ENV_REFRESH:-0}" == "1" ]] || ! "$ENV_DIR/bin/python" -c 'import vllm, transformers, torch' >/dev/null 2>&1; then
    UV_OFFLINE=1 "$UV_BIN" pip sync \
        --python "$ENV_DIR/bin/python" \
        --no-index \
        --find-links "$LOCAL_WHEELHOUSE" \
        --only-binary=:all: \
        "$LOCAL_WHEELHOUSE/requirements.lock.txt"
fi

UV_OFFLINE=1 "$UV_BIN" pip check --python "$ENV_DIR/bin/python"

cd "$PROJECT_DIR"
echo "job_id=$SLURM_JOB_ID"
echo "job_name=$SLURM_JOB_NAME"
echo "host=$(hostname)"
echo "gpu=$GPU_NAME"
echo "cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
echo "start_time=$(date --iso-8601=seconds)"
echo "project_dir=$PROJECT_DIR"
echo "scratch_dir=$TURING_SCRATCH"
echo "venv=$ENV_DIR"
nvidia-smi
module list 2>&1 || true
"$ENV_DIR/bin/python" -c 'import sys, vllm, transformers, torch; print("python", sys.version); print("vllm", vllm.__version__); print("transformers", transformers.__version__); print("torch", torch.__version__); print("cuda_available", torch.cuda.is_available()); print("gpu", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "unavailable"); raise SystemExit(0 if torch.cuda.is_available() else 18)'

if [[ "$SETUP_ONLY" == "1" ]]; then
    echo "setup_only=1"
    echo "end_time=$(date --iso-8601=seconds)"
    exit 0
fi

if [[ "$EVAL_MODE" == "explain-v1" ]]; then
    if [[ ! -f "$EXPLAIN_INPUT" ]]; then
        echo "EXPLAIN-v1 input is missing: $EXPLAIN_INPUT" >&2
        exit 23
    fi
    "$ENV_DIR/bin/python" -m anlp_project.qwen3_turing_eval \
        --mode explain-v1 \
        --model "$MODEL_PATH" \
        --input "$EXPLAIN_INPUT" \
        --student-prompt "$STUDENT_EXPLAIN_PROMPT" \
        --explain-output "$EXPLAIN_OUTPUT_FILE" \
        --report "$EXPLAIN_REPORT_FILE" \
        --batch-size 4 \
        --max-tokens 8192
elif [[ "$EVAL_MODE" == "suite" ]]; then
    "$ENV_DIR/bin/python" -m anlp_project.qwen3_turing_eval \
        --model "$MODEL_PATH" \
        --input "$SOLVE_INPUT" \
        --explain-output "$OUTPUT_DIR/qwen3-4b-turing-explain-results.json" \
        --solve-output "$OUTPUT_DIR/qwen3-4b-turing-solve-results.json" \
        --report "$OUTPUT_DIR/qwen3-4b-turing-evaluation-report.txt" \
        --batch-size 4 \
        --max-tokens 8192
elif [[ "$EVAL_MODE" == "solve-only" ]]; then
    if [[ ! -f "$SOLVE_INPUT" ]]; then
        echo "SOLVE input is missing: $SOLVE_INPUT" >&2
        exit 25
    fi
    "$ENV_DIR/bin/python" -m anlp_project.qwen3_turing_eval \
        --mode solve-only \
        --model "$MODEL_PATH" \
        --input "$SOLVE_INPUT" \
        --solve-output "$SOLVE_OUTPUT_FILE" \
        --report "$SOLVE_REPORT_FILE" \
        --batch-size 4 \
        --max-tokens 8192
else
    echo "unsupported EVAL_MODE: $EVAL_MODE" >&2
    exit 19
fi

echo "end_time=$(date --iso-8601=seconds)"
