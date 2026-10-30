#!/bin/bash
# Local driver: evaluate the Phase-1 mixed step-75 adapter (home: ~/anlp-opd-shared/grpo/mixed75) exactly as the
# controls are (eval_matrix.py, dev + val200, 4 samples), in the same environment, so the comparison is like for like.
#   bash phase2/mix_control/scripts/eval_mixed.sh node04
set -uo pipefail
cd "$(dirname "$0")/../../.."
NODE=$1
HOST=mukund.hebbar@turing.iiit.ac.in
F='post-quantum|store now|openssh.com/pq'
R=/scratch/mukund.hebbar/mix-control
A=/home/mukund.hebbar/anlp-opd-shared/grpo/mixed75
log() { echo "$(date '+%F %H:%M') [mixed75] $*"; }
t() { timeout 300 ssh -n -o BatchMode=yes $HOST "$@" 2>&1 | grep -v -E "$F"; }
submit() {
  while true; do
    out=$(t "cd ~/anlp-project-grpo && python3 scripts/turing/launch.py reconcile >/dev/null 2>&1; python3 scripts/turing/launch.py submit $*")
    id=$(echo "$out" | grep -oE '"job_id": [0-9]+' | grep -oE '[0-9]+')
    [ -n "$id" ] && { echo "$id"; return; }
    echo "$out" | grep -q refused || { log "submit failed: $out" >&2; exit 1; }
    sleep 120
  done
}
wait_job() {
  while true; do
    local s; s=$(t "sacct -j $1 -X -n -o State | head -1 | tr -d ' '" | tail -1)
    case "$s" in COMPLETED) return;; FAILED|CANCELLED*|TIMEOUT|OUT_OF_ME*|NODE_FAIL) log "job $1 $s"; exit 1;; esac
    sleep 60
  done
}
mkdir -p local/mix-control/evals  # rsync does not create the parent folder
for sp in dev val200; do n=$sp-mixed75-step75
  if [ $sp = dev ]; then split="--split dev"; else split="--split uids --uids-file phase2/failure_driven/data/val_uids.json"; fi
  id=$(submit --name mc-$n --node $NODE --gpus 1 --hours 3 -- bash phase2/failure_driven/scripts/wait_env.sh python scripts/turing/eval_matrix.py \
    --name mc-$n --adapter $A $split --tasks solve --samples 4 --samples-tasks solve --out $R/evals/$n)
  log "$n job $id"; wait_job $id
  timeout 900 rsync -a --include='*/' --include='scores.jsonl' --include='metadata.json' --exclude='*' \
    -e "ssh -o BatchMode=yes" $HOST:/scratch/$NODE/mukund.hebbar/mix-control/evals/$n/ local/mix-control/evals/$n/ 2>&1 | grep -v -E "$F"
done
log "mixed75 dev + val200 evaluated"
