#!/bin/bash
# End-to-end mixed-task Dr. GRPO (docs/plans/2026-10-08-mixed-task-grpo-plan.md), run from the workstation:
#   equal thirds SOLVE / JUDGE / RECONSTRUCT (3 x 1,134 = 3,402 questions, every batch 10/10/10), lr 2e-5,
#   30 questions x 8 answers, overlapped rollouts, 16k cap, one pass = 113 steps.
# Never more than 4 Turing GPUs at once (launch.py enforces it).
#
#   NODE=node07 nohup bash scripts/mixed_grpo_pipeline.sh > artifacts/opd/evals/mixed-pipeline.log 2>&1 &
#
# 1. Training in <=14 h chunks, each resuming from the newest adapter with optimizer state.
#    Early stopping on the training reward (user, 2026-10-08): every 8 steps the combined rolling reward (mean over
#    tasks of each task's 8-step rolling reward minus its steps 1-8 average) is checked; after 3 checks in a row
#    without beating the best by 0.005 the training job is cancelled. Manual stop: scancel the job in <local>/train_job.
# 2. Candidates: the best adapter by the combined rolling reward, the best every-8 adapter by it, the last step.
#    Dev evals on all three dev slices (SOLVE 4 samples), two candidates at a time (2 GPUs each).
# 3. Selection: best mean dev Δ over SOLVE accuracy, JUDGE Youden J, RECONSTRUCT Jev score
#    (scripts/select_checkpoint_mixed.py). 4. Test evals on all three tasks. 5. Qwen3.8-27B judging.
# 6. Local calibration and the transfer-matrix report (row "Mixed").
set -o pipefail
cd "$(dirname "$0")/.."
RUN=${RUN:-mixed-lr2e-5}
NODE=${NODE:-node07}
LAST=${LAST:-113}
PATIENCE=${PATIENCE:-3}
MIN_DELTA=${MIN_DELTA:-0.005}
SETS="--set prompts_per_step=30 --set optimizer.lr=2e-5 --set optimizer.warmup_steps=5 --set async_rollouts=true --set best_window=8 --set best_keep=3"
NV=/scratch/$NODE/mukund.hebbar/anlp-opd/v3            # login-node view of the node's scratch (read-only)
NODE_V3=/scratch/mukund.hebbar/anlp-opd/v3             # the node's own view
A=$NV/$RUN
AN=$NODE_V3/$RUN
OUT=artifacts/baselines/final-v3/test
LOCAL=artifacts/opd/evals/$RUN
BASE_DEV=artifacts/opd/evals/v3-pass4-2b-dev
PY=.venv/bin/python
mkdir -p "$LOCAL"
log() { echo "$(date '+%F %H:%M') $*"; }
t() { ssh -o ConnectTimeout=30 -o ServerAliveInterval=30 turing "$@"; }
submit() {
  t "cd ~/anlp-project && python3 scripts/turing/launch.py submit $*" 2>&1 | tee -a "$LOCAL/submits.log" \
    | grep -oE '"job_id": [0-9]+' | grep -oE '[0-9]+'
}
running() { local out; out=$(t "squeue -h -j $1 -o %T" 2>/dev/null) || return 0; [ -n "$out" ]; }
job_state() { t "sacct -j $1 -X -n -o State" | head -1 | awk '{print $1}'; }
submit_retry() { local j=""; while [ -z "$j" ]; do j=$(submit "$@"); [ -z "$j" ] && sleep 180; done; echo "$j"; }
latest() { t "ls -d $A/adapters/step*/ 2>/dev/null" | grep -oE '/step[0-9]+/' | grep -oE '[0-9]+' | sort -n | tail -1; }
resumable() { t "ls $A/adapters/step*/optimizer.pt 2>/dev/null" | grep -oE '/step[0-9]+/' | grep -oE '[0-9]+' | sort -n | tail -1; }
plateau() {  # prints "stop <reason>" when the combined rolling reward has not improved for PATIENCE 8-step checks
  rsync -aq "turing:$A/metrics.jsonl" "$LOCAL/train-metrics.jsonl" 2>/dev/null || return 0
  $PY - "$LOCAL/train-metrics.jsonl" "$PATIENCE" "$MIN_DELTA" <<'EOF'
import json, sys
sys.path.insert(0, "src")
from anlp_project.opd_train import rolling_score
recs = [json.loads(l) for l in open(sys.argv[1])]
patience, min_delta = int(sys.argv[2]), float(sys.argv[3])
checks = [(k, rolling_score(recs[:k], 8)) for k in range(16, len(recs) + 1, 8)]
best, since = None, 0
for k, s in checks:
    if best is None or s > best + min_delta:
        best, since = s, 0
    else:
        since += 1
print(" ".join(f"{k}:{s:+.3f}" for k, s in checks))
if since >= patience:
    print(f"stop: no gain over {best:+.3f} for {since} checks (last step {checks[-1][0]})")
EOF
}

