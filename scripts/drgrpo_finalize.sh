#!/bin/bash
# After the Dr. GRPO post jobs (scripts/turing/drgrpo_post.sh) finish: pull the dev selections and test
# answers from Turing, apply the Qwen3.8-27B calibration, and build the transfer-matrix report.
#   bash scripts/drgrpo_finalize.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
SEL=artifacts/opd/evals/v3-drgrpo-dev
mkdir -p "$SEL"
declare -A NODE=([solve]=node11 [judge]=node11 [reconstruct]=node07)  # where each arm ran
declare -A RUN=([solve]=v3-drgrpo-solve-r2 [judge]=v3-drgrpo-judge-r2 [reconstruct]=v3-drgrpo-reconstruct)
for t in solve judge reconstruct; do
  R=/scratch/${NODE[$t]}/mukund.hebbar/anlp-opd/v3/${RUN[$t]}/post
  ssh turing "test -f $R/done" || { echo "$t: post job not finished" >&2; continue; }
  rsync -az "turing:$R/dev/selection.json" "$SEL/selection-$t.json"
  rsync -az "turing:${R%/post}/metrics.jsonl" "$SEL/train-metrics-$t.jsonl"
  for d in $(ssh turing "ls -d $R/test-step*/ 2>/dev/null | xargs -n1 basename"); do
    k=${d#test-step}
    out=artifacts/baselines/final-v3/test/v3-drgrpo-$t-step$k
    mkdir -p "$out"
    rsync -az --include 's*/' --include 's*/*.jsonl' --include 's*/*.json' --include 'metadata.json' --exclude '*' \
      "turing:$R/$d/" "$out/"
    $PY scripts/qwen_judge_calibration.py score "$out/s0"
  done
done
# Merge the per-arm selections into one file for the report.
$PY - <<'EOF'
import json, pathlib
d = pathlib.Path("artifacts/opd/evals/v3-drgrpo-dev")
merged = {"rule": "best own-task dev score among steps 26/52/78/104; ties -> later step"}
for p in sorted(d.glob("selection-*.json")):
    merged.update({k: v for k, v in json.loads(p.read_text()).items() if k != "rule"})
(d / "selection.json").write_text(json.dumps(merged, indent=1) + "\n")
print("selections:", {k: v["selected_step"] for k, v in merged.items() if k != "rule"})
EOF
$PY scripts/report_grpo_matrix.py
