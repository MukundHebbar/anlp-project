#!/bin/bash
# Direction 3 pilot (phase2/next/stepformat.py). Submit through phase2/budget/ledger.py (sets --gres and --time).
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
OUT=${OUT:-phase2/runs/stepformat}
mkdir -p $OUT
GPUS=(${CUDA_VISIBLE_DEVICES//,/ }); pids=()
for i in "${!GPUS[@]}"; do
  CUDA_VISIBLE_DEVICES=${GPUS[$i]} python phase2/next/stepformat.py run --out $OUT --base $BASE --shard $i \
    --nshards ${#GPUS[@]} > $OUT.log-$i 2>&1 & pids+=($!)
done
mkdir -p $OUT; for p in "${pids[@]}"; do wait $p; done
python phase2/next/stepformat.py report --out $OUT
echo "end $(date -u +%FT%TZ)"
