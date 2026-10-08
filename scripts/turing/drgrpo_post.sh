#!/bin/bash
# Post-training chain for one Dr. GRPO arm, on the arm's own 2 GPUs (submitted with --after <training job>):
#   1. dev evaluation of steps 26, 52, 78, 104 on the arm's OWN task (two at a time; SOLVE 4 samples, others 1)
#   2. checkpoint selection by the fixed rule (scripts/select_dev_checkpoint.py; Jev for RECONSTRUCT only)
#   3. test evaluation of the selected step, and of step 104 if different (all three test sets;
#      SOLVE 4 samples, JUDGE and RECONSTRUCT 1)
#   4. Qwen3.8-27B judging of the JUDGE and RECONSTRUCT test answers (sample 0) on both GPUs
#
#   bash scripts/turing/drgrpo_post.sh <solve|judge|reconstruct> [run name, default v3-drgrpo-<task>]
# Outputs: $V3_ROOT/v3-drgrpo-<task>/post/{dev,test-step<k>,judge} on node-local scratch (the home directory
# filled up on 2026-10-06: 104-step adapters do not fit there). A failed step stops the chain.
set -euo pipefail
T=$1
cd "$(dirname "$0")/../.."
V3_ROOT=${V3_ROOT:-/scratch/mukund.hebbar/anlp-opd/v3}
R=$V3_ROOT/${2:-v3-drgrpo-$T}
P=$R/post
mkdir -p "$P/dev" "$P/judge"
IFS=, read -r G0 G1 _ <<< "${CUDA_VISIBLE_DEVICES:?no GPUs visible}"  # this job's two GPUs, as Slurm numbers them
for k in 26 52 78 104; do
  test -d "$R/adapters/step$k" || { echo "missing adapter $R/adapters/step$k" >&2; exit 1; }
done

dev() {  # dev() <step> <gpu>
  [ -f "$P/dev/$T-step$1/done" ] && return 0
  CUDA_VISIBLE_DEVICES=$2 python scripts/turing/eval_matrix.py --name "drgrpo-$T-dev-step$1" \
    --adapter "$R/adapters/step$1" --split dev --tasks "$T" --samples 4 --samples-tasks solve \
    --out "$P/dev/$T-step$1" > "$P/dev/$T-step$1.log" 2>&1
}
echo "$(date -u +%FT%TZ) dev evaluation"
(dev 26 "$G0" & dev 52 "$G1" & wait) && (dev 78 "$G0" & dev 104 "$G1" & wait)
for k in 26 52 78 104; do test -f "$P/dev/$T-step$k/done" || { echo "dev step $k failed" >&2; exit 1; }; done

echo "$(date -u +%FT%TZ) selection"
python scripts/select_dev_checkpoint.py "$P/dev" | tee "$P/select.log"
SEL=$(python -c "import json; print(json.load(open('$P/dev/selection.json'))['$T']['selected_step'])")
STEPS="$SEL"; [ "$SEL" != "104" ] && STEPS="$SEL 104"
echo "selected step $SEL; testing: $STEPS"

for k in $STEPS; do
  echo "$(date -u +%FT%TZ) test evaluation, step $k"
  [ -f "$P/test-step$k/done" ] || CUDA_VISIBLE_DEVICES=$G0,$G1 python scripts/turing/eval_matrix.py \
    --name "drgrpo-$T-test-step$k" --adapter "$R/adapters/step$k" --split test --samples 4 \
    --samples-tasks solve --out "$P/test-step$k" > "$P/test-step$k.log" 2>&1
done

echo "$(date -u +%FT%TZ) 27B judging"
HF_HUB_OFFLINE=0 python -c "from huggingface_hub import snapshot_download as s; s('Qwen/Qwen3.8-27B')" > /dev/null
ARGS=""
for k in $STEPS; do ARGS="$ARGS --eval-dir test:$P/test-step$k/s0"; done
CUDA_VISIBLE_DEVICES=$G0,$G1 python scripts/turing/qwen_judge_run.py --out "$P/judge/answers.jsonl" $ARGS > "$P/judge.log" 2>&1
echo "$(date -u +%FT%TZ) done"
touch "$P/done"
