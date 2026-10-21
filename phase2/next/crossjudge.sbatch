#!/bin/bash
# C: own vs others' attempts (phase2/next/crossjudge.py). Submit through phase2/budget/ledger.py with 2 GPUs.
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
BIG9=$(ls -d $ENVROOT/hf_cache/hub/models--Qwen--Qwen3.5-9B/snapshots/*/ | head -1)
OUT=phase2/runs/crossjudge; mkdir -p $OUT
C="python phase2/next/crossjudge.py"
GPUS=(${CUDA_VISIBLE_DEVICES//,/ })
( export CUDA_VISIBLE_DEVICES=${GPUS[0]}
  $C gen --source base --out $OUT --model $BASE && $C judge --source base --out $OUT --base $BASE ) > $OUT/gpu0.log 2>&1 &
A=$!
( export CUDA_VISIBLE_DEVICES=${GPUS[1]}
  $C gen --source 9b --out $OUT --model $BIG9 && $C condense --out $OUT --model $BIG9 && \
  $C judge --source 9b --out $OUT --base $BASE && $C judge --source condensed --out $OUT --base $BASE ) > $OUT/gpu1.log 2>&1 &
B=$!
wait $A; wait $B
$C report --out $OUT
echo "end $(date -u +%FT%TZ)"
