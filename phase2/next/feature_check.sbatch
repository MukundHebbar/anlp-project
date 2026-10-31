#!/bin/bash
# CPU-only confound check for the crosscoder error features (2 CPUs: no GPU billing).
#SBATCH --job-name=p2b-featcheck
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodelist=node07
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --output=phase2/runs/slurm-%x-%j.out
set -euo pipefail
source phase2/next/env.sh
export OMP_NUM_THREADS=2
python phase2/next/feature_check.py --acts /scratch/$USER/phase2/crosscoder-acts --summary phase2/runs/crosscoder2/summary.json \
  --out phase2/runs/feature_check
echo "end $(date -u +%FT%TZ)"
