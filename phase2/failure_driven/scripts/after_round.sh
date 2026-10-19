#!/bin/bash
# Local, after a training round: pull its rollouts, build the failure buffer, convert it (DeepSeek), build arm B's
# next prompt list, and push that list to the Turing repo copy. No GPU.
#   [NODE=node06] bash phase2/failure_driven/scripts/after_round.sh <run: r1|armB> <steps: 1-8|9-16> <next arm-B round: 2|3> [keep.json]
set -euo pipefail
RUN=$1 STEPS=$2 NEXT=$3 KEEP=${4:-}
HOST=mukund.hebbar@turing.iiit.ac.in
W=local/failure-driven
lo=${STEPS%-*} hi=${STEPS#*-}
mkdir -p $W/$RUN/rollouts
for s in $(seq $lo $hi); do echo step$s.jsonl; done > $W/$RUN/rollouts/.list
rsync -a --files-from=$W/$RUN/rollouts/.list -e "ssh -o BatchMode=yes" \
  $HOST:/scratch/${NODE:-node07}/mukund.hebbar/failure-driven/runs/$RUN/rollouts/ $W/$RUN/rollouts/
B=$W/buffer-$RUN-$STEPS
.venv/bin/python phase2/failure_driven/fd.py buffer --rollouts $W/$RUN/rollouts --steps $STEPS --max-correct 1 --out $B
.venv/bin/python phase2/failure_driven/fd.py convert --buffer $B/buffer.json --out $B
ITEMS=$B
[ "$NEXT" = 3 ] && ITEMS=$W/buffer-r1-1-8,$B  # round 3: still-unsolved round-1 questions (KEEP) + new failures
.venv/bin/python phase2/failure_driven/fd.py prompts --round $NEXT --items $ITEMS ${KEEP:+--keep $KEEP} \
  --out phase2/failure_driven/data/armB
rsync -aR -e "ssh -o BatchMode=yes" phase2/failure_driven/data/armB $HOST:anlp-project-grpo/
