#!/bin/bash
# B: layer transplants (phase2/next/transplant.py). Submit through phase2/budget/ledger.py with 2 GPUs.
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodelist=node07
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --output=phase2/runs/slurm-%x-%j.out
set -euo pipefail
source phase2/next/env.sh
OUT=phase2/runs/transplant; HY=/scratch/$USER/phase2/hybrids; mkdir -p $OUT
T="python phase2/next/transplant.py"
[ -f $OUT/items.jsonl ] || python phase2/scripts/processbench_eval.py prepare --pb-dir phase2/data/processbench --out $OUT
$T build --hybrids $HY
GPUS=(${CUDA_VISIBLE_DEVICES//,/ })
CUDA_VISIBLE_DEVICES=${GPUS[0]} $T run --hybrids $HY --out $OUT --base $BASE --names solve,solve+J0-5,solve+J6-11,solve+J12-17 > $OUT/run-0.log 2>&1 &
A=$!
CUDA_VISIBLE_DEVICES=${GPUS[1]} $T run --hybrids $HY --out $OUT --base $BASE --names judge,mixed,solve+J18-23 > $OUT/run-1.log 2>&1 &
B=$!
wait $A; wait $B
$T report --out $OUT
echo "end $(date -u +%FT%TZ)"
