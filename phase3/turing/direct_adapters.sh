#!/bin/bash
# Direct verdict probabilities on the cached dev/test attempts for several adapters (prefill only, 1 GPU).
#   bash phase3/turing/direct_adapters.sh <attempts root> <name=adapter|none> ...
set -euo pipefail
root=$1; shift
for spec in "$@"; do
    name=${spec%%=*}; adapter=${spec#*=}
    for s in dev test; do
        python phase3/direct_score.py --set "$s" --attempts "$root/attempts" --adapter "$adapter" --out "$root/direct-$name"
    done
done
echo "direct scoring done"
