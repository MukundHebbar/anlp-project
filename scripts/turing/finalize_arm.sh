#!/bin/bash
# Wait until an OPD run logs a step, stop it, keep a home copy of that adapter, and submit its test evaluation.
#
#   bash scripts/turing/finalize_arm.sh <run name> <task> <node> <job id> [step]      (run on the laptop)
#
# The run's adapters live on <node>'s scratch; the evaluation runs on the same node so it can read them,
# (or on EVAL_NODE, since the copy is in home), and the adapter is copied to ~/anlp-project/runs-out/<run>/final-step<step> for later use.
set -euo pipefail
RUN=$1; TASK=$2; NODE=$3; JOB=$4; STEP=${5:-104}; EVAL_NODE=${EVAL_NODE:-$NODE}
until ssh turing "grep -q '^.\{8\} step $STEP:' ~/anlp-project/runs-out/$RUN/events.log"; do sleep 60; done
ssh turing "scancel $JOB; sleep 20; srun -A priyesh.shukla -p u22 -w $NODE -n1 -c1 --mem=2G -t 00:10:00 \
  cp -rL ~/anlp-project/runs-out/$RUN/adapters/step$STEP ~/anlp-project/runs-out/$RUN/final-step$STEP 2>&1 | grep -v '^srun' || true; \
  rm -f ~/anlp-project/runs-out/$RUN/final-step$STEP/optimizer.pt; \
  cd ~/anlp-project && python3 scripts/turing/launch.py submit --name eval-test-opd-$TASK-s$STEP --gpus 1 --hours 3 --node $EVAL_NODE -- \
  python scripts/turing/eval_matrix.py --name opd-$TASK-s$STEP --adapter ~/anlp-project/runs-out/$RUN/final-step$STEP --out {out}"
echo "finalized $RUN at step $STEP"
