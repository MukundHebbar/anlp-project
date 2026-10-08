#!/bin/bash
# Submit the transfer-matrix training chain on Turing (run on the login node from ~/anlp-project).
#
#   node07 (3 GPUs): RECONSTRUCT re-filter (<=4k) -> SFT -> OPD
#   node11 (4 GPUs): SOLVE and JUDGE teacher answers (2 GPUs each) -> SFT -> OPD for both on one
#                    shared teacher (GPUs 2-3; SOLVE student on GPU 0, JUDGE student on GPU 1)
#
# Every stage waits for the previous one with Slurm afterok. Recipe: opd.MATRIX_CONFIG
# (4k rollouts, 64 prompts per step); the SFT warm-up uses the same N for every task.
set -euo pipefail
cd "$(dirname "$0")/../.."
STEPS=${STEPS:-156}
KEEP=${KEEP:-52,104}
N_SFT=${N_SFT:-400}
OUT=$PWD/runs-out
L="python3 scripts/turing/launch.py submit"
jid() { python3 -c 'import json,sys; t=sys.stdin.read(); print(json.loads(t[t.index("{"):t.index("}")+1])["job_id"])'; }

# node11: teacher answers for SOLVE and JUDGE (4k cap, correctness filter)
G1=$($L --name gen-solve-4k --gpus 2 --hours 2 --node node11 -- python scripts/turing/teacher_gen.py --task solve \
  --n 640 --samples 2 --max-tokens 4096 --filter-max-tokens 4096 --correct --chunk 320 --out {out} | jid)
G2=$($L --name gen-judge-4k --gpus 2 --hours 2 --node node11 -- python scripts/turing/teacher_gen.py --task judge \
  --n 640 --samples 2 --max-tokens 4096 --filter-max-tokens 4096 --correct --chunk 320 --out {out} | jid)

# node07: RECONSTRUCT re-filter of the existing teacher answers at <=4k, then SFT, then OPD
R1=$($L --name sft-reconstruct-4k --gpus 1 --hours 1 --node node07 -- bash -c "python scripts/turing/teacher_gen.py \
  --task reconstruct --n 512 --filter-only /scratch/mukund.hebbar/anlp-opd/runs/gen-reconstruct-w512/teacher.jsonl \
  --filter-max-tokens 4096 --out {out} && python scripts/turing/sft.py --data {out}/sft.jsonl --n $N_SFT --out {out}" | jid)
R2=$($L --name opd-reconstruct-matrix --gpus 3 --hours 12 --node node07 --after "$R1" -- python scripts/turing/opd_run.py \
  --task reconstruct --config matrix --steps "$STEPS" --keep-steps "$KEEP" --init-adapter "$OUT/sft-reconstruct-4k/adapter" \
  --out {out} | jid)

# node11: SFT for SOLVE and JUDGE, then both OPD runs on one shared teacher
S1=$($L --name sft-solve-4k --gpus 1 --hours 1 --node node11 --after "$G1" -- python scripts/turing/sft.py \
  --data "$OUT/gen-solve-4k/sft.jsonl" --n "$N_SFT" --out {out} | jid)
J1=$($L --name sft-judge-4k --gpus 1 --hours 1 --node node11 --after "$G2" -- python scripts/turing/sft.py \
  --data "$OUT/gen-judge-4k/sft.jsonl" --n "$N_SFT" --out {out} | jid)
SJ=$($L --name opd-solve-judge-matrix --gpus 4 --hours 13 --node node11 --after "$S1:$J1" -- python scripts/turing/opd_shared.py \
  --teacher-gpus 2,3 --log-dir {out} \
  --run "0|{out}/opd-solve-matrix|--task solve --config matrix --steps $STEPS --keep-steps $KEEP --init-adapter $OUT/sft-solve-4k/adapter" \
  --run "1|{out}/opd-judge-matrix|--task judge --config matrix --steps $STEPS --keep-steps $KEEP --init-adapter $OUT/sft-judge-4k/adapter" | jid)
echo "gen-solve $G1  gen-judge $G2  sft-reconstruct $R1  opd-reconstruct $R2  sft-solve $S1  sft-judge $J1  opd-solve-judge $SJ"
