#!/bin/bash
# B3 (phase2/next/transplant3.py): composite vs plain adapters on hard ProcessBench, own attempts, SOLVE test. 2 GPUs.
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
OUT=phase2/runs/transplant3; HY=/scratch/$USER/phase2/hybrids2; mkdir -p $OUT
[ -d $HY/judge ] || cp -r /scratch/$USER/phase2/hybrids/judge $HY/judge
T="python phase2/next/transplant3.py"
GPUS=(${CUDA_VISIBLE_DEVICES//,/ })
CUDA_VISIBLE_DEVICES=${GPUS[0]} $T run --hybrids $HY --out $OUT --base $BASE --names solve+J0-5,solve > $OUT/run-0.log 2>&1 &
A=$!
CUDA_VISIBLE_DEVICES=${GPUS[1]} $T run --hybrids $HY --out $OUT --base $BASE --names mixed,judge > $OUT/run-1.log 2>&1 &
B=$!
wait $A; wait $B
$T report --out $OUT
echo "end $(date -u +%FT%TZ)"
