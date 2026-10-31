#!/bin/bash
# Evaluate the trained self-judge checkpoints and the untrained mixed judge on the mixed model's own dev attempts.
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=phase2/runs/slurm-%x-%j.out
set -euo pipefail
source phase2/next/env.sh
python -c "import torch; torch.ones(1, device=\"cuda\").sum().item()" || { echo "GPU unhealthy"; exit 1; }  # node14 GPU 3 has an ECC fault
A=phase2/runs/selfjudge/adapters
L=mixed=$HOME/anlp-final-adapters/mixed-step75
for s in ${STEPS:-16 32}; do [ -d $A/step$s ] && L=$L,sj-step$s=$PWD/$A/step$s; done
python phase2/selfjudge/evaluate.py run --split ${SPLIT:-dev} --base $BASE --adapters $L
python phase2/selfjudge/evaluate.py report --split ${SPLIT:-dev}
echo "end $(date -u +%FT%TZ)"
