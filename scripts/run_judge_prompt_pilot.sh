#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

JUDGE_SHARE_ROOT="${JUDGE_SHARE_ROOT:-/share3/${USER:?USER is not set}}"
JUDGE_QWEN8B_MODEL="${JUDGE_QWEN8B_MODEL:-${JUDGE_SHARE_ROOT}/models/Qwen3-8B}"
JUDGE_PYTHON_BIN="${JUDGE_PYTHON_BIN:-/home2/${USER}/CausalRepLearning/.venv/bin/python}"
if [[ ! -x "$JUDGE_PYTHON_BIN" ]]; then
    JUDGE_PYTHON_BIN="$(command -v python3)"
fi
if ! "$JUDGE_PYTHON_BIN" -c 'import vllm' >/dev/null 2>&1; then
    echo "vLLM is missing from $JUDGE_PYTHON_BIN; install the project Turing runtime before running the pilot." >&2
    echo "See requirements-turing-qwen3.in (the repository pins vllm==0.10.1)." >&2
    exit 3
fi

MANIFEST="${JUDGE_SOURCE_MANIFEST:-data/manifests/deepmath/judge-dev-60-generator.json}"
PROMPT="${JUDGE_GENERATOR_PROMPT:-data/prompts/judge/judge_generator_v5_method_preserving.md}"
OUTPUT_DIR="artifacts/qwen3-8b/judge"
mkdir -p "$OUTPUT_DIR"

candidate="$(basename "$PROMPT" .md)"
output="${JUDGE_OUTPUT:-$OUTPUT_DIR/${candidate}-qwen-confirmation.json}"
echo "Confirming $candidate with $JUDGE_QWEN8B_MODEL"
"$JUDGE_PYTHON_BIN" -m anlp_project.judge_generation \
    --manifest "$MANIFEST" \
    --prompt "$PROMPT" \
    --model "$JUDGE_QWEN8B_MODEL" \
    --output "$output" \
    --labels both \
    --batch-size "${JUDGE_BATCH_SIZE:-4}" \
    --max-tokens "${JUDGE_MAX_TOKENS:-4096}" \
    --temperature "${JUDGE_TEMPERATURE:-0.2}" \
    --top-p "${JUDGE_TOP_P:-0.9}" \
    --top-k "${JUDGE_TOP_K:-20}" \
    --tensor-parallel-size "${JUDGE_TENSOR_PARALLEL_SIZE:-1}"

echo "Qwen confirmation artifact: $output"
