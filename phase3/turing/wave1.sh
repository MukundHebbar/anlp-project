#!/bin/bash
# Phase 3b wave 1 + sampling (1 GPU per role). Every step resumes by chunk.
#   bash phase3/turing/wave1.sh <role> <attempts root> <out> [limit]      (from the repository root, inside a GPU job)
# roles: prefill (T1 log p, E-A answer-only, E-B pairwise, E-G trained judges' direct read)
#        direct (E-G alone, to run beside prefill)
#        programs (E-D program checks, program-of-thought, E-C backward)
#        resample (T2 lock-in, then T3 at T 0.7)       temps (T3 hot start, then T 1.3)
#        smoke-a / smoke-b: every kind on a few dev questions
set -euo pipefail
role=$1; root=$2; out=$3; lim=(--limit "${4:-0}")
ev() { python phase3/evidence.py "$1" --set "$2" --attempts "$root" --out "$out" "${lim[@]}"; }
sg() { python phase3/sampling_gen.py "$@" --attempts "$root" --out "$out" "${lim[@]}"; }
case $role in
prefill)
    for k in logprob answer pairwise; do for s in dev test extra; do ev $k $s; done; done
    for arm in global perq; do for s in dev test extra; do
        python phase3/direct_score.py --set $s --attempts "$root" --adapter runs-out/p3-sj2-$arm/adapters/step32 \
            --out "$out/direct-$arm"
    done; done ;;
direct)
    for arm in global perq; do for s in dev test extra; do
        python phase3/direct_score.py --set $s --attempts "$root" --adapter runs-out/p3-sj2-$arm/adapters/step32 \
            --out "$out/direct-$arm"
    done; done ;;
programs)
    for k in program pot backward; do for s in dev test extra; do ev $k $s; done; done ;;
resample)
    for s in test extra; do sg resample --set $s; done
    sg temp --config t07 --set test ;;
temps)
    sg temp --config hot --set test
    sg temp --config t13 --set test ;;
smoke-a)
    for k in logprob answer pairwise program pot backward; do ev $k dev; done ;;
smoke-b)
    sg resample --set dev
    sg temp --config hot --set dev ;;
*) echo "unknown role $role"; exit 2 ;;
esac
echo "wave1 $role done"
