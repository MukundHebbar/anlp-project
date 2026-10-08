#!/bin/bash
# End-to-end SOLVE Dr. GRPO, run from the workstation (2026-10-07 recipe):
#   lr 1e-5 (LoRA r64), 32 questions x 8 answers, overlapped rollouts, 16k cap, checker v3, one pass = 106 steps.
#   Main training metric: the 8-step rolling mean reward; the 3 best adapters by it are kept (adapters/best-step<k>).
# Never more than 4 Turing GPUs at once (launch.py enforces it).
#
#   SWITCH_JOB=<running non-overlapped job> nohup bash scripts/solve_grpo_pipeline.sh > <log> 2>&1 &
#
# Stop training by hand at any time: `touch artifacts/opd/evals/<run>/STOP` (stops after the running chunk's
# next resubmission point), or cancel the training job on Turing (scancel <id>; the id is in <run>/train_job).
# Either way the pipeline then picks the final model and evaluates it.
#
# 1. (SWITCH_JOB) wait for the running job's next saved step, cancel it, resume from there with overlap on.
# 2. Training in <=14 h chunks on node11 (2 GPUs), each resuming from the newest adapter with optimizer state,
#    until step 106, an AUTO-STOP, or a manual stop. A chunk without progress stops the pipeline.
# 3. Candidates: the best adapter by rolling reward, the best every-8 adapter by rolling reward, the last step.
#    Dev eval of each (200 dev questions x 4) on node11, then the best dev accuracy wins (ties -> later step).
# 4. Test eval of the winner on all three test sets (SOLVE 4 samples). 5. Qwen3.8-27B judging of the JUDGE and
#    RECONSTRUCT test answers. 6. Local calibration and the transfer-matrix report.
set -o pipefail
cd "$(dirname "$0")/.."
RUN=${RUN:-solve-p1-lr1e-5}
LAST=${LAST:-106}
SETS="--set prompts_per_step=32 --set optimizer.lr=1e-5 --set optimizer.warmup_steps=5 --set async_rollouts=true --set best_window=8 --set best_keep=3"
N11=/scratch/node11/mukund.hebbar/anlp-opd/v3          # login-node view of node11 scratch
NODE_V3=/scratch/mukund.hebbar/anlp-opd/v3             # the node's own view
A=$N11/$RUN
AN=$NODE_V3/$RUN
OUT=artifacts/baselines/final-v3/test
LOCAL=artifacts/opd/evals/$RUN
BASE_DEV=artifacts/opd/evals/v3-pass4-2b-dev
PY=.venv/bin/python
mkdir -p "$LOCAL"
log() { echo "$(date '+%F %H:%M') $*"; }
t() { ssh -o ConnectTimeout=30 -o ServerAliveInterval=30 turing "$@"; }
submit() {  # submit <launch.py args...> -> the job id (empty if refused, e.g. by the 4-GPU cap)
  t "cd ~/anlp-project && python3 scripts/turing/launch.py submit $*" 2>&1 | tee -a "$LOCAL/submits.log" \
    | grep -oE '"job_id": [0-9]+' | grep -oE '[0-9]+'
}
running() {  # an ssh failure counts as "still running", never as "finished"
  local out; out=$(t "squeue -h -j $1 -o %T" 2>/dev/null) || return 0
  [ -n "$out" ]
}
wait_job() { while running "$1"; do sleep 120; done; }
job_state() { t "sacct -j $1 -X -n -o State" | head -1 | awk '{print $1}'; }
submit_retry() { local j=""; while [ -z "$j" ]; do j=$(submit "$@"); [ -z "$j" ] && sleep 180; done; echo "$j"; }
latest() { t "ls -d $A/adapters/step*/ 2>/dev/null" | grep -oE '/step[0-9]+/' | grep -oE '[0-9]+' | sort -n | tail -1; }
resumable() { t "ls $A/adapters/step*/optimizer.pt 2>/dev/null" | grep -oE '/step[0-9]+/' | grep -oE '[0-9]+' | sort -n | tail -1; }

# ---------------------------------------------------------------------------------- 1. switch to overlap
if [ -n "${SWITCH_JOB:-}" ] && running "$SWITCH_JOB"; then
  from=$(resumable)
  log "waiting for job $SWITCH_JOB to save the step after $from, then switching to overlapped rollouts"
  until [ "$(resumable)" -gt "$from" ] 2>/dev/null; do sleep 60; done
  t "scancel $SWITCH_JOB"; wait_job "$SWITCH_JOB"
  log "job $SWITCH_JOB cancelled after step $(resumable)"
fi

# ---------------------------------------------------------------------------------------- 2. training
before=-1
while :; do
  [ -f "$LOCAL/STOP" ] && { log "manual stop (STOP file)"; break; }
  if t "grep -q 'AUTO-STOP' $A/events.log"; then log "AUTO-STOP: $(t "grep AUTO-STOP $A/events.log | tail -1")"; break; fi
  now=$(latest); now=${now:-0}
  [ "$now" -ge "$LAST" ] && { log "training reached step $now"; break; }
  [ "$now" -le "$before" ] && { log "ERROR: the last chunk made no progress (step $now); see $A/events.log"; exit 1; }
  before=$now
  resume=$(resumable)
  [ -z "$resume" ] && { log "ERROR: no adapter with optimizer state to resume from"; exit 1; }
  steps=$((LAST - resume)); hours=14; cap=$(( (hours * 60 - 30) / 10 )); [ $steps -gt $cap ] && steps=$cap
  log "training chunk: resume from step $resume, $steps steps"
  job=$(submit_retry --name "$RUN-from$resume" --gpus 2 --hours $hours --node node11 -- env PYTHONFAULTHANDLER=1 \
    python scripts/turing/opd_run.py --task solve --config grpo --start-step $resume --steps $steps \
    --resume-from $AN/adapters/step$resume --keep-steps $((resume + steps)) $SETS --student-port 8420 --out $AN)
  echo "$job" > "$LOCAL/train_job"
  log "training job $job"
  wait_job "$job"
  st=$(job_state "$job")
  log "training job $job ended: $st (latest step $(latest))"
  [ "$st" = "CANCELLED" ] && { log "training job cancelled by hand: stopping training"; break; }
