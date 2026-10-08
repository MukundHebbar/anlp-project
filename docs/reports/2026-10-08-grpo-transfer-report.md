# Cross-task transfer with Dr. GRPO on Qwen3.5-2B: SOLVE, JUDGE, RECONSTRUCT

Report date: 2026-10-08 (updated with the mixed-task run). Covers all GRPO runs to date. On-policy distillation
(OPD) is postponed and not covered.

## 1. Summary

We trained Qwen3.5-2B with Dr. GRPO on one task at a time and evaluated each trained model on all three test sets.
Each test set has 400 questions. Results below are deltas against the untrained model, paired, with 95% bootstrap
confidence intervals.

**Headline transfer matrix:** one primary metric per task.

| Trained on ↓ / measured on → | SOLVE accuracy | JUDGE error-finding (step %) | JUDGE Youden's J | RECONSTRUCT PC-v4 |
|---|---:|---:|---:|---:|
| **SOLVE** (step 66) | **+16.6 [+13.8, +19.1]** | +8.8 [+2.1, +16.1] | +15.4 [+6.2, +23.8] | +3.8 [+1.4, +6.3] |
| **JUDGE** (step 26) | −1.1 [−4.1, +1.9] | **+17.2 [+10.2, +24.0]** | **+28.4 [+19.5, +36.9]** | +6.0 [+3.3, +8.6] |
| **RECONSTRUCT** (step 104) | −10.7 [−13.7, −7.7] | +14.2 [+7.2, +21.8] | +7.9 [−1.2, +17.0] | **+21.4 [+19.1, +23.5]** |
| **Mixed: ⅓ SOLVE + ⅓ JUDGE + ⅓ RECONSTRUCT** (step 75) | **+17.1 [+14.3, +19.9]** | **+32.2 [+25.9, +38.6]** | **+45.4 [+37.4, +52.6]** | **+18.3 [+16.1, +20.5]** |

