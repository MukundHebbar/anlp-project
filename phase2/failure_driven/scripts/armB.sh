#!/bin/bash
# Arm B, one round, in one 4-GPU job on any L40S node: mirror node07's environment, weights and the step-8 adapter
# if needed (mirror_node07.sh; skipped on node07), then run_armB.py.
#   bash phase2/failure_driven/scripts/armB.sh 2      # round 2 = steps 9-16; then 3 = steps 17-24
set -euo pipefail
[ -d /scratch/yashas.kotre/anlp-env/venv ] || bash phase2/failure_driven/scripts/mirror_node07.sh
bash phase2/failure_driven/scripts/env.sh python phase2/failure_driven/run_armB.py --round "$1"
