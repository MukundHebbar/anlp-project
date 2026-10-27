# Phase 2: full results (positive and negative)

All Phase-2 work on Qwen3.5-2B after the Phase-1 GRPO transfer report, in one place. Every experiment that was run
is listed, including the ones that failed.

## Setup and terms

| Term | Meaning |
|---|---|
| **SOLVE** | Task: write a solution to a maths problem |
| **JUDGE** | Task: given a step-numbered solution, say whether it is correct and, if not, which step is the first wrong one |
| **RECONSTRUCT** | Task: recover the question from its answer and some clues |
| SOLVE / JUDGE / RECONSTRUCT model | Phase-1 LoRA adapter trained by Dr. GRPO on that task only (`solve-step66`, `judge-step26`, `reconstruct-step104`) |
| Mixed model | Phase-1 adapter trained on all three tasks (`mixed-step75`); the best overall model |
| Untrained | Qwen3.5-2B with no adapter |
| Own attempts | Solutions written by the mixed model itself, then shown to a judge |
| AUROC | Chance that a judge rates a random wrong attempt as more suspicious than a random right one. 0.5 = guessing, 1.0 = perfect |
| F1 (error-finding) | Harmonic mean of: exact first wrong step found on wrong solutions, and "correct" said on correct solutions |
| Majority vote | Sample 4 answers, keep the most common one |
| Best possible | Share of problems where at least one of the 4 answers is right (the ceiling for any picking rule) |
| [a, b] | 95% paired bootstrap interval (2,000 resamples over problems). If it excludes 0, the difference is significant |

Data: the repository's FINAL-v3 splits (SOLVE dev slice of 200 problems, SOLVE test 400, JUDGE test 400) and
ProcessBench (3,400 step-split solutions by 12 other models, first wrong step labelled by humans). Answers are graded
by the repository's answer checker (v3). All runs on IIIT Turing.

---

## 1. Overview

| # | Experiment | Question | Outcome |
|---|---|---|---|
| 1 | Hints for always-wrong problems | Can JUDGE / RECONSTRUCT hints make dead GRPO problems learnable? | **Negative** |
| 2 | Tutor | Can JUDGE + RECONSTRUCT mark student solutions, including ones that solve the wrong question? | **Positive** |
| 3 | Self-checking solver with drift detection | Can the model catch and repair its own wrong attempts? | **Negative** |
| 4 | JUDGE on real errors (ProcessBench) | Does trained error-finding transfer from injected to real errors? | **Partly** (about half) |
| 5 | Step-format solving | Does writing solutions in numbered steps make them easier to check? | **Negative** |
| 6 | Layer transplant | Where does the checking skill live in the network? | **Positive** (strong, causal) |
| 7 | Bias vs real skill (signal detection) | What exactly transfers between tasks? | **Positive** (explanatory) |
| 8 | Error representation inside the model | Is there an internal "error" feature, and does it work on own attempts? | **Positive on benchmarks, negative on own attempts** |
| 9 | Why judging own attempts fails | Self-blindness or something else? | **Explained**: length and error type |
| 10 | Shortened rewrites before judging | Does a same-model condensed rewrite make own attempts easier to judge? | **Negative** |
| 11 | Failure-driven GRPO | Does turning GRPO failures into JUDGE / RECONSTRUCT items help SOLVE? | **Negative** |
| 12 | **Self-judge training** | Train the judge on its own attempts, labelled only by the answer checker | **Positive for judging, negative for SOLVE accuracy** |

The two stated goals:

| Goal | Best result | Met? |
|---|---|---|
| Better SOLVE accuracy (any loss over 0.5 points counts as failure) | Self-judge picking: +1.2 over majority vote on test, not significant | **No** |
| JUDGE good at judging the model's own solutions | Self-judge: AUROC 0.568 → 0.665 on test, +0.097 [+0.066, +0.128] | **Yes** (moderate size) |

---

## 2. Hints for always-wrong problems (negative)

GRPO learns nothing from a problem the model always gets right or always gets wrong. The mixed model answered its
750 SOLVE training problems 8 times each.

| Result over 8 tries | Problems | Share |
|---|---|---|
| Always right | 291 | 39% |
| Sometimes right (useful to GRPO) | 374 | 50% |
| Always wrong | 85 | 11% |
| ↳ answer unreadable or cut off | 46 | |
| ↳ genuinely wrong | 39 | |

