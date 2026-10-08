# Transfer-matrix run: warm-up → OPD for all three tasks, and the 3×3 evaluation

Started 2026-10-02. Turing only (node07, node11; L40S). One seed. The goal is three trained students
(SOLVE, JUDGE, RECONSTRUCT) with one recipe, and every checkpoint, including the untrained student,
evaluated on all three test sets.

## Resources

| Item | State |
|---|---|
| GPUs | node07 4 × L40S (1 held by another user), node11 4 × L40S. **The Slurm account `priyesh.shukla` has an 8-GPU limit shared by all its users**, so the usable count varies (5–7 observed). |
| Code | `~/anlp-project` on Turing (home, visible on both nodes); outputs in `~/anlp-project/runs-out/<job>` |
| Environment | venv and model caches on `/scratch/mukund.hebbar/anlp-opd` (node-local, present on both nodes) |
| Ledger | `artifacts/opd/turing/turing_budget.json`: +128 GPU-h approved on 2026-10-01 for this run |

## Recipe (identical for all arms)

1. **Teacher answers:** Qwen3.8-27B, 2 samples per warm-up question (640 SOLVE, 640 JUDGE; RECONSTRUCT reuses its
   512-question set), generated at an 8k cap so both the 4k and 8k warm-up sets come from one run.
   - **Kept if:** finished, parses, repetition < 0.2, within the training cap, and correct (SOLVE verifier v2; JUDGE verdict
     and, for incorrect solutions, the first wrong step). RECONSTRUCT has no correctness check.
2. **SFT warm-up:** 400 examples per task (the same N for every arm), 1 epoch, LR 1e-4, LoRA r 64.
3. **OPD (`opd.MATRIX_CONFIG`):**
   - **Loss and regularisers:** sampled-token reverse KL, KL anchor β 0.5 to the SFT model, overlong penalty 1.0,
     anti-repetition teacher instruction.
   - **Settings:** LR 5e-5, T 1.0, **64 prompts per step**, rollout cap **4,096** (8,192 if the probe fails).
   - **Prompts:** the 3,400 train questions outside the dev slice, reshuffled each epoch (`opd-matrix-<task>.json`).
   - **Length:** 156 steps (≈ 3 epochs). Adapters are kept at steps 16, 52, 104 and 156 and at every 8th step.

## The 4k probe (decides the cap for every arm)

The SOLVE run at 4k is the probe: its first 16 steps are the probe, and it continues if 4k passes.

**4k passes if, at step 16:**
- training truncation is not rising and stays ≤ 30%, with no auto-stop and a log-prob gap below 0.03; and
- dev SOLVE accuracy (200 questions, 16k → 32k eval) at step 16 is at least the SFT-only and untrained dev accuracy
  minus 3 points.

**If it fails,** every arm uses 8k: the SOLVE and JUDGE warm-ups are re-filtered at ≤ 8k from the same teacher run,
RECONSTRUCT uses its existing 8k set, and SOLVE restarts. Steps drop to 104 if time requires.

## Speed-ups

| Change | Check |
|---|---|
| 4k cap, 64 prompts per step | — |
| Teacher scores each rollout as soon as it finishes | — |
| Micro-batched training (right padding, ≤ 16k tokens per batch) | vLLM-vs-trainer log-prob gap must stay near 0.015 |
| One teacher serving the JUDGE and RECONSTRUCT students (`scripts/turing/opd_shared.py`) | Fallback: separate 3-GPU runs |
| Evals at 16k, with capped answers continued from their own tokens to 32k (`scripts/turing/eval_matrix.py`) | Same distribution as one 32k pass |

## Layout

| Node | Jobs |
|---|---|
| node07 | untrained SOLVE dev eval → SOLVE OPD (teacher TP 2 + student/trainer on one GPU) |
| node11 | SOLVE and JUDGE teacher answers → SFT warm-ups → JUDGE and RECONSTRUCT OPD on one shared teacher (GPUs 2–3; students on GPUs 0 and 1) |

Training gets the GPUs first; test evaluations run as GPUs free up, one task per GPU.

## Evaluation and report

- **Checkpoints:** the untrained student, the 3 SFT-only adapters, and each arm's OPD adapters at steps 52, 104 and 156.
  Each is evaluated on all three test sets, 400 questions each.
- **Scoring:** SOLVE uses the deterministic verifier. JUDGE uses the parsed verdict and first wrong step, plus the
  DeepSeek V/L/E/M score. RECONSTRUCT uses the DeepSeek PC-v4 score, with unusable answers scored 0. DeepSeek V4.1 Flash
  runs on DeepInfra, about $1.5 per checkpoint.
- **Report:** `scripts/report_matrix.py` writes `artifacts/transfer-matrix/REPORT.md` with 95% bootstrap intervals and
  paired differences against the untrained student.

## Monitoring

- **W&B:** project `anlp-transfer`, group `matrix-v1`, fed by `scripts/wandb_bridge.py`, which runs on the laptop and
  mirrors `metrics.jsonl` every 60 s.
- **Trainer auto-stop:** truncation rise, log-prob gap, repetition.
- **Recovery:** a failed run resumes from its latest adapter, whose optimiser state is saved.