# ---------------------------------------------------------------------------------------- 1. training
before=-1
while :; do
  [ -f "$LOCAL/STOP" ] && { log "manual stop (STOP file)"; break; }
  if t "grep -q 'AUTO-STOP' $A/events.log 2>/dev/null"; then log "AUTO-STOP: $(t "grep AUTO-STOP $A/events.log | tail -1")"; break; fi
  now=$(latest); now=${now:-0}
  [ "$now" -ge "$LAST" ] && { log "training reached step $now"; break; }
  [ "$now" -le "$before" ] && [ "$before" -ge 0 ] && { log "ERROR: the last chunk made no progress (step $now)"; exit 1; }
  before=$now
  resume=$(resumable)
  hours=14; cap=$(( (hours * 60 - 30) / 9 ))
  if [ -z "$resume" ]; then
    steps=$LAST; [ $steps -gt $cap ] && steps=$cap
    log "training chunk: fresh start, $steps steps"
    from=""
  else
    steps=$((LAST - resume)); [ $steps -gt $cap ] && steps=$cap
    log "training chunk: resume from step $resume, $steps steps"
    from="--start-step $resume --resume-from $AN/adapters/step$resume"
  fi
  job=$(submit_retry --name "$RUN-from${resume:-0}" --gpus 2 --hours $hours --node $NODE -- env PYTHONFAULTHANDLER=1 \
    python scripts/turing/opd_run.py --task mixed --config grpo $from --steps $steps \
    --keep-steps $(( ${resume:-0} + steps )) $SETS --student-port 8470 --out $AN)
  echo "$job" > "$LOCAL/train_job"; log "training job $job"
  stopped=0
  while running "$job"; do
    p=$(plateau)
    if echo "$p" | grep -q '^stop'; then
      log "EARLY STOP on training reward: $(echo "$p" | tail -1)"; log "checks: $(echo "$p" | head -1)"
      t "scancel $job"; stopped=1; break
    fi
    sleep 300
  done
  [ $stopped = 1 ] && { while running "$job"; do sleep 30; done; break; }
  st=$(job_state "$job"); log "training job $job ended: $st (latest step $(latest))"
  [ "$st" = "CANCELLED" ] && { log "training job cancelled by hand: stopping training"; break; }
done
plateau | head -1 | sed 's/^/combined rolling reward at 8-step checks: /'