For the 39: JUDGE looked for the first wrong step in a failed attempt; RECONSTRUCT wrote the question the wrong
answer would be correct for. The mixed model then retried with each hint (23 non-Yes/No problems, 184 tries per hint).

| What the specialists produced | Result |
|---|---|
| JUDGE finds a usable wrong step | 0 / 39 (5 / 39 with 4× longer budget) |
| RECONSTRUCT writes a genuinely different question | rarely; mostly a reworded original |

| Hint | Correct tries |
|---|---|
| No hint | 6 |
| RECONSTRUCT hint | 2 |
| "An earlier attempt got X, which is wrong" | 7 |
| JUDGE hint (5 problems, 40 tries) | 0 |

**Finding:** same-size specialists share the learner's blind spot; no hint beats simply saying which answer is wrong.

---

## 3. Tutor (positive)

Two kinds of student mistake: a **false step** (one line is wrong; JUDGE finds it) and a **wrong question** (every
line is right but it solves a slightly different problem, e.g. divisors of k instead of k + 1; RECONSTRUCT rebuilds
the question the work actually answers and Qwen3.8-27B compares it with the one set).

Test set: 200 correct + 200 false-step solutions (JUDGE test set) + 102 wrong-question solutions (one detail of a
correct solution's problem changed, confirmed by the 27B to change the answer).

| Measure | Specialists | Mixed |
|---|---|---|
| False-step solutions caught by JUDGE | 64.5% | 80.5% |
| ↳ with the exact wrong step named | 55.5% | 72.5% |
| Correct solutions wrongly flagged by JUDGE | 4.5% | 4.0% |
| Wrong-question solutions caught by JUDGE alone (held out) | 69.6% | 73.6% |
| ↳ with RECONSTRUCT added, threshold for 5% false alarms | **78.2%** | **81.3%** |
| ↳ with RECONSTRUCT added, threshold for 10% false alarms | **83.1%** | **83.5%** |
| Correct solutions flagged with RECONSTRUCT added (5% / 10% threshold) | 8.8% / 15.2% | 10.0% / 14.2% |

Thresholds picked on one half of the solutions, measured on the other (50 random splits, both directions).

**Finding:** on short, step-numbered solutions both specialists are useful: RECONSTRUCT adds 8–14 points of
wrong-question detection on top of JUDGE, at 5–10 points more false alarms.
**Caveat:** the wrong-question solutions were made by the 27B, not by real students.

---

## 4. Self-checking solver with drift detection (negative)

The mixed model made 4 attempts at each of 200 unseen problems (800 attempts, 242 wrong). JUDGE checked each attempt;
RECONSTRUCT rebuilt the question from the work at ¼, ½, ¾ and the end, and the 27B flagged drift. Flagged attempts
were cut at the flag and regenerated.

| Checker | Flags wrong attempts | Flags correct attempts | AUROC |
|---|---|---|---|
| JUDGE (specialist) | 4.1% | 2.7% | 0.51 |
| JUDGE (mixed) | 7.4% | 2.2% | 0.53 |
| Drift check (specialist) | 0.0% | 0.0% | 0.44 |
| Drift check (mixed) | 0.4% | 0.5% | 0.38 |

| Repair rule | Accuracy |
|---|---|
| None | 69.75% |
| Where JUDGE flagged | 70.13% |
| Random, same number | 69.75% |
| Perfect flags (every wrong attempt) | 76.75% |

**Finding:** repair would be worth about 7 points with perfect detection, but neither checker finds the wrong
attempts. Only 1 wrong attempt showed drift without a false step.

---

## 5. JUDGE on real errors: ProcessBench (partly positive)

Same JUDGE prompt and sampling for every model. F1 as defined above.

| Model | Injected errors (JUDGE test set) | Real errors (ProcessBench average) |
|---|---|---|
| Untrained 2B | 44.7 | 41.1 |
| SOLVE model | 52.0 | 45.5 |
| JUDGE model | 68.9 | 54.6 |
| RECONSTRUCT model | 50.4 | 55.2 |
| Mixed | 79.5 | 59.8 |
| Qwen3.5-9B (reference) | 84.1 | 74.5 |

**Finding:** about half of the trained gain survives on real errors (mixed: +34.8 → +18.7). RECONSTRUCT training helps
real error-finding as much as JUDGE training. Not comparable with published ProcessBench numbers (different prompt,
temperature-1 sampling).

---

## 6. Step-format solving (negative)

Idea: if the solver writes in numbered steps, its attempts should be easier to judge. Mixed model, 200 dev problems ×
4 attempts, asked to answer in the JUDGE step format.

| Measure | Normal format | Step format |
|---|---|---|
| Accuracy, one attempt | 69.75 | 63.75 |
| pass@4 | | 86.5 |
| Majority vote | | 73.5 |
| Judge-weighted vote (JUDGE model / mixed as judge) | | 76.0 / 75.0 |
| JUDGE AUROC on these attempts (JUDGE model / mixed) | 0.53 | 0.588 / 0.545 |
| Mean length | | 6,474 tokens |

**Finding:** the step format costs 6 points of SOLVE accuracy and does not make judging work.

---

## 7. Layer transplant: the checking skill lives in the first layers (positive)

Hybrid adapters: the SOLVE adapter with the LoRA weights of some layers swapped for another adapter's. No training.
Change in F1 vs the plain SOLVE adapter; ProcessBench GSM8K + MATH (1,400 solutions); synthetic = JUDGE test set.

| SOLVE adapter with layers … from … | ProcessBench F1 change | Synthetic F1 change |
|---|---|---|
| **0–5 from JUDGE** | **+15.3 [+11.5, +19.2]** | **+16.1 [+10.2, +22.4]** |
| 0–3 from JUDGE | +11.5 [+7.5, +15.5] | +8.9 [+2.1, +15.8] |
| 6–11 / 12–17 / 18–23 from JUDGE | +6.8 / +2.2 / +4.5 | +3.3 / +3.5 / −1.8 |
| single layers 0, 1, 2, 3, 4, 5 from JUDGE | +4.7, +5.4, +2.5, +3.2, −1.5, +1.7 | |
| all 24 from JUDGE (= the JUDGE adapter) | +10.7 [+6.8, +14.9] | +14.0 [+7.9, +20.8] |
| 0–5 from mixed | +12.6 [+8.7, +16.4] | +16.6 [+10.0, +22.9] |
| *Controls* | | |
| 0–5 with SOLVE's change removed (base weights) | +0.4 [−3.6, +4.5] | −3.7 |
| 0–5 filled with JUDGE's layers 16–21 (same size of change, wrong place) | −2.7 [−6.7, +1.3] | −4.0 |
| 0–5 from RECONSTRUCT | −2.0 [−6.3, +2.1] | −2.3 |
| *Reverse: JUDGE adapter with SOLVE's layers 0–5* | *JUDGE's +10.7 falls to +1.6* | |
| *Mixed adapter with SOLVE's layers 0–5* | *−2.2 [−5.5, +1.0]* | |

- Causal in both directions: adding JUDGE's early layers gives the skill; removing them from JUDGE takes it away.
- JUDGE's weight change is spread evenly over depth (each 6-layer block holds 24–26% of it), so the effect is not just
  where the change is largest.
- The skill adds up roughly over layers 0–3.
- Mixed training spreads the skill over depth (removing its early layers costs little); single-task RL concentrates it
  early.
- Exact first-wrong-step accuracy among solutions flagged: SOLVE 47.5%, JUDGE 48.4%, **composite 59.3%**, mixed 61.0%.

Generalization and cost (OlympiadBench / Omni-MATH: 1,000 solutions each; SOLVE test: 400 questions × 4, 16k cap):

| Adapter | OlympiadBench F1 | Omni-MATH F1 | SOLVE test accuracy (change vs SOLVE) | pass@4 |
|---|---|---|---|---|
| SOLVE | 44.2 | 35.0 | 66.6 | 84.0 |
| **SOLVE + JUDGE layers 0–5** | **53.1** | **46.6** | 62.7 (**−3.9 [−6.4, −1.4]**) | 83.75 |
| JUDGE | 54.0 | 42.2 | 49.8 (−16.8 [−19.7, −13.9]) | 77.75 |
| Mixed | 53.2 | 43.9 | 66.5 (−0.1 [−2.6, +2.3]) | 83.0 |

| Judging own attempts (dev, 200 × 4) | AUROC |
|---|---|
| JUDGE model | 0.571 |
| SOLVE + JUDGE layers 0–5 | 0.605 |

**Finding:** a located, causal, training-free result about where RL puts a checking skill. **Not usable as a solver**
(−3.9 SOLVE), and it barely helps on own attempts.

---

## 8. Bias vs real skill: signal-detection analysis (positive, explanatory)

Each model's verdicts split into sensitivity d′ (telling wrong from right) and criterion c (negative = quick to say
"wrong").

