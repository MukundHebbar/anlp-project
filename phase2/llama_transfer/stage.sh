#!/bin/bash
# Stage the full code + data export into each node's /scratch/mukund.hebbar/llama-transfer/repo (the old repo is kept
# as repo-old-<time>), holding a 1-CPU job on the node (compute-node scratch is writable only over ssh from the login
# node while one of our jobs runs there). A node other than node08 also gets node08's verified Llama weights, the
# low-LR probe (adapter + optimizer) and node08's Transformers 5.16.0, so every node runs the same packages.
#   bash phase2/llama_transfer/stage.sh node08 node03
set -euo pipefail
cd "$(dirname "$0")/../.."
HOST=mukund.hebbar@turing.iiit.ac.in
F='post-quantum|store now|openssh.com/pq'
tar -czf local/llama-transfer/code-full.tar.gz --exclude=__pycache__ src scripts data/manifests data/prompts \
  phase2/llama_transfer phase2/failure_driven/scripts phase2/results/local-judge-calibration/gemma-full-explicit \
  local/llama-transfer/reward-parity.jsonl
scp -q -o BatchMode=yes local/llama-transfer/code-full.tar.gz $HOST:llama-code-full.tar.gz 2>&1 | grep -v -E "$F" || true
for NODE in "$@"; do
  ssh -o BatchMode=yes $HOST bash -s -- "$NODE" <<'EOF' 2>&1 | grep -v -E "$F"
set -euo pipefail
# Inner ssh calls take -n: without it they read the rest of this script from stdin.
NODE=$1; B=/scratch/mukund.hebbar/llama-transfer; N8=/scratch/node08/mukund.hebbar
SP=/scratch/mukund.hebbar/failure-driven/venv/lib/python3.12/site-packages
job=$(sbatch --parsable --account=priyesh.shukla --partition=u22 --nodelist=$NODE --ntasks=1 --cpus-per-task=1 \
  --mem=2G --time=01:00:00 --chdir=/tmp --job-name=stage-llama-$NODE --output=/dev/null --wrap 'sleep 3500')
trap "scancel $job" EXIT
until [ "$(squeue -h -j $job -o %T)" = RUNNING ]; do sleep 5; done
ssh -o BatchMode=yes $NODE "mkdir -p $B && rm -rf $B/repo-new && mkdir $B/repo-new && tar -xzf - -C $B/repo-new" < ~/llama-code-full.tar.gz
ssh -n -o BatchMode=yes $NODE "if [ -d $B/repo ]; then mv $B/repo $B/repo-old-\$(date +%s); fi; mv $B/repo-new $B/repo"
if [ "$NODE" != node08 ]; then
  P=runs/llama3b-probes-20261028/solve-probe-low
  ssh -n -o BatchMode=yes $NODE "mkdir -p $B/models $B/$P $SP"
  rsync -a -e "ssh -o BatchMode=yes" $N8/llama-transfer/models/llama/ $NODE:$B/models/llama/
  rsync -a -e "ssh -o BatchMode=yes" $N8/llama-transfer/$P/ $NODE:$B/$P/
  rsync -a -e "ssh -o BatchMode=yes" $N8/failure-driven/venv/lib/python3.12/site-packages/transformers \
    $N8/failure-driven/venv/lib/python3.12/site-packages/transformers-5.16.0.dist-info $NODE:$SP/
fi
ssh -n -o BatchMode=yes $NODE "ls $B/repo/src/anlp_project/qwen_judging.py $B/repo/data/manifests/final-v3/solve-test.jsonl.gz $B/models/llama/source.json $B/runs/llama3b-probes-20261028/solve-probe-low/adapters/step8/optimizer.pt >/dev/null && echo STAGED $NODE"
EOF
done
