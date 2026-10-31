#!/bin/bash
# CPU-only analysis of the error-feature scores.
#SBATCH --job-name=p2b-efanalyze
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
python phase2/next/errfeat_analyze.py --feats /scratch/$USER/phase2/errfeat --out phase2/runs/errfeat