| Model | JUDGE test d′ / c | ProcessBench d′ / c | ProcessBench exact step, among flagged |
|---|---|---|---|
| Untrained | 0.73 / −0.04 | 2.13 / +0.25 | 49.7% |
| SOLVE model | 1.17 / +0.13 | 2.35 / +0.40 | 55.0% |
| JUDGE model | 1.64 / +0.30 | 2.50 / +0.68 | 52.9% |
| RECONSTRUCT model | 1.05 / **−0.46** | 2.25 / **−0.18** | 54.4% |
| Mixed | **2.32** / +0.27 | **2.63** / +0.45 | **61.1%** |

**Finding:** RECONSTRUCT's "transfer" to checking is mostly the model becoming suspicious, not discerning (it matched
JUDGE's ProcessBench F1 with SOLVE-level sensitivity). Only mixed training adds real sensitivity. On real errors the
untrained model already discriminates fairly well; most trained gain is giving a usable verdict, the bias, and
locating the step.

---

## 9. An error feature inside the model (positive on benchmarks, negative on own attempts)

A crosscoder (shared sparse dictionary, 8,192 features) on the residual streams of the untrained and mixed models.

| Result | Value |
|---|---|
| Features specific to one model (layers 12 and 18) | None (every live feature shared; decoder share 0.48–0.52) |
| Activation change from GRPO | 8–9% |
| Layer-18 feature flagging the first wrong step, held-out ProcessBench AUROC | **0.80** |
| … controlling for step position / excluding final-answer steps / within wrong solutions only | 0.80 / 0.80 / 0.80 |
| … added to a position + length + final-step baseline | 0.69 → 0.82 |
| … on OlympiadBench / Omni-MATH (layer 12) | 0.73 |
| … on the synthetic JUDGE set | 0.74 |
| … across the 12 ProcessBench generator models | 0.67–0.82 |
| **… on solutions freshly sampled from our models (untrained 2B, mixed, 9B; condensed or not)** | **0.50–0.53** |

