#!/bin/bash
# Error-feature scoring (phase2/next/errfeat.py). Submit through phase2/budget/ledger.py with 1 GPU.
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
python phase2/next/errfeat.py steps --acts /scratch/$USER/phase2/crosscoder-acts --out /scratch/$USER/phase2/errfeat \
  --base $BASE --sources ${SOURCES:-pb-easy,pb-hard,own-free,own-step,base-step,9b-step,condensed}
echo "end $(date -u +%FT%TZ)"
