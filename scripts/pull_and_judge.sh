#!/bin/bash
# Pull a finished Turing test evaluation into artifacts/baselines/final-v3/test/matrix-<key>/ and start DeepSeek judging.
#   bash scripts/pull_and_judge.sh <turing eval dir name> <matrix key>
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=$1; KEY=$2; D=artifacts/baselines/final-v3/test/matrix-$KEY
ssh turing "test -f anlp-project/runs-out/$SRC/summary.json" || { echo "$SRC not finished"; exit 1; }
mkdir -p "$D"
rsync -az --include 'responses.jsonl' --include 'scores.jsonl' --include 'summary.json' --include 'metadata.json' --exclude '*' \
  "turing:anlp-project/runs-out/$SRC/" "$D/"
(setsid nohup .venv/bin/python scripts/judge_baseline.py --split test --model "matrix-$KEY" --workers 12 > "local/judge-test-$KEY.log" 2>&1 < /dev/null &)
echo "judging matrix-$KEY"