**Finding:** RL reuses existing features rather than creating new ones. A real error feature exists and is robust on
curated benchmarks, but it is at chance on the model's own fresh solutions, exactly where verbal judging also fails.

---

## 10. Why judging own attempts fails: length and error type, not self-blindness

JUDGE AUROC at telling wrong from right attempts, 200 dev problems × 4 (JUDGE model / mixed as judge):

| Attempts judged | Mean length | AUROC |
|---|---|---|
| Own, step format | 6,317 tokens | 0.58 / 0.54 |
| Untrained 2B's | 4,662 | 0.55 / 0.49 |
| Qwen3.5-9B's | 1,902 | 0.63 / 0.59 |
| Own, condensed to 6 steps by the 9B | 482 | 0.67 / 0.59 |

**Finding:** others' attempts are no easier, so it is not self-blindness. Shorter attempts are easier to judge.
Neither verbal nor internal checking transfers from curated error sets to the model's own failures.

---

## 11. Shortened same-model rewrites before judging (negative)

The mixed model rewrote each of its own attempts in a short form (no larger model, no check that the answer was kept);
the mixed model then judged the rewrites. 200 dev problems × 4 attempts.

| Measure | Value |
|---|---|
| Mean rewrite length | 998 tokens |
| Rewrites whose final answer differs from the original | 30% |
| Judge AUROC on originals / on rewrites | 0.54 / 0.57 |

| Picking 1 answer of 4 (dev) | Accuracy |
|---|---|
| Majority vote | 77.5 |
| Judge on originals, weighted vote | 78.5 (+1.0, not significant) |
| Judge on rewrites, weighted vote | 78.0 (+0.5) |
| Pairwise comparison of the top-2 answers (8 votes) | 76.5 (−1.0) |
| Best possible | 86.5 |

**Finding:** rewriting changes the answer too often and does not make judging meaningfully better. Not run on test
(no dev improvement).

---

## 12. Failure-driven GRPO pilot (negative)

