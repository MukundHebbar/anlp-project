#!/bin/bash
# B2: finer transplants, the reverse transplant and other donors (phase2/next/transplant.py). 1 GPU via the ledger.
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodelist=node07
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=phase2/runs/slurm-%x-%j.out
set -euo pipefail
source phase2/next/env.sh
OUT=phase2/runs/transplant2; HY=/scratch/$USER/phase2/hybrids2; mkdir -p $OUT
T="python phase2/next/transplant.py"
cp phase2/runs/transplant/items.jsonl $OUT/items.jsonl
NAMES=${NAMES:-solve,solve+J0-5,mixed,judge+S0-5,solve+M0-5,solve+R0-5,solve+J0-11,solve+J0-2,solve+J3-5,solve+J0-0,solve+J1-1,solve+J2-2,solve+J3-3,solve+J4-4,solve+J5-5,solve+Z0-5,solve+X0-5}
EXTRA=${EXTRA:-}; EXTRA=${EXTRA//:/,}; NAMES=${NAMES},${EXTRA}; NAMES=${NAMES%,}
$T build --hybrids $HY --names $NAMES
REST1=${REST1:-solve+J0-2,solve+J3-5,solve+J0-0,solve+J1-1,solve+J2-2}; REST1=${REST1//:/,}
REST2=${REST2:-solve+J3-3,solve+J4-4,solve+J5-5,solve+Z0-5,solve+X0-5}; REST2=${REST2//:/,}
GPUS=(${CUDA_VISIBLE_DEVICES//,/ })
if [ ${#GPUS[@]} -ge 2 ] && [ -f $OUT/solve-mixed.jsonl ]; then  # resume: SOLVE evaluations done, judge-only remain
  CUDA_VISIBLE_DEVICES=${GPUS[0]} $T run --hybrids $HY --out $OUT --base $BASE --names $REST1 > $OUT/run-a.log 2>&1 &
  A=$!
  CUDA_VISIBLE_DEVICES=${GPUS[1]} $T run --hybrids $HY --out $OUT --base $BASE --names $REST2 > $OUT/run-b.log 2>&1 &
  B=$!
  wait $A; wait $B
else
  $T run --hybrids $HY --out $OUT --base $BASE --names $NAMES --solve-names solve,solve+J0-5,mixed,judge+S0-5,solve+M0-5 \
    --solve-samples 4
fi
$T report --out $OUT
echo "end $(date -u +%FT%TZ)"