# --------------------------------------------------------------------------------- 2. candidates + dev
rsync -aq "turing:$A/metrics.jsonl" "$LOCAL/train-metrics.jsonl"
rsync -aq "turing:$A/best.json" "$LOCAL/best.json" 2>/dev/null
FINAL=$(latest)
CANDS=$($PY - "$LOCAL" "$FINAL" <<'EOF'
import json, sys
from pathlib import Path
sys.path.insert(0, "src")
from anlp_project.opd_train import rolling_score
local, final = Path(sys.argv[1]), int(sys.argv[2])
recs = [json.loads(l) for l in (local / "train-metrics.jsonl").open()]
cands = {final: "last"}
best = local / "best.json"
if best.exists():
    cands.setdefault(json.loads(best.read_text())[0]["step"], "best-by-reward")
every8 = [k for k in range(16, final + 1, 8)]
if every8:
    cands.setdefault(max(every8, key=lambda k: rolling_score(recs[:k], 8)), "best-every-8")
print(" ".join(f"{k}:{v}" for k, v in sorted(cands.items())))
EOF
)
log "candidates: $CANDS"
declare -A DJ=()
for c in $CANDS; do
  k=${c%%:*}; kind=${c##*:}
  src=$AN/adapters/step$k; [ "$kind" = "best-by-reward" ] && src=$AN/adapters/best-step$k
  echo "$src" > "$LOCAL/adapter-step$k"
  t "test -f $NV/$RUN-dev/step$k/done" && continue
  DJ[$k]=$(submit_retry --name "dev-$RUN-$k" --gpus 2 --hours 2 --node $NODE -- python scripts/turing/eval_matrix.py \
    --name "dev-$RUN-$k" --adapter $src --split dev --samples 4 --samples-tasks solve --out $NODE_V3/$RUN-dev/step$k)
  log "dev eval step $k ($kind) job ${DJ[$k]}"
done
for k in "${!DJ[@]}"; do while running "${DJ[$k]}"; do sleep 120; done; done
rm -rf "$LOCAL/dev"; mkdir -p "$LOCAL/dev"
for c in $CANDS; do
  k=${c%%:*}
  t "test -f $NV/$RUN-dev/step$k/done" || { log "ERROR: dev eval of step $k failed"; exit 1; }
  mkdir -p "$LOCAL/dev/step$k"
  rsync -aq --include 's*/' --include 's*/*.jsonl' --include 's*/*.json' --include 'metadata.json' --exclude '*' \
    "turing:$NV/$RUN-dev/step$k/" "$LOCAL/dev/step$k/"
done
$PY scripts/select_checkpoint_mixed.py "$LOCAL/dev" "$BASE_DEV" | tee "$LOCAL/selection.txt" || exit 1
SEL=$($PY -c "import json; print(json.load(open('$LOCAL/dev/selection.json'))['selected_step'])")
SRC=$(cat "$LOCAL/adapter-step$SEL")
log "selected step $SEL ($SRC)"

# -------------------------------------------------------------------------------------------- 3. test
if ! t "test -f $NV/$RUN-test-step$SEL/done"; then
  TJ=$(submit_retry --name "test-$RUN-$SEL" --gpus 3 --hours 5 --node $NODE -- python scripts/turing/eval_matrix.py \
    --name "test-$RUN-$SEL" --adapter $SRC --split test --samples 4 --samples-tasks solve --out $NODE_V3/$RUN-test-step$SEL)
  log "test eval job $TJ"; while running "$TJ"; do sleep 120; done
fi
t "test -f $NV/$RUN-test-step$SEL/done" || { log "ERROR: test eval failed"; exit 1; }

# ---------------------------------------------------------------------------------------- 4. 27B judge
if ! t "test -s $NV/$RUN-test-step$SEL/s0/judgments.qwen.jsonl"; then
  J=$(submit_retry --name "judge27b-$RUN" --gpus 2 --hours 4 --node $NODE -- python scripts/turing/qwen_judge_run.py \
    --out $NODE_V3/$RUN-judge27b/answers.jsonl --eval-dir test:$NODE_V3/$RUN-test-step$SEL/s0)
  log "27B judging job $J"; while running "$J"; do sleep 120; done
fi

# ------------------------------------------------------------------------------------------ 5. report
d=$OUT/v3-grpo-mixed-lr2e-5-step$SEL
mkdir -p "$d"
rsync -aq --include 's*/' --include 's*/*.jsonl' --include 's*/*.json' --include 'metadata.json' --exclude '*' \
  "turing:$NV/$RUN-test-step$SEL/" "$d/"
$PY scripts/qwen_judge_calibration.py score "$d/s0"
SOLVE_SEL=66 MIXED_SEL=$SEL $PY scripts/report_grpo_matrix.py | tail -25
log "pipeline finished"
