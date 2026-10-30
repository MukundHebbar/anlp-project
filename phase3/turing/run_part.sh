#!/bin/bash
# One Phase-3 worker (1 GPU): generate its share of every set, then judge the same chunks.
#   bash phase3/turing/run_part.sh <i> <n> <out dir>        (from the repository root, inside a GPU job)
# Worker i takes chunks with index % n == i, so n workers never collide; every step is resumable by chunk.
set -euo pipefail
i=$1; n=$2; out=$3
A=final-adapters/mixed-step75
for s in dev test extra train; do
    lim=()
    [ "$s" = train ] && lim=(--limit 600)
    python phase3/gen.py --set "$s" --adapter "$A" --out "$out/attempts" --chunk 50 --part "$i/$n" "${lim[@]}"
done
for s in dev test extra; do
    python phase3/judge.py --set "$s" --attempts "$out/attempts" --adapter "$A" --out "$out/judge" --part "$i/$n"
done
echo "worker $i/$n done"