done

# ------------------------------------------------------------------------------ 3. candidates + dev
rsync -aq "turing:$A/metrics.jsonl" "$LOCAL/train-metrics.jsonl"
rsync -aq "turing:$A/best.json" "$LOCAL/best.json" 2>/dev/null
FINAL=$(latest)
CANDS=$($PY - "$LOCAL" "$FINAL" <<'EOF'
import json, sys
from pathlib import Path
local, final = Path(sys.argv[1]), int(sys.argv[2])
rewards = [json.loads(l)["reward_mean"] for l in (local / "train-metrics.jsonl").open()]
roll = lambda k: sum(rewards[k - 8:k]) / 8 if k >= 8 else -1
cands = {final: "last"}
best = local / "best.json"
if best.exists():
    top = json.loads(best.read_text())[0]["step"]
    cands.setdefault(top, "best-by-reward")
every8 = [k for k in range(8, final + 1, 8)]
if every8:
    cands.setdefault(max(every8, key=roll), "best-every-8")
print(" ".join(f"{k}:{v}" for k, v in sorted(cands.items())))
EOF
)
log "candidates: $CANDS"
declare -A DJ=()
for c in $CANDS; do
  k=${c%%:*}; kind=${c##*:}
  src=$AN/adapters/step$k; [ "$kind" = "best-by-reward" ] && src=$AN/adapters/best-step$k
  t "test -f $N11/$RUN-dev/step$k/done" && continue
  DJ[$k]=$(submit_retry --name "dev-$RUN-$k" --gpus 1 --hours 1.5 --node node11 -- python scripts/turing/eval_matrix.py \
    --name "dev-$RUN-$k" --adapter $src --split dev --tasks solve --samples 4 --samples-tasks solve \
    --out $NODE_V3/$RUN-dev/step$k)
  echo "$src" > "$LOCAL/adapter-step$k"
  log "dev eval step $k ($kind) job ${DJ[$k]}"
done
for k in "${!DJ[@]}"; do wait_job "${DJ[$k]}"; done
rm -rf "$LOCAL/dev"; mkdir -p "$LOCAL/dev"
for c in $CANDS; do
  k=${c%%:*}
  t "test -f $N11/$RUN-dev/step$k/done" || { log "ERROR: dev eval of step $k failed"; exit 1; }
  mkdir -p "$LOCAL/dev/step$k"
  rsync -aq --include 's*/' --include 's*/scores.jsonl' --exclude '*' "turing:$N11/$RUN-dev/step$k/" "$LOCAL/dev/step$k/"
done
$PY scripts/select_solve_step.py "$LOCAL/dev" "$BASE_DEV" | tee "$LOCAL/selection.txt"
SEL=$($PY -c "import json; print(json.load(open('$LOCAL/dev/selection.json'))['selected_step'])")
SRC=$(cat "$LOCAL/adapter-step$SEL" 2>/dev/null || echo "$AN/adapters/step$SEL")
log "selected step $SEL ($SRC)"

# ------------------------------------------------------------------------------------------ 4. test
if ! t "test -f $N11/$RUN-test-step$SEL/done"; then
  TJ=$(submit_retry --name "test-$RUN-$SEL" --gpus 2 --hours 5 --node node11 -- python scripts/turing/eval_matrix.py \
    --name "test-$RUN-$SEL" --adapter $SRC --split test --samples 4 --samples-tasks solve --out $NODE_V3/$RUN-test-step$SEL)
  log "test eval job $TJ"; wait_job "$TJ"
fi
t "test -f $N11/$RUN-test-step$SEL/done" || { log "ERROR: test eval failed"; exit 1; }

# -------------------------------------------------------------------------------------- 5. 27B judge
if ! t "test -s $N11/$RUN-test-step$SEL/s0/judgments.qwen.jsonl"; then
  J=$(submit_retry --name "judge27b-$RUN" --gpus 2 --hours 4 --node node11 -- python scripts/turing/qwen_judge_run.py \
    --out $NODE_V3/$RUN-judge27b/answers.jsonl --eval-dir test:$NODE_V3/$RUN-test-step$SEL/s0)
  log "27B judging job $J"; wait_job "$J"
fi

# ---------------------------------------------------------------------------------------- 6. report
d=$OUT/v3-grpo-lr1e-5-solve-step$SEL
mkdir -p "$d"
rsync -aq --include 's*/' --include 's*/*.jsonl' --include 's*/*.json' --include 'metadata.json' --exclude '*' \
  "turing:$N11/$RUN-test-step$SEL/" "$d/"
$PY scripts/qwen_judge_calibration.py score "$d/s0"
SOLVE_SEL=$SEL $PY scripts/report_grpo_matrix.py | tail -20
log "pipeline finished"
