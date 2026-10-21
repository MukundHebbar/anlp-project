#!/bin/bash
# B3: SOLVE test set only, for the plain SOLVE and JUDGE adapters (one GPU each). 2 GPUs via the ledger.
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --output=phase2/runs/slurm-%x-%j.out
set -euo pipefail
source phase2/next/env.sh
OUT=phase2/runs/transplant3; HY=/scratch/$USER/phase2/hybrids2; mkdir -p $OUT
python phase2/next/transplant.py build --hybrids $HY --names judge,solve
T="python phase2/next/transplant3.py"
GPUS=(${CUDA_VISIBLE_DEVICES//,/ })
CUDA_VISIBLE_DEVICES=${GPUS[0]} $T run --hybrids $HY --out $OUT --base $BASE --names solve --parts test > $OUT/run-c0.log 2>&1 &
A=$!
CUDA_VISIBLE_DEVICES=${GPUS[1]} $T run --hybrids $HY --out $OUT --base $BASE --names judge --parts test > $OUT/run-c1.log 2>&1 &
B=$!
wait $A; wait $B
echo "end $(date -u +%FT%TZ)"