During SOLVE GRPO (32 prompts × 8 samples, lr 1e-5, 16k rollouts), after a shared 8 SOLVE-only steps, three arms for
steps 9–24:

| Arm | Each step |
|---|---|
| A | 32 SOLVE |
| B | 24 SOLVE + 8 items made from current failures: their JUDGE item and a RECONSTRUCT item (27B as reward judge) |
| D | 24 SOLVE + 8 current failures replayed as plain SOLVE |

| SOLVE dev (200 × 4), mean pass@1 | Step 16 | Step 24 |
|---|---|---|
| Untrained 2B | 52.4 | |
| A | 55.0 | 59.9 |
| B | 59.5 | 62.1 |
| D | 60.1 | 61.1 |
| B − A | +4.5 [+0.6, +8.1] | +2.2 [−1.2, +6.0] |
| D − A | +5.1 [+1.4, +8.9] | +1.2 [−3.0, +5.5] |
| B − D | −0.6 [−4.2, +3.1] | +1.0 [−2.8, +4.9] |
| B step 16 vs A step 24, same GPU-hours | −0.4 [−4.4, +3.5] | |

**Finding:** practising current failures speeds up early gains, but by step 24 no arm differs beyond noise. Turning
failures into JUDGE / RECONSTRUCT items is no better than replaying them as SOLVE, and costs about 1.6× the GPU time.

---

## 13. Self-judge training (positive for judging, negative for SOLVE accuracy)

**Idea.** Every earlier judge learned on injected errors or other models' errors, and all were near chance on the
model's own attempts (sections 4, 9, 10). Here the judge is trained directly on the model's own attempts. The label
comes only from the answer checker (right or wrong final answer); no larger model, no human labels, no step labels.

### Data

| Item | Value |
|---|---|
| Questions | 900 SOLVE training questions the mixed model never trained on (excluding the dev slice) |
| Attempts | 4 per question by the mixed model, 16k token cap → 3,600 |
| Mixed model accuracy on them | 70.6% |
| Usable (finished, answered, verified right or verified wrong, prompt ≤ 50k characters) | 3,041: 501 wrong, 2,540 right |
| Training prompts | 1,024 (48.9% wrong), shown in the JUDGE step format |
| Prompt length | median 9,509 tokens, max 16,658 |

The plan was 1,200 questions; one node14 GPU failed with a hardware memory (ECC) error, so the last quarter was dropped.

### Training

| Setting | Value |
|---|---|
| Start | Mixed adapter (`mixed-step75`) |
| Algorithm | Dr. GRPO, 32 steps × 32 prompts × 8 samples, lr 1e-5 (5 warm-up steps) |
| Reward | 1 if the verdict (correct / incorrect) matches the checker label, else 0; cut-off answers score 0 |
| Judge answer cap | 8,192 tokens |
| Time | 3.5 h on 2 GPUs |

| Steps | Verdict reward | Answers cut off | Mean answer length |
|---|---|---|---|
| 1–4 | 39% | 24% | 4,400 |
| 5–8 | 40% | 15% | 3,660 |
| 9–12 | 52% | 4% | 2,770 |
| 13–16 | 55% | 2% | 2,280 |
| 27–28 | | 0% | about 1,450 |

### Results (judge gives 4 verdicts per attempt; the score is the share saying "incorrect")

Picking rule: group the 4 answers by value and keep the group with the largest summed judge confidence that the
answer is correct.

**Dev: 200 problems × 4 own attempts** (single attempt 69.8, best possible 86.5)

| | Untrained mixed judge | Self-judge step 16 | Self-judge step 32 |
|---|---|---|---|
| AUROC on own attempts | 0.567 | 0.619 | **0.665** |
| AUROC change vs untrained | | +0.052 [+0.009, +0.096] | **+0.098 [+0.057, +0.142]** |
| Answers with no verdict | 11.3% | 1.9% | 0.5% |
| Accuracy picking 1 of 4 | 78.5 | 78.0 | 79.5 |
| vs majority vote (77.5) | +1.0 [−1.5, +3.5] | +0.5 [−1.0, +2.5] | +2.0 [+0.5, +4.0] |

**Test: 400 problems × 4 own attempts** (step 32 fixed in advance; single attempt 67.4, best possible 82.8)

