#!/bin/bash
# Inside a job on a node other than node07: copy what the experiment needs from node07's scratch, read through the
# login node's read-only /scratch/node07 mount over SSH. rsync only sends what is missing, so later jobs on the
# same node are quick. Copies (read-only use of Yashas's files; nothing is written on node07):
#   Yashas's venv and the Qwen3.5-2B / Qwen3.8-27B HF folders -> /scratch/$USER/yashas-anlp-env (see env.sh)
#   our round-1 step-8 adapter (the arms' shared start)        -> /scratch/$USER/failure-driven/runs/r1/adapters/step8
set -euo pipefail
LOGIN=mukund.hebbar@turing.iiit.ac.in
SRC=/scratch/node07
DST=/scratch/$USER/yashas-anlp-env
R=/scratch/$USER/failure-driven/runs
mkdir -p $DST/hf_cache/hub $R/r1/adapters
SSH="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
t0=$(date +%s)
rsync -a -e "$SSH" $LOGIN:$SRC/yashas.kotre/anlp-env/venv $DST/
for m in Qwen--Qwen3.5-2B Qwen--Qwen3.8-27B; do
  # -L: his weight files are links into a shared store (hub/blobs/..), so copy the files they point to.
  # trees/ is the hub's file-listing cache: not needed to load the weights, and one of its files is unreadable.
  find $DST/hf_cache -xtype l -delete 2>/dev/null || true  # links left by an earlier copy without -L
  rsync -aL --exclude trees/ -e "$SSH" $LOGIN:$SRC/yashas.kotre/anlp-env/hf_cache/hub/models--$m $DST/hf_cache/hub/
done
rsync -a -e "$SSH" $LOGIN:$SRC/mukund.hebbar/failure-driven/runs/r1/adapters/step8 $R/r1/adapters/
echo "mirror done in $(( $(date +%s) - t0 )) s: $(du -sh $DST | cut -f1) env+models, adapter $(du -sh $R/r1/adapters/step8 | cut -f1)"