**Main findings:**
0. **One model trained on an equal mixture of the three tasks is the best overall** (§7b):
   - SOLVE: as good as the SOLVE specialist (+0.6 vs it, not significant).
   - JUDGE: far better than the JUDGE specialist (error-finding +15.0, Youden's J +17.0 vs it).
   - RECONSTRUCT: within 3 points of the RECONSTRUCT specialist (−3.0 vs it).
   - It has no negative transfer anywhere.
1. **Every arm improves strongly on its own task.**
   - SOLVE accuracy goes from 52.6% to 69.2%.
   - JUDGE error-finding goes from 34.8% to 52.0%, and false alarms fall from 37.2% to 13.0%.
   - RECONSTRUCT goes from 40.1 to 61.4.
2. **SOLVE training transfers positively to both other tasks.** It is the only arm with no negative cell.
3. **JUDGE training transfers positively to RECONSTRUCT** (+6.0) and leaves SOLVE unchanged (−1.1, not significant).
4. **RECONSTRUCT training hurts SOLVE** (−10.7). Its JUDGE error-finding gain (+14.2) comes with more false alarms
   (+10.2 points): it calls most solutions incorrect. Youden's J, which corrects for that, is not significant
   (+7.9).
5. **SOLVE needed a different recipe.** The first SOLVE run (lr 5e-5, 8 questions per step) gave −2.2.
   - The fix was a larger batch (32 questions per step) with lr 1e-5.
   - A stricter answer checker and overlapped rollouts were also added.
   - Details are in §7.

**Important caveats** (more in §9):
- One seed per arm.
- The SOLVE arm uses the newer recipe; the JUDGE and RECONSTRUCT arms use the first recipe.
- Checkpoints were chosen by different rules per arm (§4).
- The mixed run's checkpoint (step 75) was chosen by training reward without a dev check.

## 2. Setup

### 2.1 Model and data

- **Student:** `Qwen/Qwen3.5-2B`, post-trained, non-thinking chat template. Each run starts from this model.
- **Reference upper model:** `Qwen/Qwen3.5-9B`, evaluated the same way. It is not trained.
- **Data:** FINAL-v3. All questions are from DeepMath-103K (difficulty 5–9). For each task, the questions differ from
  the other tasks' and are matched on topic and difficulty.
  - 4,000 rows per task: 3,600 train and 400 test.
  - A seeded **200-question dev slice** of the train split is never trained on, leaving **3,400** training questions per
    task.
  - The trained arms' question order is a seeded shuffle of those 3,400.

| Task | Input | Output | Correctness |
|---|---|---|---|
| SOLVE | a maths problem | a solution with one `<final_answer>` | answer equal to the key (checker v3, §2.3) |
| JUDGE | a problem + a worked solution split into steps S1…Sn | `Decision: correct/incorrect`, `First wrong step: Sk/none`, an explanation | verdict and first wrong step against the key; explanation by an LLM judge |
| RECONSTRUCT | a final answer + clues (observations) | one JSON with `question`, `assumptions`, `justification` | fidelity to the hidden original question and validity, by an LLM judge |

### 2.2 Prompts and strict gates

- **Student prompts are v2** (`baseline.PROMPT_FILES`). They ask for one final block, carry a brevity line, and state
  the gate rules.
- **Strict gates** (`strict_gates.py`) are applied before any score or reward. A failed gate scores 0.
  - SOLVE: several `<final_answer>` tags that disagree.
  - JUDGE: several or contradictory decisions or steps (e.g. "correct" with a wrong step).
  - RECONSTRUCT: the answer written into the question, monologue or drafting, or no question.
  - RECONSTRUCT is parsed from its last JSON object.

### 2.3 Scoring

| What | How |
|---|---|
| SOLVE correctness | **Checker v3** (`solution_verification.py`, no LLM): normalised exact match, booleans, exact arithmetic, SymPy; cleaned answer forms; numeric precision rules; DeepMath's official `math_equal` + `math-verify` on pure-maths answers only; 10 s limit per check. Audited by hand on 7,465 (key, answer) pairs; every false positive found is a regression test. **All SOLVE numbers in this report use v3**, including re-scored old runs |
| JUDGE verdict and step | deterministic parser + gates |
| JUDGE V/L/E/M, RECONSTRUCT PC-v4 and same question (test) | **Qwen3.8-27B** logit-reading judge (`qwen_judging.py`), calibrated against DeepSeek (agreement r 0.940 JUDGE, 0.840 RECONSTRUCT) |
| Training rewards and RECONSTRUCT dev scoring | **Jev** API (`jev-1.13.0`, `jev_judging.py`): gate → few-shot shortcut stage → calibrated questions |

The judge used for training and dev selection (Jev) is never the one used for final test scores (27B).

### 2.4 Evaluation protocol and metrics

- **Sampling:** T 1.0, top-p 1.0, seed 0. A 16k-token first pass; answers that hit 16k are continued to 32k.
- **Samples:** SOLVE has 4 samples per question; we report pass@1 (the mean over samples) and pass@4. JUDGE and
  RECONSTRUCT have 1 sample per question for trained arms. The untrained and 9B models have 4, so their pass@1 is the
  mean of 4 and estimates the same expected single-sample score.

**Metrics:**
- **SOLVE accuracy:** a strict, gated, verified answer.
- **JUDGE step % (error finding):** on the 200 solutions that contain an error, the model says "incorrect" and names
  the exact first wrong step.
- **JUDGE false alarm %:** a correct solution called incorrect. Lower is better.
- **JUDGE Youden's J:** verdict accuracy on incorrect solutions + on correct solutions − 100. A model that always
  gives the same verdict scores 0. On this balanced 200/200 set it equals 2 × verdict accuracy − 100.
  - These three are the JUDGE headline metrics.
  - Verdict accuracy and the combined "verdict + step" score are secondary; the combined score favours answering
    "correct".
- **JUDGE V/L/E/M /100:** the 27B rubric for verdict, location, explanation and mathematical soundness.
- **RECONSTRUCT PC-v4 /100:** the 27B rubric for premise fidelity, target fidelity, evidence use and validity.
  Shortcuts score 0.
- **RECONSTRUCT same question %:** the reconstruction is judged equivalent to the hidden original.

**Statistics:** deltas are paired on the same questions, with a 95% bootstrap over questions (2,000 resamples).

## 3. Training method: Dr. GRPO

**Objective:** for each question, sample G = 8 answers and score each with a reward r ∈ [0, 1].

- **Advantage:** Âᵢ = rᵢ − mean(r₁…r_G). There is no division by the standard deviation (Dr. GRPO).
- **Loss:** −Σᵢ Σₜ ρᵢₜ · Âᵢ · log π(oᵢₜ) / 16,384 / (number of answers kept).
  - The normalizer is a constant (the generation cap), not each answer's own length (Dr. GRPO).
  - ρ is the token-level importance ratio against vLLM's sampling log-probs, capped at 2.
- **Updates:** one update per batch, so there is no PPO clipping. β (KL) = 0.

**Batch filtering:**
- Questions whose 8 answers all got the same reward carry no signal and are dropped.
- Truncated answers stay in their group with reward 0.

**Rewards (`rewards.py`):** a gated or truncated answer scores 0 for every task.

| Task | Reward |
|---|---|
| SOLVE | 1 if the single final answer is verified correct (checker v3), else 0 |
| JUDGE | 0 for a wrong verdict; otherwise 0.5 + 0.25 · [first wrong step right] + 0.25 · min(8, E + M)/8, with E (explanation, 0–4) and M (soundness, 0–4) from Jev |
| RECONSTRUCT | Jev staged score (P + T + E + M, each 0–4) × 6.25/100, minus 0.1 for several question drafts; shortcut or gated answers score 0 |

**Shared settings:**
- LoRA r 64, α 64, dropout 0, on all attention and MLP projections (62.5M trainable parameters);
- AdamW (β 0.9/0.999, weight decay 0), grad clip 1.0;
- T 1.0, 16k cap, vLLM rollouts on one L40S and the trainer on another.

**Per-arm recipe:**

| | SOLVE (new recipe) | JUDGE | RECONSTRUCT | SOLVE (first recipe, superseded) |
|---|---|---|---|---|
| lr | **1e-5**, 5-step warm-up | 5e-5 constant | 5e-5 constant | 5e-5 constant |
| Questions × answers per step | **32 × 8** | 8 × 8 | 8 × 8 | 8 × 8 |
| Rollouts | **overlapped** (step s+1 generated while step s trains; one-update lag, corrected by ρ) | synchronous | synchronous | synchronous |
| Steps trained | 79 (stopped by hand) | 104 | 104 | 104 |
| Questions seen by the final checkpoint | 2,112 (step 66) | 208 (step 26) | 832 (step 104) | 832 |
| Checkpoint rule | best 8-step rolling training reward, confirmed on dev | best dev verdict + step among 26/52/78/104 | best dev Jev score among 26/52/78/104 | best dev accuracy among 26/52/78/104 |
| Wall time per step | ~8 min (15 without overlap) | ~4 min | ~2 min | ~5 min |
| GPU-h (training + probes + evals) | ~34 | ~18 | ~10 | ~19 |

## 4. Checkpoint selection

| Arm | Candidates (dev score) | Chosen |
|---|---|---|
| SOLVE (new) | Rolling training reward peaked at 0.691 (step 66), up from 0.528 at steps 1–8. Dev accuracy: step 8 **56.1%**, step 66 **72.4%** (untrained 52.4%) | 66 |
| JUDGE | Dev verdict + step (sum of two accuracies): step 26 **1.441**, 52 1.215, 78 1.302, 104 1.034 | 26 |
| RECONSTRUCT | Dev Jev score: step 26 56.6, 52 62.2, 78 60.7, 104 **63.1** | 104 |
| SOLVE (first recipe) | Dev accuracy: 47.9 / 51.2 / 49.4 / **54.2** (checker v3) | 104 |

- JUDGE peaked early and fell afterwards. For future JUDGE runs, choose within steps 30–50.
- The SOLVE step-66 checkpoint was picked by training reward. Its SOLVE test was run while training continued, at the
  user's request. No later model choice used test data.

## 5. Results in full

### 5.1 Absolute scores (test, pass@1 unless noted, 95% CI)

| Model | SOLVE acc | SOLVE pass@4 | JUDGE verdict | JUDGE step % | JUDGE false alarm | JUDGE Youden J | JUDGE V/L/E/M | RECON PC-v4 | RECON same Q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Untrained Qwen3.5-2B | 52.6 [48.9, 56.2] | 80.2 [76.2, 84.0] | 64.3 [61.7, 67.1] | 34.8 [30.9, 38.5] | 37.2 [33.2, 41.1] | 28.6 [23.4, 34.1] | 53.9 [51.6, 56.5] | 40.1 [38.4, 41.9] | 2.9 [1.9, 4.0] |
| **Trained on SOLVE** (step 66) | **69.2** [65.6, 72.9] | **87.5** [84.0, 90.8] | 72.0 [67.5, 76.2] | 43.5 [36.5, 50.5] | 23.5 [17.5, 29.5] | 44.0 [35.0, 52.5] | 62.9 [59.1, 66.7] | 43.9 [41.2, 46.6] | 6.8 [4.5, 9.2] |
| **Trained on JUDGE** (step 26) | 51.6 [48.0, 55.1] | 76.0 [72.0, 80.2] | **78.5** [74.2, 82.5] | **52.0** [45.0, 58.5] | **13.0** [8.5, 18.0] | **57.0** [48.5, 65.0] | **72.2** [68.5, 75.8] | 46.1 [43.4, 48.8] | 5.8 [3.5, 8.0] |
| **Trained on RECONSTRUCT** (step 104) | 41.9 [38.4, 45.6] | 66.2 [61.8, 71.0] | 68.2 [63.7, 72.8] | 49.0 [42.5, 56.0] | 47.5 [40.5, 54.5] | 36.5 [27.5, 45.5] | 55.7 [52.0, 59.5] | **61.4** [59.3, 63.3] | 2.5 [1.0, 4.2] |
| **Trained on the mixture** (step 75) | **69.8** [66.1, 73.4] | 84.5 [80.8, 87.8] | **87.0** [83.5, 90.0] | **67.0** [60.0, 73.5] | **7.5** [4.0, 11.0] | **74.0** [67.0, 80.0] | **80.8** [77.6, 83.7] | 58.4 [55.9, 60.8] | **10.5** [7.8, 13.5] |
| *Reference: Qwen3.5-9B (untrained)* | 82.7 | 91.5 | 87.6 | 87.9 | 17.8 | 75.2 | 85.7 | 72.7 | 19.6 |

### 5.2 Δ against the untrained 2B (paired, 95% CI; **bold** = own task)

| Trained on | SOLVE acc | SOLVE pass@4 | JUDGE verdict | JUDGE step % | JUDGE false alarm | JUDGE Youden J | JUDGE V/L/E/M | RECON PC-v4 | RECON same Q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SOLVE (step 66) | **+16.6 [+13.8, +19.1]** | +7.2 [+3.8, +10.8] | +7.7 [+3.1, +11.9] | +8.8 [+2.1, +16.1] | −13.8 [−19.8, −8.1] | +15.4 [+6.2, +23.8] | +9.0 [+5.1, +12.6] | +3.8 [+1.4, +6.3] | +3.9 [+1.9, +5.9] |
| JUDGE (step 26) | −1.1 [−4.1, +1.9] | −4.2 [−8.0, −0.2] | +14.2 [+9.8, +18.4] | **+17.2 [+10.2, +24.0]** | **−24.2 [−29.2, −19.4]** | **+28.4 [+19.5, +36.9]** | **+18.3 [+14.7, +21.8]** | +6.0 [+3.3, +8.6] | +2.9 [+0.8, +4.9] |
| RECONSTRUCT (step 104) | −10.7 [−13.7, −7.7] | −14.0 [−18.2, −9.8] | +3.9 [−0.6, +8.5] | +14.2 [+7.2, +21.8] | +10.2 [+3.9, +16.5] | +7.9 [−1.2, +17.0] | +1.8 [−2.0, +5.6] | **+21.4 [+19.1, +23.5]** | **−0.4 [−2.2, +1.4]** |
| Mixture (step 75) | +17.1 [+14.3, +19.9] | +4.2 [+1.0, +7.8] | +22.7 [+18.7, +26.3] | +32.2 [+25.9, +38.6] | −29.8 [−34.2, −25.5] | +45.4 [+37.4, +52.6] | +26.9 [+23.7, +29.9] | +18.3 [+16.1, +20.5] | +7.6 [+4.9, +10.3] |

For false alarms a negative Δ is an improvement.

### 5.3 How far each arm closes the gap to the 9B

Gap closed = (arm − 2B) / (9B − 2B), on the own-task metric:
- SOLVE accuracy: 16.6 / 30.1 = **55%**;
- JUDGE step %: 17.2 / 53.1 = **32%**;
- RECONSTRUCT PC-v4: 21.4 / 32.6 = **66%**.

The mixed model closes 57% on SOLVE (17.1 / 30.1), **61% on JUDGE error-finding** (32.2 / 53.1) and 56% on
RECONSTRUCT (18.3 / 32.6). On JUDGE it nearly reaches the 9B: verdict 87.0 vs 87.6, and fewer false alarms (7.5 vs
17.8).

### 5.4 JUDGE by answer-key label (verdict accuracy, pass@1, 200 questions each)

| Model | Correct solutions (verdict right) | Incorrect solutions (verdict right) | Incorrect solutions (verdict + step right) |
|---|---:|---:|---:|
| Untrained 2B | 62.7 | 65.9 | 34.8 |
| Trained on SOLVE | 76.5 | 67.5 | 43.5 |
| Trained on JUDGE | **87.0** | **70.0** | **52.0** |
| Trained on RECONSTRUCT | 52.5 | **84.0** | 49.0 |
| Trained on the mixture | **92.5** | 81.5 | **67.0** |

- The JUDGE arm improves on both kinds of solution.
- The RECONSTRUCT arm's gain on incorrect solutions comes from answering "incorrect" more often, which costs it on
  correct solutions.
- The SOLVE arm improves on both, mostly on correct solutions.

### 5.5 Sub-dimensions (27B, 0–4 levels, sample 0; gated or unscored answers count as 0)

| Model | JUDGE V | JUDGE L | JUDGE E | JUDGE M | RECON P | RECON T | RECON E | RECON M |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Untrained 2B | 2.57 | 1.95 | 2.08 | 1.99 | 1.71 | 1.97 | 1.90 | 0.84 |
| Trained on SOLVE | 2.88 | 2.40 | 2.52 | 2.26 | 1.88 | 2.10 | 2.06 | 0.98 |
| Trained on JUDGE | **3.14** | **2.78** | **2.80** | **2.83** | 1.88 | 2.17 | 2.28 | **1.04** |
| Trained on RECONSTRUCT | 2.73 | 2.03 | 2.09 | 2.06 | **2.49** | **3.00** | **3.58** | 0.75 |
| Trained on the mixture | 3.48 | 3.19 | 3.25 | 3.00 | 2.37 | 2.72 | 2.88 | **1.37** |
| Qwen3.5-9B | 3.61 | 3.50 | 3.54 | 3.50 | 2.85 | 3.17 | 3.44 | 2.33 |

The RECONSTRUCT arm gains on fidelity (P, T) and evidence use (E), but not on mathematical validity (M: 0.84 → 0.75).
Its reconstructions read closer to the source but are not better verified. The "same question" rate does not move.

### 5.6 Behaviour: gate failures and answer length (test, all samples)

| Model | SOLVE gate % | SOLVE mean tokens | JUDGE gate % | JUDGE mean tokens | RECON gate % | RECON mean tokens |
|---|---:|---:|---:|---:|---:|---:|
| Untrained 2B | 6.8 | 8,089 | 13.8 | 5,087 | 12.6 | 5,337 |
| Trained on SOLVE | **1.4** | 8,643 | 11.8 | 5,613 | 11.5 | 5,734 |
| Trained on JUDGE | 4.0 | 5,518 | **1.2** | **3,017** | 16.0 | 5,287 |
| Trained on RECONSTRUCT | 1.1 | 5,291 | 3.8 | 5,026 | **3.8** | **2,236** |
| Trained on the mixture | 1.0 | 9,114 | 1.8 | 6,751 | 5.5 | 7,793 |
| Qwen3.5-9B | 3.2 | 4,088 | 5.4 | 3,737 | 3.8 | 3,889 |

- Fewer than 0.5% of trained-model answers hit the 32k cap.
- **JUDGE and RECONSTRUCT training shorten answers** on their own tasks (−41% and −58%). JUDGE training also
  shortens SOLVE answers (−32%) without losing accuracy.
- **SOLVE training keeps SOLVE length about the same** (+7%) and removes most format failures.
- **The mixed model writes longer answers on every task:** SOLVE +13%, JUDGE +33%, RECONSTRUCT +46%. Answers capped
  at 32k stay at or below 0.4%.

### 5.7 SOLVE answer types (test, 400 × 4)

| | Correct | Wrong (checked) | Unverified | Gated | No answer |
|---|---:|---:|---:|---:|---:|
| Untrained 2B | 52.6% | 20.8% | 16.2% | 6.8% | 3.6% |
| Trained on SOLVE (step 66) | **69.2%** | 15.6% | 12.6% | 1.4% | 1.3% |

The +16.6 splits into about 8 points of format (gated or missing answers fixed) and about 9 points of correctness.

## 6. Training curves

| Arm | Rolling training reward (start → peak → end) | Questions with a learning signal per step | Mean length | Truncation |
|---|---|---|---|---|
| SOLVE (new) | 0.53 (steps 1–8) → **0.69** (steps 57–66) → 0.64 (steps 72–79) | 25 → 18 of 32 | 7.7k → 7.9k | 2–6% |
| JUDGE | 0.64 (steps 1–13) → 0.76 (steps 40–52) → 0.58 (steps 92–104) | 8 → 6 of 8 | 6.0k → 3.0k | 5% → 4% |
| RECONSTRUCT | 0.40 (steps 1–13) → 0.57 (steps 40–104, flat) | 8 of 8 | 4.4k → 2.5k | ~0% |
| SOLVE (first recipe) | 0.55 → 0.35 (falling) | 5.5 → 3.8 of 8 | 8.7k → 8.8k | ~9% |

Rewards differ by task and are only comparable within a row. For SOLVE, every step in the first pass draws unseen
questions, so the reward measures accuracy on new questions.

## 7. The SOLVE story: why the first run failed and what fixed it

**First recipe (lr 5e-5, 8 × 8, 104 steps): test −2.2 [−5.8, +1.1].** Diagnosis from its 6,656 training rollouts:
- **Too little signal per step.** Questions whose answers differed fell from 5.5 to 3.8 of 8, so each update came from
  about 3 questions at a high lr, a large and noisy step.
- **More wrong answers.** Wrong answers rose from 23% to 33% of rollouts. Truncation fell, but the answers that used
  to be cut off now finished wrong.
- **Little data.** Only 832 of 3,400 questions were seen.

**Changes, each tested:**
1. **Checker v3** (§2.3).
   - It recovers about 2 points of correct answers that v2 left unverified (the untrained 2B goes 51.0 → 52.6 on test).
   - The audit found and blocked false positives in both our layers and DeepMath's official checker: a 1e-4
     tolerance that accepts 88327 for 88329, `True == 1`, `a ≠ 3` read as 3, hedged answers ("3 or 5"), and prose.
   - `parse_expr` (Python eval) was removed from the vendored DeepMath code.
2. **32 questions × 8 answers per step,** so 18–25 questions per step carry a signal.
3. **lr probe at 32 × 8, step 8, dev 200 × 4:**
   - lr 1e-5: **+3.8 [−0.2, +7.6]**; lr 2e-5: +3.9 [+0.2, +7.5].
   - They are tied, so we chose 1e-5, the literature value for LoRA (≈10× the 1e-6 used for full fine-tuning in
     DeepMath and DeepScaleR).
   - An lr 5e-5 control at 32 × 8 was cancelled when the GPU cap dropped to 4.
4. **Overlapped rollouts:** 15 → ~8 min per step; the vLLM/trainer log-prob gap is unchanged at 0.010–0.011.
5. **Best-by-reward checkpoints:** the top 3 by 8-step rolling reward are kept automatically.

**Not used:** difficulty filtering (by user decision), early stopping, a length penalty, or a longer cap. 16k covers
99.3% of the untrained model's correct answers.

## 7b. The mixed-task run (⅓ SOLVE + ⅓ JUDGE + ⅓ RECONSTRUCT)

Plan: `docs/plans/2026-10-08-mixed-task-grpo-plan.md`.

### Recipe
- **Data:** the first 1,134 questions of each task's training order (the same orders as the single-task arms, no dev
  questions), interleaved S, J, R, … for **3,402 questions in total**.
