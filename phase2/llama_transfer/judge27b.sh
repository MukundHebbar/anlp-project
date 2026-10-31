#!/bin/bash
# Final Qwen3.8-27B judging of Llama test answers, as in the Qwen study (scripts/turing/drgrpo_post.sh step 4), on
# node08: the eval folders are judged where the arms wrote them (sample 0's JUDGE / RECONSTRUCT answers ->
# s0/judgments.qwen.jsonl), then pulled to artifacts/baselines/llama3b/test/<name>/ and calibrated locally
# (scripts/qwen_judge_calibration.py score). The 27B was copied from node06 into node08's model cache on
# 2026-10-28 (node06 was fully occupied).
#   bash phase2/llama_transfer/judge27b.sh <label> <name>=<eval dir on node08> ...
set -euo pipefail -f  # -f: no globbing, the rsync patterns are passed as written
cd "$(dirname "$0")/../.."
LABEL=$1; shift
HOST=mukund.hebbar@turing.iiit.ac.in
F='post-quantum|store now|openssh.com/pq'
BASE=/scratch/mukund.hebbar/llama-transfer
OUT=artifacts/baselines/llama3b/test
log() { echo "$(date '+%F %H:%M') [$LABEL] $*"; }
t() { timeout 300 ssh -n -o BatchMode=yes $HOST "$@" 2>&1 | grep -v -E "$F" || true; }
ARGS=""
for spec in "$@"; do
  dir=${spec#*=}
  [ -n "$(t "test -s /scratch/node08${dir#/scratch}/s0/responses.jsonl && echo yes")" ] || { log "no answers in $dir"; exit 1; }
  ARGS="$ARGS --eval-dir test:$dir/s0"
done
while :; do
  out=$(t "cd ~/anlp-project-grpo && python3 scripts/turing/launch.py reconcile >/dev/null; python3 phase2/llama_transfer/submit.py \
    --name llama3b-judge27b-$LABEL-n08 --node node08 --gpus 2 --hours 4 -- \
    python scripts/turing/qwen_judge_run.py --out $BASE/judge27b-$LABEL/answers.jsonl $ARGS")
  id=$(echo "$out" | grep -oE '"job_id": [0-9]+' | grep -oE '[0-9]+' || true)
  [ -n "$id" ] && break
  echo "$out" | grep -q refused || { log "submit failed: $out"; exit 1; }
  sleep 300
done
log "27B judging job $id"
while :; do
  s=$(t "sacct -j $id -X -n -o State | head -1 | tr -d ' '" | tail -1)
  case "$s" in COMPLETED) break;; FAILED|CANCELLED*|TIMEOUT|OUT_OF_ME*|NODE_FAIL) log "job $id $s"; exit 1;; esac
  sleep 120
done
for spec in "$@"; do
  name=${spec%%=*}; dir=${spec#*=}
  mkdir -p $OUT/$name
  timeout 900 rsync -a --include='s*/' --include='s*/*.jsonl' --include='s*/*.json' --include='metadata.json' --exclude='*' \
    -e "ssh -o BatchMode=yes" "$HOST:/scratch/node08${dir#/scratch}/" $OUT/$name/ 2>&1 | grep -v -E "$F" || true
  .venv/bin/python scripts/qwen_judge_calibration.py score $OUT/$name/s0
done
log "judged and calibrated: $*"
