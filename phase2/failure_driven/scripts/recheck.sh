#!/bin/bash
# Unaided re-solve of buffered questions: 8 samples each at the training cap (16,384 tokens, no continuation).
#   bash phase2/failure_driven/scripts/env.sh bash phase2/failure_driven/scripts/recheck.sh <adapter> <uids.json> <name>
set -euo pipefail
python scripts/turing/eval_matrix.py --name "$3" --adapter "$1" --split uids --uids-file "$2" \
  --rows-file phase2/failure_driven/data/solve_rows.jsonl --tasks solve --samples 8 --samples-tasks solve \
  --first-cap 16384 --max-cap 16384 --out /scratch/$USER/failure-driven/evals/$3
