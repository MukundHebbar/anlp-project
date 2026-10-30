#!/bin/bash
# Run on the login node while our node08 job holds its allocation.
set -euo pipefail
DEST=/scratch/mukund.hebbar/ministral-baseline
NODE=node08
SSH=(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$NODE")
"${SSH[@]}" "mkdir -p $DEST/repo /scratch/mukund.hebbar/yashas-anlp-env/venv"
rsync -a --exclude=__pycache__ /scratch/node07/mukund.hebbar/yashas-anlp-env/venv/ \
    "$NODE:/scratch/mukund.hebbar/yashas-anlp-env/venv/"
rsync -a "$HOME/.local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu/" "$NODE:$DEST/python/"
rsync -a --exclude=.cache "$HOME/anlp-models/Ministral-3-3B-Instruct-2512-BF16-b6d637be/" "$NODE:$DEST/model/"
rsync -a "$1" "$NODE:$DEST/repo.tar.gz"
"${SSH[@]}" "tar -xzf $DEST/repo.tar.gz -C $DEST/repo"
"${SSH[@]}" "$DEST/python/bin/python3.12 -c 'import hashlib,json; from pathlib import Path; p=Path(\"$DEST/model\"); x=json.loads((p/\"source.json\").read_text()); [(print(n),None) if hashlib.file_digest((p/n).open(\"rb\"),\"sha256\").hexdigest()==v[\"sha256\"] else (_ for _ in ()).throw(RuntimeError(n)) for n,v in x[\"files\"].items()]; print(\"Pinned model verified on node08\")'"
"${SSH[@]}" "touch $DEST/.staged-ready"
echo 'Node08 runtime, repository and pinned model staged.'
