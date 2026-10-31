#!/bin/bash
# Self-judge data: the mixed model's attempts on 1,200 unseen train questions, one shard per GPU, then build.
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=160G
#SBATCH --output=phase2/runs/slurm-%x-%j.out
set -euo pipefail
source phase2/next/env.sh
OUT=phase2/runs/selfjudge; mkdir -p $OUT
GPUS=(${CUDA_VISIBLE_DEVICES//,/ }); pids=()
for i in "${!GPUS[@]}"; do
  [ -f $OUT/attempts-shard$i.jsonl ] && continue
  CUDA_VISIBLE_DEVICES=${GPUS[$i]} python phase2/selfjudge/build.py gen --out $OUT --base $BASE --n 1200 --shard $i \
    --nshards ${#GPUS[@]} > $OUT/gen-$i.log 2>&1 & pids+=($!)
done
for p in "${pids[@]}"; do wait $p; done
python phase2/selfjudge/build.py build --out $OUT --steps 48 --per-step 32
echo "end $(date -u +%FT%TZ)"
