#!/bin/bash
# One allocated GPU: native Instruct BF16 smoke check on dev, then the frozen SOLVE test baseline.
set -euo pipefail
if [ "${1:-}" != --in-env ]; then
    exec bash phase2/failure_driven/scripts/env.sh bash "$0" --in-env
fi

MODEL=mistralai/Ministral-3-3B-Instruct-2512-BF16
PINNED=${ANLP_MINISTRAL_MODEL_PATH:-$HOME/anlp-models/Ministral-3-3B-Instruct-2512-BF16-b6d637be}
OUT=/scratch/$USER/ministral-baseline
# Download runs on the login node without GPUs; wait only if the allocation arrives first.
for _ in $(seq 90); do
    [ -f "$PINNED/source.json" ] && break
    sleep 10
done
[ -f "$PINNED/source.json" ] || { echo "Pinned model download has not finished"; exit 1; }
mkdir -p "$OUT"
cp "$PINNED/source.json" "$OUT/model-source.json"

# The smoke run tests model loading, native tokenization and the shared scoring pipeline only.
if [ ! -f "$OUT/smoke-dev/done" ]; then
    python scripts/turing/eval_matrix.py --name ministral-instruct-bf16-smoke \
        --model "$MODEL" --model-path "$PINNED" --model-format mistral --chat-mode instruct \
        --split dev --limit 2 --tasks solve --samples 1 --samples-tasks solve --out "$OUT/smoke-dev"
fi
if [ ! -f "$OUT/test/done" ]; then
    python scripts/turing/eval_matrix.py --name ministral-instruct-bf16-solve-test \
        --model "$MODEL" --model-path "$PINNED" --model-format mistral --chat-mode instruct \
        --split test --tasks solve --samples 4 --samples-tasks solve --out "$OUT/test"
fi
