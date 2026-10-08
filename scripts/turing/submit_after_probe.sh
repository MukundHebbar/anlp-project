#!/bin/bash
# After the SOLVE probe: start JUDGE and RECONSTRUCT OPD on one shared teacher (node11), at the chosen cap.
#
#   CAP=4096 bash scripts/turing/submit_after_probe.sh          # 4k passed: SOLVE keeps running
#   CAP=8192 bash scripts/turing/submit_after_probe.sh          # 4k failed: also re-run SOLVE at 8k
#
# Run on the login node from ~/anlp-project. The SFT warm-ups for the chosen cap must exist or be queued
# (their job ids go in AFTER, e.g. AFTER=41247:41248).
set -euo pipefail
cd "$(dirname "$0")/../.."
CAP=${CAP:?set CAP to 4096 or 8192}
STEPS=${STEPS:-156}
KEEP=${KEEP:-16,52,104}
AFTER=${AFTER:-}
TAG=$([ "$CAP" = 4096 ] && echo 4k || echo 8k)
OUT=$PWD/runs-out
L="python3 scripts/turing/launch.py submit"
SET="--cap $CAP"
DEP=$([ -n "$AFTER" ] && echo "--after $AFTER" || true)

if [ "$CAP" = 8192 ]; then
  $L --name opd-solve-matrix-8k --gpus 3 --hours 14 --node node07 --after "${SOLVE_SFT:?set SOLVE_SFT job id}" -- \
    python scripts/turing/opd_run.py --task solve --config matrix --steps "$STEPS" --keep-steps "$KEEP" $SET \
    --init-adapter "$OUT/sft-solve-8k/adapter" --out {out}
fi
$L --name "opd-judge-reconstruct-matrix-$TAG" --gpus 4 --hours 14 --node node11 $DEP -- python scripts/turing/opd_shared.py \
  --teacher-gpus 2,3 --cap "$CAP" --log-dir {out} \
  --run "0|{out}/opd-judge-matrix|--task judge --config matrix --steps $STEPS --keep-steps $KEEP $SET --init-adapter $OUT/sft-judge-$TAG/adapter" \
  --run "1|{out}/opd-reconstruct-matrix|--task reconstruct --config matrix --steps $STEPS --keep-steps $KEEP $SET --init-adapter $OUT/sft-reconstruct-$TAG/adapter"
