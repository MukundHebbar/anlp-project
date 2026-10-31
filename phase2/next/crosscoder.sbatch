#!/bin/bash
# Direction 4 pilot (phase2/next/crosscoder.py). Submit through phase2/budget/ledger.py (sets --gres and --time).
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodelist=node07
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --output=phase2/runs/slurm-%x-%j.out
set -euo pipefail
source phase2/next/env.sh
OUT=${OUT:-phase2/runs/crosscoder}
python phase2/next/crosscoder.py ${STAGE:-all} --out $OUT --acts /scratch/$USER/phase2/crosscoder-acts --base $BASE \
  --pb-dir phase2/data/processbench
echo "end $(date -u +%FT%TZ)"