- **Batches:** every batch of 30 holds exactly 10 + 10 + 10 (balanced mixed batches, chosen over rotating one-task
  batches on the literature; plan §2).
- **Training:** Dr. GRPO, **lr 2e-5** (5-step warm-up), 30 questions × 8 answers, T 1.0, 16k cap, overlapped rollouts.
  Each task keeps its own reward. LoRA r64, 2 L40S GPUs, about 6.5 min per step.
- **Tracking:**
  - per-task reward, learning signal, |advantage|, length and truncation;
  - the combined rolling reward (mean over tasks of each task's 8-step rolling reward minus its steps 1–8 average);
  - the top 3 checkpoints by it are kept;
  - early stopping on it with patience 3 (8-step checks).
- **Stopped by hand at step 80** (2,400 questions, 800 per task).
- **Evaluated checkpoint: step 75**, the best by combined rolling reward (+0.174). It was **not** dev-checked. A
  step-72 test eval was started and cancelled in favour of step 75.

### Training curve (8-step blocks)

| Steps | SOLVE reward | JUDGE reward | RECONSTRUCT reward | Length S / J / R | Truncation |
|---|---:|---:|---:|---|---:|
| 1–8 | 0.62 | 0.52 | 0.31 | 7.1k / 4.9k / 5.1k | 1–5% |
| 17–24 | 0.62 | 0.62 | 0.42 | 6.1k / 4.3k / 5.4k | 0–1% |
| 41–48 | 0.59 | 0.75 | 0.44 | 6.0k / 4.1k / 5.0k | 0% |
| 65–72 | 0.68 | 0.79 | 0.46 | 9.0k / 7.0k / 8.4k | ~4% |
| 73–80 | 0.63 | 0.72 | 0.49 | 8.8k / 7.9k / 8.0k | 4–7% |

Combined rolling reward at the 8-step checks:

| Step | 16 | 24 | 32 | 40 | 48 | 56 | 64 | 72 | 80 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Combined gain | +0.007 | +0.072 | +0.065 | +0.091 | +0.109 | +0.092 | +0.128 | +0.161 | +0.130 |

**Behaviour during training:**
- **RECONSTRUCT's mean |advantage| was about 2× smaller** than SOLVE's and JUDGE's (0.11–0.15 vs 0.20–0.34), below the
  plan's 3× action threshold, so no rescaling was applied.
- **Lengths rose for all tasks from step ~57.** This is the same drift the lr 5e-5 single-task runs showed, and the
  reason to stop around step 75–80.

### Mixed model vs each single-task model (test, paired Δ = mixed − single, 95% CI)

| Compared with | SOLVE acc | SOLVE pass@4 | JUDGE step % | JUDGE false alarm | JUDGE Youden J | JUDGE V/L/E/M | RECON PC-v4 | RECON same Q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SOLVE model (step 66) | **+0.6 [−1.8, +2.8]** | −3.0 [−5.8, −0.2] | +23.5 [+15.0, +32.5] | −16.0 [−22.5, −9.5] | +30.0 [+20.5, +40.0] | +17.9 [+13.6, +22.2] | +14.5 [+11.4, +17.5] | +3.8 [+0.8, +6.8] |
| JUDGE model (step 26) | +18.2 [+15.1, +21.2] | +8.5 [+5.0, +12.0] | **+15.0 [+7.5, +23.0]** | **−5.5 [−10.5, −0.5]** | **+17.0 [+8.0, +25.5]** | **+8.5 [+5.0, +12.2]** | +12.3 [+9.4, +15.2] | +4.8 [+2.0, +7.8] |
| RECONSTRUCT model (step 104) | +27.8 [+24.4, +31.4] | +18.2 [+13.8, +22.8] | +18.0 [+8.5, +27.5] | −40.0 [−47.5, −33.0] | +37.5 [+26.5, +48.0] | +25.1 [+20.4, +29.5] | **−3.0 [−5.9, −0.1]** | **+8.0 [+5.0, +11.0]** |

**Bold = the specialist's own task.** Against each specialist on its own task, the mixed model is:
- **equal on SOLVE** (+0.6, not significant). Its pass@4 is 3 points lower: the SOLVE specialist's answers are more
  varied.
- **much better on JUDGE**: +15.0 error-finding, −5.5 false alarms, +17.0 Youden's J. But the JUDGE specialist used
  the first recipe (lr 5e-5, 8 × 8) and saw only 208 JUDGE questions, against 750 here. The comparison mixes the
  mixture effect with a better recipe.
- **slightly worse on RECONSTRUCT score** (−3.0) but **better on same-question** (+8.0) and on validity (M 1.37 vs
  0.75). The RECONSTRUCT specialist scored higher on fidelity (P, T, E) with weaker maths.

**Every off-diagonal cell is positive.** Mixing removes the negative transfer of the RECONSTRUCT and JUDGE models
(their SOLVE −10.7 and −1.1 become +17.1).

**SOLVE answer types (test):**

| | Correct | Wrong | Unverified | Gated | No answer | Capped |
|---|---:|---:|---:|---:|---:|---:|
| Mixed | 69.8% | 16.4% | 11.4% | 1.0% | 1.0% | 0.4% |

This is close to the SOLVE specialist's breakdown (§5.7).

### Caveats specific to the mixed run
- **lr 2e-5**, against 1e-5 for the SOLVE specialist and 5e-5 for the JUDGE and RECONSTRUCT specialists.
- **The checkpoint was picked by training reward only.**
- **800 questions per task were seen** (SOLVE specialist 2,112; JUDGE 208; RECONSTRUCT 832).
- **One seed.**

## 8. Comparison with published recipes

| Recipe | lr | Questions/step × answers | Reward | Notes |
|---|---|---|---|---|
| **Ours, SOLVE (new)** | 1e-5 LoRA | 32 × 8 | 1/0 verified | Dr. GRPO, no KL, overlapped rollouts |
| DeepMath-1.5B (same data source; official code) | 1e-6 full | 128 × 16, refills all-same groups | +1/−1 (`math_equal` or math-verify) | KL 0.001, T 0.6, 24k + overlong penalty |
| DeepScaleR-1.5B | 1e-6 full | 128 × 8 | 1/0 | 8k → 16k → 24k context |
| Dr. GRPO paper | full | — | 1/0 | no ÷ std, constant normalizer |
| TRL / "LoRA without regret" | ~1e-5 LoRA | 32–512 | — | LoRA ≈ 10× the full-fine-tuning lr |

## 9. Limitations

1. **One seed per arm.** The confidence intervals cover question sampling, not training randomness.
2. **The arms use different recipes.** (This also applies to the mixed run: §7b.) SOLVE uses lr 1e-5, 32 × 8 and overlap; JUDGE and RECONSTRUCT use lr 5e-5 and
   8 × 8. The off-diagonal cells therefore mix task effects and recipe effects. Re-running JUDGE and RECONSTRUCT with
   the SOLVE recipe would make the matrix uniform (about 2 × 15 h on 2 GPUs).
3. **Different amounts of data:** the final checkpoints saw 2,112 (SOLVE), 208 (JUDGE) and 832 (RECONSTRUCT)
   questions.
4. **Different selection rules.** SOLVE: training reward, confirmed on dev. JUDGE and RECONSTRUCT: dev among 4
   fixed steps.
5. **Trained arms use 1 sample per question for JUDGE and RECONSTRUCT** (the untrained model uses 4). Pass@1 estimates
   the same quantity, but the trained arms' JUDGE and RECONSTRUCT numbers are noisier.
6. **Judge-based metrics depend on the 27B judge.** Its calibration against DeepSeek: r 0.94 JUDGE, 0.84 RECONSTRUCT.
   The RECONSTRUCT arm was trained on a different judge (Jev); its validity score (M) did not improve.
7. **About 12.6% of SOLVE answers stay unverified** (their form, e.g. a set described in words, can't be checked by
   rules). They count as wrong for every model, so the deltas are unbiased but absolute accuracy is underestimated.

## 10. Compute

- **Hardware:** Turing cluster, L40S GPUs.
  - Never more than 6 GPUs at once, then never more than 4 from 2026-10-07.
  - A typical arm used 2 GPUs: vLLM + trainer.
- **Ledger:** 234 GPU-h used of the 500 approved (the mixed run: ~22.5 GPU-h including its test eval and judging), covering all work (baselines, judges, the first matrix, the SOLVE
  probes and run, evaluations); 266 remain.
- **API:** Jev for JUDGE and RECONSTRUCT rewards and RECONSTRUCT dev scoring, a few dollars in total. The 27B judge runs
  on our GPUs.

## 11. Reproducing

The exact commands are in `docs/reports/2026-10-07-status-and-runbook.md` §3. In short:

```bash
# SOLVE arm (new recipe), end to end from the workstation; at most 4 GPUs
nohup bash scripts/solve_grpo_pipeline.sh > artifacts/opd/evals/solve-pipeline.log 2>&1 &

# one GRPO arm by hand (2 GPUs)
python3 scripts/turing/launch.py submit --name <run> --gpus 2 --hours 14 --node node11 -- \
  python scripts/turing/opd_run.py --task <task> --config grpo --steps 106 \
    --set prompts_per_step=32 --set optimizer.lr=1e-5 --set optimizer.warmup_steps=5 \
    --set async_rollouts=true --set best_window=8 --set best_keep=3 \
    --student-port <port> --out /scratch/mukund.hebbar/anlp-opd/v3/<run>

# evaluation, judging, report
python scripts/turing/eval_matrix.py --name <n> --adapter <adapter> --split test --samples 4 --samples-tasks solve --out <dir>
python scripts/turing/qwen_judge_run.py --eval-dir test:<dir>/s0 --out <log>/answers.jsonl
uv run python scripts/qwen_judge_calibration.py score <dir>/s0
uv run python scripts/rescore_solve.py <eval dirs>        # after any checker change
uv run python scripts/report_grpo_matrix.py               # writes artifacts/baselines/final-v3/v3-report/grpo-matrix.md
```

## 12. Files

| What | Where |
|---|---|
| Test answers and scores per model | `artifacts/baselines/final-v3/test/{v3-grpo-mixed-lr2e-5-step75, v3-pass4-2b, v3-pass4-9b, v3-grpo-lr1e-5-solve-step66, v3-drgrpo-judge-step26, v3-drgrpo-reconstruct-step104, v3-drgrpo-solve-step104, v3-drgrpo-judge-step104}` |
| Generated matrix tables | `artifacts/baselines/final-v3/v3-report/grpo-matrix.md` |
| Training metrics and checkpoint records | `artifacts/opd/evals/mixed-lr2e-5/` (mixed run), `artifacts/opd/evals/solve-p1-lr1e-5/` (SOLVE), `artifacts/opd/evals/v3-drgrpo-dev/` (first-recipe arms, dev selections) |
| Adapters | Turing scratch: node11 `v3/solve-p1-lr1e-5/adapters/best-step66` (also `~/anlp-project/runs-out/solve-lr1e-5-step66-adapter`), node11 `v3/v3-drgrpo-judge-r2/adapters/step26`, node07 `v3/v3-drgrpo-reconstruct/adapters/step104` |
| Code | `src/anlp_project/{opd_train.py (GRPO loop, overlap, best-by-reward), rewards.py, solution_verification.py (checker v3), strict_gates.py, jev_judging.py, qwen_judging.py}` |
| Scripts | `scripts/solve_grpo_pipeline.sh`, `scripts/select_solve_step.py`, `scripts/rescore_solve.py`, `scripts/report_grpo_matrix.py`, `scripts/turing/{opd_run.py, eval_matrix.py, qwen_judge_run.py, launch.py}` |
| Earlier plans and status | `docs/plans/2026-10-06-dr-grpo-plan.md`, `docs/reports/2026-10-07-status-and-runbook.md` |
