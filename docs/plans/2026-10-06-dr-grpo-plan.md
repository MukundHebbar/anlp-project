# Dr. GRPO plan (final): Qwen3.5-2B on SOLVE, JUDGE, RECONSTRUCT

Date: 2026-10-06. GRPO only, as Dr. GRPO; OPD is postponed. Baselines are done (`2026-10-06-final-plan.md` §8).
Limits: at most 6 GPUs at once; Jev only where required; nothing beyond the 2-step checks runs without the user's go.

## 1. What the 2-step checks measured (2 GPUs per run: vLLM on one, trainer on the other)

| Task | Seconds per step (step 1) | Rollouts / training | Task reward at step 1 | Mixed groups | Failed Jev calls | Mean length |
|---|---:|---|---:|---:|---:|---:|
| SOLVE | 249 | 170 / 77 s | 0.47 | 5 / 8 | — | 7.2k |
| JUDGE | 248 | 157 / 88 s | 0.56 | 8 / 8 | 0 | 5.1k |
| RECONSTRUCT | 267 | (with Jev) | 0.28 | — | 0 | 5.8k |

- **Placement:** vLLM uses about 40 GB on GPU 0 and the trainer 12–18 GB on GPU 1.
- **Gradient norms are small (0.003–0.013)** under Dr. GRPO's fixed normalizer. AdamW normalizes the update
  size, so each parameter still moves by about lr; lr 5e-5 needs no change.

## 2. Configuration (`opd.GRPO_CONFIG`, `--config grpo`)

| Setting | Value |
|---|---|
| Algorithm | Dr. GRPO: advantage = reward − group mean (no std); loss = token sum / 16,384 (no 1/\|o\|) |
| Start | the plain Qwen3.5-2B (post-trained, non-thinking, v2 prompts), all three tasks |
| LoRA / optimizer | r 64, α 64; AdamW, lr 5e-5 constant, grad clip 1.0 |
| Rollouts | 8 prompts × 8 samples = 64 per step, T 1.0; 16k cap; truncated rollouts filtered; equal-reward groups skipped |
| KL | β 0 |
| **Steps** | **104** (was 52; affordable at ~4.2 min/step). Adapters kept every 8 steps |
| Rewards | SOLVE: exact answer, 1/0. JUDGE: 0 for a wrong verdict, else 0.5 + 0.25 step + 0.25·Jev(E+M)/8. RECONSTRUCT: Jev staged score / 100, −0.1 for several drafts. Gated and truncated answers: 0 |
| Seed | 1 |

## 3. Making an own-task gain as likely as possible (without touching the test sets)

1. **Train longer:** 104 steps, 832 distinct prompts per arm.
2. **Choose the checkpoint on dev, by a rule fixed now:**
   - evaluate steps **26, 52, 78 and 104** on the arm's **own** dev slice (200 questions);
   - SOLVE uses 4 samples, JUDGE and RECONSTRUCT 1 sample;
   - the metric is SOLVE accuracy, JUDGE verdict + step, or RECONSTRUCT score (Jev);
   - report the checkpoint with the best own-task dev score; ties go to the later step;
   - **step 104 is also reported** as the fixed endpoint, for transparency.
3. **Free early-warning monitoring**, from training logs on new prompts at each step:
   - the 8-step rolling task reward should rise;
   - **by step 24, if the rolling reward is not above its steps 1–8 level on an arm**, report it and propose
     one restart at lr 1e-4.
4. **Stop rules:** truncation over 15%, a rising gate rate, repetition over 0.5, or Jev failures over 5% of
   rollouts.
5. **Hacking audit at step 26:** read the 20 highest-reward RECONSTRUCT rollouts.

## 4. Schedule (≤ 6 GPUs at all times)

| Phase | What | GPUs | Wall | GPU-h |
|---|---|---|---:|---:|
| A | Finish the 2-step checks (running) | 6 | ~10 min | ~1 |
| B | **Main runs:** SOLVE, JUDGE, RECONSTRUCT, 104 steps each, at the same time (2 GPUs each: vLLM + trainer) | **6** | **~7.5–8 h** | **~47** |
| C | Dev selection: 4 checkpoints × 3 arms, own-task dev slice only, 12 short jobs spread over 6 GPUs | 6 | ~1 h | ~5 |
| D | Test evaluation of the 3 selected checkpoints (plus step 104 where it differs): 3 test sets; SOLVE 4 samples, JUDGE and RECONSTRUCT 1 | 6 | ~2–3 h | ~15 |
| E | 27B judging of JUDGE and RECONSTRUCT test answers (800 per checkpoint), overlapping D | 2 | ~30 min per checkpoint | ~4 |
| F | Report | 0 | ~1 h | — |
| **Total** | | | **~12–14 h** | **~72** |

- **Ledger:** 378 GPU-h remaining.
- **Jev:**
  - about $4.50 for training rewards (104 steps, JUDGE and RECONSTRUCT);
  - about $0.30 for RECONSTRUCT dev selection.

## 5. Results reported

- **GRPO transfer matrix.** Rows are the trained arms; columns are the three test sets:
  - SOLVE accuracy (pass@1, pass@4);
  - JUDGE verdict, step and V/L/E/M;
  - RECONSTRUCT PC-v4 and same question.

  Each cell gives Δ against the 2B baseline, paired bootstrap, 95% CI.
