# Phase 3: self-verification for answer selection

Theory and predictions: `docs/research/verification-theory/theory-and-plan.md`.
Protocol, fixed before any results: `PREREGISTRATION.md` (sha256 recorded in the conversation log).
Paper: `paper/`.

## Pipeline

| Step | Where | Command |
|---|---|---|
| Question sets | laptop | `PYTHONPATH=src .venv/bin/python phase3/sets.py` → `manifests/sets.json` (test 400, dev 200, extra 400, train 1,200) |
| Environment | Turing, CPU job | `sbatch -w node09 phase3/turing/setup_env.sbatch` (vLLM 0.30 cu129, Qwen3.5-2B in `/scratch/$USER/anlp-p3`) |
| Attempts + judging | Turing, 4 × 1 GPU | `python3 scripts/turing/launch.py submit --name p3-w<i> --gpus 1 --hours 12 --node node09 --scratch /scratch/aryama.murthy/anlp-p3 -- bash phase3/turing/run_part.sh <i> 4 <out>` |
| Grading | laptop | `PYTHONPATH=src .venv/bin/python phase3/grade.py --set <s> --attempts <out>/attempts --out phase3/runs/graded` |
| Analysis | laptop | `python phase3/analyze.py --graded phase3/runs/graded --judge <out>/judge --out phase3/runs/analysis` |
| Paper tables | laptop | `python phase3/paper_tables.py` |
| Stage-2 prompts | laptop | `PYTHONPATH=src .venv/bin/python phase3/build_selfjudge.py --attempts <out>/attempts --graded phase3/runs/graded --out <dir>` |
| Stage-2 training | Turing, 2 GPUs per arm | `bash phase3/turing/train_selfjudge.sh <global\|perq> <prompts dir> <out>` |

## Files

| File | Role |
|---|---|
| `common.py` | Sets, prompts, the own-attempt → JUDGE step conversion (rebuilt; the Phase-2 converter was lost), verdict-token scoring |
| `gen.py` | 16 attempts per question (T 1.0, 16k cap), resumable by chunk, `--part i/n` to split across GPUs |
| `judge.py` | Judge chain (stops at "Decision:"), forced verdict probability after the chain, direct probability with no reasoning |
| `grade.py` | Correctness (project SOLVE reward) and answer groups (checker equivalence) |
| `analyze.py` | Stage-0 measurements, pooled / within / contested AUROC, configurations, selection rules (majority, adaptive-consistency, Bayes, argmax, CAV) at matched unit and token cost, paired bootstrap |
| `build_selfjudge.py` | Stage-2 training prompts: `global` (Phase-2 replica) and `perq` (per-question balanced) |
| `remote_ctl.py` | Unused HTTPS control channel for Jarvislabs (the campus network blocks SSH to Jarvislabs; the permission policy declined an exposed exec server). Kept for reference. |

## Turing notes (2026-10-28)

- node08 does not mount this account's home. node09, node10 and node12 do.
- FlashInfer's sampling kernels need a newer CUDA runtime than the 575 driver supports. `gen.py`/`judge.py` set
  `VLLM_USE_FLASHINFER_SAMPLER=0`.
- Jarvislabs: SSH from the campus network times out (outbound port 22 is blocked except for whitelisted hosts).
