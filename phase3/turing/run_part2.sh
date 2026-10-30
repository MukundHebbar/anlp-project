#!/bin/bash
# Phase-3 worker, second order (2026-10-29): finish dev/test/extra, judge them, then generate the Stage-2 train set.
# Same outputs as run_part.sh; every step resumes by chunk, so restarting a worker loses at most one chunk.
#   bash phase3/turing/run_part2.sh <i> <n> <out dir>
set -euo pipefail
i=$1; n=$2; out=$3
A=final-adapters/mixed-step75
for s in dev test extra; do
    python phase3/gen.py --set "$s" --adapter "$A" --out "$out/attempts" --chunk 50 --part "$i/$n"
done
for s in dev test extra; do
    python phase3/judge.py --set "$s" --attempts "$out/attempts" --adapter "$A" --out "$out/judge" --part "$i/$n"
done
python phase3/gen.py --set train --adapter "$A" --out "$out/attempts" --chunk 50 --part "$i/$n" --limit 600
echo "worker $i/$n done"
