# Next steps after the baselines: warm-up → checks → main runs → evaluation

Date: 2026-10-06. This file is the runbook for Phases 2–4 of `2026-10-06-final-plan.md`, which keeps the settings.
Limits: at most 6 GPUs at once; each step starts only after the user's go-ahead; Jev only where required.

## What the baselines tell us for the next phases

- The 9B is far ahead on every task (+23 to +53 points), so all three OPD arms go ahead.
- The 2B's answers average 5–8k tokens. Only 1–4% continue past 16k, so **the 16k training cap fits**.
- The 9B is concise (3.7–4.1k tokens) and breaks the gates far less (4–5% vs 13–14% on JUDGE and
  RECONSTRUCT). Its warm-up answers should teach format and brevity as well as content.
- Measured cost: one 2B test evaluation with 4 samples takes about 2 h on 3 GPUs. 27B judging takes about
  1.5–2 h on 2 GPUs per checkpoint.

## Phase 2: warm-up and checks (~4–5 h wall, ~10 GPU-h, ~$0.40 Jev)

| # | Step | Detail | GPUs | Time | Passes if |
|---|---|---|---|---|---|
| 2a | 9B warm-up answers | `teacher_gen.py --config opd9b --tp 1 --n 512 --samples 2 --max-tokens 16384`, JUDGE (with `--correct`) and RECONSTRUCT | 2 | ~1 h | both finish |
| 2b | Filter | JUDGE: gates + correct verdict and step (inside teacher_gen). RECONSTRUCT: gates, then **Jev ≥ 70**, best of 2 per question (`--filter-only --jev-min 70`, run locally) | 0 | ~15 min | **≥ 256 kept per task** (expected ~400 JUDGE, ~300 RECONSTRUCT) |
| 2c | SFT warm-ups | `sft.py --n 256`, 1 epoch, JUDGE and RECONSTRUCT | 2 | ~20 min | loss falls, adapter saved |
| 2d | Check the warm-ups on dev | dev slices, 1 sample, JUDGE and RECONSTRUCT, each warm-up adapter. Jev on RECONSTRUCT dev only | 2 | ~40 min | gate rate and format **no worse** than the 2B (13.8% / 12.6%); RECONSTRUCT dev not below 40.1 by more than noise |
| 2e | GRPO unit tests (local) | group advantages, reward ranges, gate zeroing, failed Jev call → rollout dropped, truncated rollouts filtered | 0 | ~1 h coding | all tests pass |
| 2f | 2-step checks | GRPO-RECONSTRUCT 2 steps (1 GPU, Jev reward from the node) and OPD-JUDGE 2 steps (student + 9B teacher, 2 GPUs) | 3 | ~45 min | finite loss; rewards or teacher log-probs present; Jev reachable; adapter syncs; seconds per step recorded |
| 2g | Commit | all code, prompts, calibration files and plans from 2026-10-06 | 0 | — | needs the user's OK |

From 2f's seconds per step, re-estimate Phase 3's wall time before launching it.

## Phase 3: main runs, 52 steps, 1 seed (~18–20 h wall, ~95 GPU-h, ~$4 Jev)

| Wave | Runs | GPUs | Time (est.) |
|---|---|---|---|
| 1 | OPD-SOLVE, OPD-JUDGE, OPD-RECONSTRUCT + shared 9B teacher (`opd_shared.py --config opd9b`); GRPO-JUDGE, GRPO-RECONSTRUCT | 4 + 2 = 6 | ~9–10 h |
| 2 | GRPO-SOLVE (no judge needed), on the first GPU wave 1 frees | 1 | ~8–9 h |

- **The Jev-rewarded GRPO arms go in wave 1**, so any reward problem shows up early.
- **Time per step** (estimate; replaced by 2f's measurement): ~500–600 s.
  - Rollouts are 64 × ~6k tokens.
  - The LoRA update follows.
  - The teacher or Jev scoring overlaps the rollouts.
- **Starting points:**
  - SOLVE arms start from the plain 2B;
  - JUDGE and RECONSTRUCT arms start from their warm-up adapter (`--init-adapter`).
- **Kept checkpoints:** steps 26 and 52. **Final = 52, fixed in advance.**
- **Free monitoring from the training logs:** reward or teacher gap, truncation, gate rate, repetition, length.
- **Stop rules:** truncation over 15%, a steadily rising gate rate, or repetition over 0.5. A stopped run is
  reported as stopped.
- **Hacking audit at step 26:** read the 20 highest-reward RECONSTRUCT rollouts. Check that gate-rate trends
  don't diverge between the GRPO and OPD arms.

## Phase 4: evaluation and report (~12–14 h wall, ~65 GPU-h, $0 Jev)

| # | Step | GPUs | Time |
|---|---|---|---|
| 4a | 8 checkpoints (6 trained at step 52 + 2 warm-up-only) × 3 test sets × 4 samples (`eval_matrix.py --adapter … --samples 4`), two at a time | 6 | ~8 h |
| 4b | 27B judging of each checkpoint as it finishes (`qwen_judge_run.py`, a free port per session), then `qwen_judge_calibration.py score` | 2 | overlaps 4a; ~1.5 h per checkpoint |
| 4c | Dev check of the step-26 and step-52 adapters (diagnostics only), 1 sample; Jev on RECONSTRUCT dev only | 2 | ~2 h |
| 4d | Report: two transfer matrices (Δ against each arm's starting model, paired bootstrap), GRPO − OPD per cell, warm-up-only rows, pass@1 and pass@4, 16k-budget score, gate and format rates, length, GPU-h and $ per arm | 0 | ~2 h |

`report_matrix.py` needs extending for the pass@4 sample folders and the GRPO/OPD/warm-up rows. That's code only
and can be done during Phase 3.

## Totals

| Phase | Wall | GPU-h | Jev |
|---|---|---:|---:|
| 2 warm-up and checks | ~4–5 h | ~10 | ~$0.40 |
| 3 main runs | ~18–20 h | ~95 | ~$4 |
| 4 evaluation and report | ~12–14 h | ~65 | $0 |
| **Total** | **~1.5–2 days** | **~170** | **~$4.50** |

The ledger has 378 GPU-h remaining.

## Decisions needed before starting
1. Go-ahead for Phase 2 (steps 2a–2f).
2. OK to commit the 2026-10-06 work (2g) before the main runs.
