#!/bin/bash
# Answer selection (phase2/next/select.py): dev on one GPU, test on the other. 2 GPUs via the ledger.
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --output=phase2/runs/slurm-%x-%j.out
set -euo pipefail
source phase2/next/env.sh
OUT=phase2/runs/select; mkdir -p $OUT
S="python phase2/next/select.py"
GPUS=(${CUDA_VISIBLE_DEVICES//,/ })
CUDA_VISIBLE_DEVICES=${GPUS[0]} $S run --split dev --out $OUT --base $BASE > $OUT/dev.log 2>&1 &
A=$!
CUDA_VISIBLE_DEVICES=${GPUS[1]} $S run --split test --out $OUT --base $BASE > $OUT/test.log 2>&1 &
B=$!
wait $A; wait $B
$S report --out $OUT
echo "end $(date -u +%FT%TZ)"