- **Own-task cells** (the diagonal) are the primary results; **off-diagonal cells measure transfer**.
- **Secondary:**
  - the 16k-budget score, gate and format rates, and answer length (Dr. GRPO should not inflate it);
  - training reward curves;
  - GPU-h and Jev $ per arm;
  - the dev-selected vs step-104 comparison.

## 6. Later (not in this plan)

- OPD arms with the 9B teacher and warm-up.
- Extra seeds for the diagonal cells.
- Committing the 2026-10-06 work (awaiting OK).

## 7. Changes during the runs (2026-10-06)

- **Outputs moved to node scratch** (`/scratch/mukund.hebbar/anlp-opd/v3`). The 50 GB home directory filled up,
  which killed the first JUDGE run and emptied the GPU ledger (rebuilt from per-job records).
- **Truncated rollouts are kept, with reward 0, inside their group** (Dr. GRPO as published). Before, they were
  filtered out (DAPO).
  - With filtering, JUDGE's answers ran away: truncation 2% → 67% and mean length 5.5k → 14k by step 12.
    The auto-stop rule fired.
  - SOLVE was drifting the same way (truncation 3% → 14%).
  - Both were restarted as `v3-drgrpo-{solve,judge}-r2` with `drop_truncated=false` (now the config default).
  - RECONSTRUCT kept its run: its answers stayed at 1–1.3k tokens with 0% truncation, so the setting never
    applied there.

## 8. Result (2026-10-07): Dr. GRPO transfer matrix complete

Full report: `artifacts/baselines/final-v3/v3-report/grpo-matrix.md`. FINAL-v3 test. Dev-selected checkpoints:
SOLVE step 104, JUDGE step 26, RECONSTRUCT step 104. Δ against the untrained 2B, paired, 95% CI.

| Trained on → measured on | SOLVE acc | JUDGE verdict | JUDGE step | JUDGE V/L/E/M | RECON PC-v4 |
|---|---:|---:|---:|---:|---:|
| SOLVE | **−2.2 [−5.7, +1.0]** | +0.7 | −3.2 | +4.1 [+0.2, +8.0] | −6.7 [−9.3, −4.1] |
| JUDGE | −0.8 | **+14.2 [+9.8, +18.4]** | **+17.2 [+10.2, +24.0]** | **+18.3 [+14.7, +21.8]** | +6.0 [+3.3, +8.6] |
| RECONSTRUCT | −10.6 [−13.6, −7.7] | +3.9 | +14.2 [+7.2, +21.8] | +1.8 | **+21.4 [+19.1, +23.5]** |

**JUDGE headline metrics (user decision, 2026-10-07).** Report these instead of combined accuracy, which favours
answering "correct":
- **step %**: on a solution with an error, the verdict is "incorrect" and the exact first wrong step is named;
- **false alarm %**: a correct solution called incorrect (lower is better);
- **Youden's J**: verdict accuracy on incorrect keys + on correct keys − 100; a model that always gives the same
  verdict scores 0.

| Model | Step % | False alarm % | Youden's J |
|---|---:|---:|---:|
| Untrained 2B | 34.8 | 37.2 | 28.6 |
| **JUDGE arm (step 26)** | **52.0 (+17.2 [+10.2, +24.0])** | **13.0 (−24.2 [−29.2, −19.4])** | **57.0 (+28.4 [+19.5, +36.9])** |
| JUDGE arm (step 104) | 41.5 (+6.8) | 10.5 (−26.8) | 44.5 (+15.9) |
| SOLVE arm | 31.5 (−3.2) | 18.5 (−18.8) | 30.0 (+1.4) |
| RECONSTRUCT arm | 49.0 (+14.2) | 47.5 (+10.2) | 36.5 (+7.9) |

How to read the table:
- The RECONSTRUCT arm's step gain comes with more false alarms: it calls most solutions incorrect.
- The SOLVE arm's lower false-alarm rate comes from calling most solutions correct; its J is unchanged.
- The per-label table and the combined-accuracy breakdown are in `grpo-matrix.md`.

**Own-task results:**
- JUDGE and RECONSTRUCT gain strongly on their own tasks.
- SOLVE does not gain on its own task: −2.2 on test, not significant; dev 0.520 vs 0.503. Its answers grew long and
  truncated during training, and the user chose to leave it as is.

**Transfer:**
- RECONSTRUCT → JUDGE step: positive (+14.2).
- JUDGE → RECONSTRUCT: positive (+6.0).
- Training on RECONSTRUCT or SOLVE lowers SOLVE and RECONSTRUCT scores respectively (−10.6, −6.7).

**Compute:** ~55 GPU-h for the GRPO phase, never more than 6 GPUs at once. Training reward and dev scoring used Jev.

**Rule for future JUDGE runs (user, 2026-10-07):** stop at ~30–50 steps, choosing within that window on dev.
JUDGE's dev score peaked at step 26 and fell by step 104.

**SOLVE failure breakdown (test, 4 samples):**

| | Correct | Finished, wrong | No answer or gated | Capped at 32k | Needed >16k |
|---|---:|---:|---:|---:|---:|
| Untrained 2B | 51.0% | 38.4% | 10.5% | 0.1% | 2.6% |
| Dr. GRPO SOLVE (step 104) | 48.8% | 48.2% | 1.6% | 1.4% | 17.2% |

Training fixed format failures, but the recovered answers and longer reasoning mostly ended wrong.