| | Untrained mixed judge | Self-judge step 32 |
|---|---|---|
| AUROC on own attempts | 0.568 | **0.665** |
| AUROC change vs untrained | | **+0.097 [+0.066, +0.128]** |
| Answers with no verdict | 10.5% | 0.8% |
| Accuracy picking 1 of 4 | 75.2 | 75.2 |
| vs majority vote (74.0) | +1.2 [−0.2, +2.8] | +1.2 [−0.5, +3.0] |

**Findings**

- **Judging own attempts improved, and replicated:** +0.098 on dev and +0.097 on test. This is the only method that
  moved own-attempt judging clearly off chance; the transplant (0.605), the condensed rewrites (0.57) and the step
  format (0.55–0.59) did not come close.
- It also learned to always give a verdict (no-verdict answers 11% → under 1%) and to answer much more briefly.
- **SOLVE accuracy did not improve:** the dev gain (+2.0) did not hold on test, where both judges pick 75.2 (+1.2 over
  majority, not significant). A better ranking of attempts did not change which answer wins.
- The judge was still improving between steps 16 and 32, and only 501 wrong attempts were available for training.

---

## 14. What it adds up to

| Input to the checker | Learned checking |
|---|---|
| Short step-numbered solutions with injected errors | Works (tutor: 72.5% exact step, mixed) |
| Real errors by other models (ProcessBench) | Partly (about half the gain; internal feature 0.80) |
| The model's own long solutions | Near chance for every off-the-shelf judge and the internal feature (0.50–0.58) |
| The model's own solutions, judge trained on them with answer-checker labels | **0.665**, replicated |

1. Checking skill learned on other people's mistakes does not transfer to the model's own mistakes; the obstacle is
   length and error type, not self-blindness.
2. Training on its own outcome-labelled attempts is a cheap fix for judging (about 14 GPU-hours, no external labels),
   but a 0.1 AUROC gain is not enough to beat majority vote at picking answers.
3. RL places the JUDGE skill in the first layers, where it can be moved by copying weights, with clean controls; it
   costs SOLVE accuracy.
4. Cross-task "transfer" to checking from RECONSTRUCT is mostly response bias.
5. No method raised SOLVE accuracy on test: hints, repair, step format, rewrites, failure-driven practice, and
   judge-based picking all stayed within noise or lost accuracy.

---

## 15. Compute

| Block | GPU-hours |
|---|---|
| Sections 2–5 (hints, tutor, drift, ProcessBench), earlier budget | 30.0 |
| Sections 6–11 and 13, 80 GPU-hour budget | about 58.6 used |
| ↳ of which self-judge (generation 2.7, failed starts 0.2, training 7.0, evaluation about 4.4) | about 14 |
| Section 12 (failure-driven pilot, separate run) | 24.8 (23.2 in arms, 1.5 failed setup) |

At most 4 GPUs ran at once throughout.

---

## 16. Where things are

| What | Path |
|---|---|
| Earlier experiments (sections 2–5) | `phase2/scripts/`, results in `phase2/results/{hint-pilot,functional,processbench}` |
| Transplant, bias analysis, error feature, own-attempt judging, step format | `phase2/next/`, results in `phase2/results/phase2b/` |
| Rewrite selection (section 11) | `phase2/next/select.py`; generated data on Turing in `phase2/runs/select/` |
| Failure-driven pilot | `phase2/failure_driven/`, results in `phase2/results/failure-driven/` |
| Self-judge | `phase2/selfjudge/` (`build.py`, `evaluate.py`, `auroc_ci.py`, `*.sbatch`); runs in `phase2/runs/selfjudge/` |
| Self-judge adapters (steps 16 and 32) | Turing: `~/anlp-project-phase2/phase2/runs/selfjudge/adapters/` |
| Trainer changes for self-judge | `src/anlp_project/rewards.py` (verdict-only JUDGE reward), `opd_train.py` / `opd.py` (`reward_judge="none"`, `prompt_max_tokens`) |
| GPU ledger | `phase2/budget/` |

## 17. Caveats

- One training run per method (one seed); Phase-1 adapters also come from single runs.
- Dev has 200 problems and test 400; differences of 1–2 points are within noise.
- ProcessBench scores use this project's prompt and temperature-1 sampling.
- Tutor wrong-question items and drift checks rely on Qwen3.8-27B judgements.
- Self-judge: the step-16 vs step-32 choice was made on dev; step 32 was fixed before test was run.
