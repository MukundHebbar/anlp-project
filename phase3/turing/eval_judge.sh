#!/bin/bash
# Judge the cached Phase-3 attempts with a trained self-judge adapter (same protocol as run_part.sh's judging).
# One chain per attempt everywhere (the 4-chain test subset is needed only for the untrained judge).
#   bash phase3/turing/eval_judge.sh <adapter dir> <attempts root> <judge out> <i> <n>
set -euo pipefail
adapter=$1; attempts=$2; out=$3; i=$4; n=$5
for s in dev test extra; do
    python phase3/judge.py --set "$s" --attempts "$attempts" --adapter "$adapter" --out "$out" --part "$i/$n" --chains-first 1
done
echo "judge eval $i/$n done"
