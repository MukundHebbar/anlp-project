# Phase 2: where RL-trained task skills live, and whether they work on the model's own solutions

Qwen3.5-2B, LoRA adapters trained by Dr. GRPO (Phase 1). This report collects the Phase-2 results worth reporting,
positive and negative. A complete log of every run, including minor ones, is in `phase2-all-runs-log.md`.

## Summary

| # | Finding | Type | Key number |
|---|---|---|---|
| 1 | The checking skill learned by JUDGE RL sits in the **first layers (0–5, mostly 0–3)** and can be moved between adapters by copying weights, with no training | Positive, causal | SOLVE + JUDGE layers 0–5: **+15.3 F1** on ProcessBench; all controls ≈ 0 |
| 2 | How well that skill is used sits in **layers 6–23**, and only layers trained with checking data help | Positive, causal | JUDGE + mixed layers 6–23: **+8.6 F1** on the JUDGE test set; SOLVE's layers 6–23: −1.9 |
| 3 | Swapping or adding layers raises JUDGE only **to the mixed model's level, never beyond** | Informative negative | Best swap vs mixed: +0.9 (n.s.); mixed + (JUDGE − SOLVE): −0.6 (n.s.) |
| 4 | Majority voting over 8 answers is the largest JUDGE gain available | Positive | Mixed: 76.7 → **87.9 F1** |
| 5 | RECONSTRUCT's apparent transfer to checking is mostly **response bias**, not skill | Positive, explanatory | Sensitivity d′ 1.05 (SOLVE 1.17), most "wrong"-leaning bias (c = −0.46) |
| 6 | Learned checking works on short curated errors, partly on real errors, and **fails on the model's own solutions**: verbal judges and an internal error feature alike | Positive → negative | Error feature AUROC 0.80 on ProcessBench → 0.50 on own solutions |
| 7 | The failure is about **length and error type, not self-blindness** | Explanatory | Others' attempts are no easier (0.55 vs 0.58); condensed attempts easier (0.67) |
| 8 | Training the judge on its **own attempts, labelled only by the answer key**, fixes judging | Positive, replicated | Own-attempt AUROC 0.568 → **0.665** on test (+0.097 [+0.066, +0.128]) |
| 9 | Better judging **did not raise SOLVE accuracy**; nor did hints, repair or failure-driven practice | Informative negative | Judge-picked answers 75.2 vs majority vote 74.0 (n.s.) |
| 10 | RECONSTRUCT adds a useful second check for tutoring: it catches solutions that answer the wrong question | Positive, application | Wrong-question solutions caught: 73.6% → **81.3%** at 5% false alarms |

---

## 1. Setup and terms

| Term | Meaning |
|---|---|
| **SOLVE** | Task: solve a maths problem |
| **JUDGE** | Task: given a step-numbered solution, say whether it is correct and, if not, which step is the first wrong one |
| **RECONSTRUCT** | Task: recover the question from its answer and some clues |
| SOLVE / JUDGE / RECONSTRUCT adapter | Phase-1 LoRA adapter (rank 64, all attention and MLP projections, all 24 layers) trained by Dr. GRPO on that task only |
| Mixed adapter | Phase-1 adapter trained on all three tasks; the best Phase-1 model |
| Untrained | Qwen3.5-2B with no adapter |
| Own attempts | Solutions written by the mixed model, then shown to a judge |
| F1 (error-finding) | Harmonic mean of (a) naming the exact first wrong step on wrong solutions and (b) saying "correct" on correct solutions |
| AUROC | Chance that a judge rates a random wrong solution as more suspicious than a random right one (0.5 = guessing) |
| [a, b] | 95% paired bootstrap interval (2,000 resamples over items or problems); n.s. = interval includes 0 |

| Data | Size | Use |
|---|---|---|
| JUDGE test set (Phase-1 split) | 400 step-numbered solutions: 200 correct, 200 with one injected error | Error-finding on curated errors |
| ProcessBench (Qwen) | 3,400 solutions written by 12 other models, first wrong step labelled by humans | Error-finding on real errors |
| SOLVE dev slice / SOLVE test | 200 / 400 problems (FINAL-v3) | Solving accuracy; own attempts |

All models use the same prompts and temperature-1 sampling. Answers are graded with the repository's answer checker.

---

## 2. Where the skills live: layer transplants

### 2.1 Method

All adapters have the same shape, so a **hybrid** can be built without training:

1. Take one adapter as the **receiver** (e.g. SOLVE) and another as the **donor** (e.g. JUDGE).
2. For each layer in a chosen range (e.g. 0–5), replace all of the receiver's LoRA weights in that layer (attention
   and MLP) with the donor's weights for the same layer.
3. Evaluate the result like any other model.

Naming: "SOLVE + JUDGE layers 0–5" is the SOLVE adapter with layers 0–5 taken from JUDGE.

| Control | How it is built | What it rules out |
|---|---|---|
| Reset | Layers 0–5 set back to the untrained model (LoRA update zeroed) | That simply removing SOLVE's early update helps |
| Wrong place | Slots 0–5 receive JUDGE's layers 16–21 (same layer types, same size of change) | That any JUDGE update of that size helps, wherever it sits |
| Wrong donor | Layers 0–5 from RECONSTRUCT | That any trained early layers help |
| Reverse | JUDGE adapter with SOLVE's layers 0–5 | Whether removing the layers removes the skill |

### 2.2 The checking skill is in the first layers

Change in error-finding F1 relative to the plain SOLVE adapter (one answer per item).

| SOLVE adapter with … | ProcessBench F1 (GSM8K + MATH, 1,400) | JUDGE test F1 |
|---|---|---|
| **JUDGE layers 0–5** | **+15.3 [+11.5, +19.2]** | **+16.1 [+10.2, +22.4]** |
| JUDGE layers 0–3 | +11.5 [+7.5, +15.5] | +8.9 [+2.1, +15.8] |
| JUDGE single layer 0 / 1 / 2 / 3 / 4 / 5 | +4.7 / +5.4 / +2.5 / +3.2 / −1.5 / +1.7 | |
| JUDGE layers 6–11 / 12–17 / 18–23 | +6.8 / +2.2 / +4.5 | +3.3 / +3.5 / −1.8 |
| All 24 layers from JUDGE (= the JUDGE adapter) | +10.7 [+6.8, +14.9] | +14.0 [+7.9, +20.8] |
| Mixed layers 0–5 | +12.6 [+8.7, +16.4] | +16.6 [+10.0, +22.9] |
| *Control: reset layers 0–5* | +0.4 [−3.6, +4.5] | −3.7 |
| *Control: JUDGE's layers 16–21 in slots 0–5* | −2.7 [−6.7, +1.3] | −4.0 |
| *Control: RECONSTRUCT layers 0–5* | −2.0 [−6.3, +2.1] | −2.3 |

| Removing early layers (replacing layers 0–5 with SOLVE's) | ProcessBench F1 change |
|---|---|
| From the JUDGE adapter | Gain over SOLVE falls from +10.7 to +1.6: the skill is gone |
| From the mixed adapter | −4.4 [−7.6, −1.2] vs mixed: a partial loss |

- **Causal in both directions:** adding JUDGE's layers 0–5 gives the skill; removing them takes it away; all three
  controls are null.
- **Not explained by where the weights changed most:** JUDGE's update is spread evenly over depth (each 6-layer block
  holds 24–26% of it).
- **Roughly additive** over layers 0–3.
- **Specialist vs mixed training:** JUDGE RL concentrates the skill early; mixed training spreads it (removing mixed's
  early layers costs much less).
- The composite judges better than the JUDGE adapter itself (+15.3 vs +10.7): JUDGE's early layers work better with
  SOLVE's later layers than with JUDGE's own. Among flagged solutions, it names the exact step 59.3% of the time
  (SOLVE 47.5%, JUDGE 48.4%, mixed 61.0%).

Generalization to harder, unseen sets, and the cost to solving (SOLVE test: 400 problems × 4 answers):

| Adapter | OlympiadBench F1 | Omni-MATH F1 | SOLVE test accuracy (change vs SOLVE) |
|---|---|---|---|
| SOLVE | 44.2 | 35.0 | 66.6 |
| **SOLVE + JUDGE layers 0–5** | **53.1** | **46.6** | 62.7 (**−3.9 [−6.4, −1.4]**) |
| JUDGE | 54.0 | 42.2 | 49.8 (−16.8 [−19.7, −13.9]) |
| Mixed | 53.2 | 43.9 | 66.5 (−0.1 [−2.6, +2.3]) |

The composite is a good judge but not a usable solver: JUDGE's early layers cost SOLVE accuracy.

### 2.3 Can layer swaps improve the JUDGE adapter itself?

Here JUDGE keeps its first layers and receives later layers from another adapter. Single-answer comparisons on 400
items proved too noisy (the same adapter scored 71.3 and 66.6 in two runs), so every adapter answered each JUDGE test
item **8 times**. F1 pools all answers; the bootstrap resamples items with their 8 answers.

| Adapter | JUDGE test F1 | vs JUDGE | vs mixed | Exact wrong step found | Correct kept correct | No verdict |
|---|---|---|---|---|---|---|
| **JUDGE + mixed layers 6–23** (= mixed with JUDGE's layers 0–5) | **77.5** | **+8.6 [+6.1, +11.1]** | +0.9 [−1.0, +2.9] | 68.6% | 89.1% | 4.8% |
| Mixed | 76.7 | +7.8 [+4.8, +10.8] | — | 67.2% | 89.1% | 5.7% |
| JUDGE + mixed layers 12–23 | 73.6 | +4.7 [+2.7, +6.7] | −3.1 [−5.6, −0.6] | 63.2% | 87.9% | 4.3% |
| JUDGE | 68.9 | — | −7.8 [−10.8, −4.8] | 57.3% | 86.4% | 3.0% |
| JUDGE + SOLVE layers 6–23 | 67.0 | −1.9 [−4.4, +0.7] | −9.6 [−11.8, −7.4] | 58.4% | 78.8% | 13.1% |

- **A training-free swap raises JUDGE by 8.6 F1**, mainly by naming the exact wrong step more often (57.3% → 68.6%).
- **Mixed's advantage over JUDGE sits in layers 6–23**: about half in 12–23, the rest in 6–11.
- **Only later layers trained with checking data help.** SOLVE's later layers find the step as often as JUDGE's own
  but fail to give a verdict four times as often and flag more correct solutions.
- **JUDGE's and mixed's first layers are interchangeable** for checking.
- **The swap only ties mixed.**

### 2.4 Adding instead of replacing

Since mixed's first layers already hold the skill, replacing them cannot add anything. We instead **added** JUDGE's
checking-specific update to mixed's own, in layers 0–5: mixed + (JUDGE − SOLVE). Subtracting SOLVE's update
removes the part of JUDGE's update that any maths GRPO run produces, so the generic part is not added twice
(task arithmetic). The combination was baked into the model weights and scored on the first 300 JUDGE test items,
8 answers each, against the other runs on the same items.

| Model (first 300 items) | JUDGE test F1 | Change (95% range) |
|---|---|---|
| Mixed + (JUDGE − SOLVE) in layers 0–5 | 77.1 | vs mixed: **−0.6 [−2.8, +1.7]**; vs JUDGE: +8.2 [+5.0, +11.2] |
| Mixed | 77.7 | — |

Adding the extra checking update neither helps nor disrupts the network. Every swap and addition lands at the mixed
model's level.

### 2.5 Skill map

| Layers | Checking (JUDGE) | Solving (SOLVE) |
|---|---|---|
| 0–3 | **Core checking skill** created by JUDGE RL (+11.5 F1 when moved; single layers +2.5 to +5.4, roughly additive). JUDGE's and mixed's versions interchangeable | JUDGE's early layers hurt solving: SOLVE + JUDGE layers 0–5 loses 3.9 points; restoring SOLVE's layers 0–5 in JUDGE raises SOLVE dev accuracy 56.2 → 62.4 |
| 4–5 | Small further gain (+15.3 for 0–5 vs +11.5 for 0–3) | |
| 6–11 | **Use of the skill** (naming the step, giving a verdict): mixed's 6–11 add about half of its advantage over JUDGE | Replacing SOLVE's 6–11 with JUDGE's: no change in SOLVE dev accuracy (68.8 vs 68.5) |
| 12–23 | Use of the skill, continued (mixed's 12–23: +4.7). The internal error feature (section 4.3) is read out here, and exists before any training | Replacing SOLVE's 12–17 or 18–23 with JUDGE's: no loss in SOLVE dev accuracy (73.2 / 71.8, 2 answers per problem, noisy) |

The solving side is less certain: SOLVE accuracy was measured for few hybrids, with 2–4 answers per problem.

### 2.6 Relation to prior work

Bandarkar & Peng (MRL 2025) swap the first and last layers of a language expert into a maths expert and find
swapping beats training on mixed data by about 1 point.

| | Bandarkar & Peng | This project |
|---|---|---|
| Skills combined | Language vs maths | Two functional skills on the same maths (checking vs solving) |
| Training | Supervised fine-tuning, 7–8B | RL (Dr. GRPO), LoRA, 2B |
| Which layers | Chosen from prior interpretability work | Found by sweeping blocks and single layers, with controls |
| Swapping vs mixed training | Swapping better (about +1) | Swapping ties mixed training on JUDGE (+0.9, n.s.) and costs SOLVE accuracy |

---

## 3. What "transfer" between tasks means: bias vs skill

Each model's JUDGE verdicts split into sensitivity d′ (separating wrong from right solutions) and criterion c
(negative = quick to say "wrong"):

| Model | JUDGE test d′ / c | ProcessBench d′ / c | ProcessBench exact step, among flagged |
|---|---|---|---|
| Untrained | 0.73 / −0.04 | 2.13 / +0.25 | 49.7% |
| SOLVE | 1.17 / +0.13 | 2.35 / +0.40 | 55.0% |
| JUDGE | 1.64 / +0.30 | 2.50 / +0.68 | 52.9% |
| RECONSTRUCT | 1.05 / **−0.46** | 2.25 / **−0.18** | 54.4% |
| Mixed | **2.32** / +0.27 | **2.63** / +0.45 | **61.1%** |

- RECONSTRUCT training matched JUDGE training on ProcessBench F1 (55.2 vs 54.6) by becoming **suspicious**, not
  discerning: its sensitivity is at SOLVE's level.
- Only mixed training raises sensitivity substantially.
- On real errors the untrained model already discriminates fairly well; most of the trained gain is producing a usable
  verdict, shifting the bias, and locating the step.

---

## 4. Does learned checking work where it matters?

### 4.1 On curated errors: a tutor (positive)

Students make two kinds of mistake: a **false step** (JUDGE finds it) and a **wrong question** (every line is right
but solves a slightly different problem, e.g. divisors of k instead of k + 1). For the second, RECONSTRUCT rebuilds
the question the work answers and Qwen3.8-27B compares it with the one set. Test set: 200 correct and 200 false-step
solutions (JUDGE test set) plus 102 wrong-question solutions (one detail of a correct solution's problem changed).

| Measure | Specialists | Mixed |
|---|---|---|
| False-step solutions caught (exact step named) | 64.5% (55.5%) | 80.5% (72.5%) |
| Correct solutions wrongly flagged by JUDGE | 4.5% | 4.0% |
| Wrong-question solutions caught by JUDGE alone | 69.6% | 73.6% |
| … with RECONSTRUCT added, threshold for 5% false alarms | **78.2%** | **81.3%** |
| … with RECONSTRUCT added, threshold for 10% false alarms | **83.1%** | **83.5%** |
| Correct solutions flagged with RECONSTRUCT added (5% / 10% threshold) | 8.8% / 15.2% | 10.0% / 14.2% |

Thresholds are chosen on one half of the solutions and measured on the other (50 random splits, both directions).
Caveat: the wrong-question solutions were made by the 27B, not by students.

### 4.2 On real errors: ProcessBench (partly)

| Model | Injected errors (JUDGE test F1) | Real errors (ProcessBench F1, all 4 subsets) |
|---|---|---|
| Untrained 2B | 44.7 | 41.1 |
| SOLVE | 52.0 | 45.5 |
| JUDGE | 68.9 | 54.6 |
| RECONSTRUCT | 50.4 | 55.2 |
| Mixed | 79.5 | 59.8 |
| Qwen3.5-9B (reference) | 84.1 | 74.5 |

About half of the trained gain survives on real errors (mixed: +34.8 → +18.7 over untrained).

### 4.3 On the model's own solutions: failure (negative)

**Verbal judging.** The mixed model made 4 attempts at each of 200 unseen problems (800 attempts, 242 wrong); JUDGE
checked each one, and flagged attempts were regenerated from the flag.

| Checker on own attempts | Flags wrong attempts | Flags correct attempts | AUROC |
|---|---|---|---|
| JUDGE adapter | 4.1% | 2.7% | 0.51 |
| Mixed as judge | 7.4% | 2.2% | 0.53 |

| Repair rule | SOLVE accuracy |
|---|---|
| None | 69.75% |
| Regenerate where the judge flagged | 70.13% |
| Regenerate with perfect flags (upper bound) | 76.75% |

Repair would be worth about 7 points, but the judges cannot find the wrong attempts. A RECONSTRUCT-based check for
"drifting onto a different problem" was also near chance (AUROC 0.38–0.44); only 1 wrong attempt drifted without a
false step.

**An internal error feature.** A crosscoder (8,192 shared features) on the residual streams of the untrained and
mixed models:

| Result | Value |
|---|---|
| Features specific to either model (layers 12, 18) | None: GRPO reuses existing features |
| Layer-18 feature flagging the first wrong step, held-out ProcessBench AUROC | **0.80** |
| … controlling for step position / excluding final steps / within wrong solutions only | 0.80 / 0.80 / 0.80 |
| … on OlympiadBench + Omni-MATH (layer 12) / synthetic JUDGE set | 0.73 / 0.74 |
| **… on solutions freshly sampled from our models** | **0.50–0.53** |

The error information exists inside the model, robustly, on curated errors, and vanishes on the model's own
solutions, exactly where verbal judging fails.

### 4.4 Why: length and error type, not self-blindness

AUROC of the JUDGE adapter / mixed as judge, 200 dev problems × 4 attempts:

| Attempts judged | Mean length (tokens) | AUROC |
|---|---|---|
| Own (mixed model) | 6,317 | 0.58 / 0.54 |
| Untrained 2B's | 4,662 | 0.55 / 0.49 |
| Qwen3.5-9B's | 1,902 | 0.63 / 0.59 |
| Own, condensed to 6 steps by the 9B | 482 | 0.67 / 0.59 |

Others' attempts are no easier to judge, so the model is not blind to its own mistakes. Short attempts are easier.
Curated error sets (short, one clean error) do not resemble the model's own failures (long, unstructured).

### 4.5 The fix: train the judge on its own attempts (positive, replicated)

| Step | Detail |
|---|---|
| Data | 900 SOLVE training questions the mixed model had not trained on; 4 attempts each (3,600); labelled right or wrong **only by the answer checker**; 1,024 prompts, 49% wrong |
| Training | From the mixed adapter; Dr. GRPO, 32 steps × 32 prompts × 8 samples, lr 1e-5; reward 1 if the verdict (correct / incorrect) matches the label |
| Cost | About 14 GPU-hours in total (generation, training, evaluation); no larger model, no human or step labels |

| Training steps | Verdict reward | Answers cut off at 8,192 tokens | Mean answer length |
|---|---|---|---|
| 1–4 | 39% | 24% | 4,400 |
| 9–12 | 52% | 4% | 2,770 |
| 13–16 | 55% | 2% | 2,280 |

Evaluation on own attempts (4 verdicts per attempt; score = share saying "incorrect"). Step 32 was chosen on dev and
fixed before test.

| | Dev: untrained judge | Dev: trained (step 32) | Test: untrained judge | Test: trained (step 32) |
|---|---|---|---|---|
| AUROC on own attempts | 0.567 | **0.665** | 0.568 | **0.665** |
| Change | | +0.098 [+0.057, +0.142] | | **+0.097 [+0.066, +0.128]** |
| Answers with no verdict | 11.3% | 0.5% | 10.5% | 0.8% |

This is the only method that moved own-attempt judging clearly off chance. Transplanted layers (0.605), condensed
same-model rewrites (0.57) and writing in numbered steps (0.55–0.59) did not.

### 4.6 Majority voting for JUDGE (positive)

Each adapter answered every JUDGE test item 8 times (section 2.3). Taking each item's most common answer:

| Adapter | F1, one answer (average of 8) | F1, majority of 8 |
|---|---|---|
| **Mixed** | 76.7 | **87.9** |
| JUDGE + mixed layers 6–23 | 77.5 | 86.6 (vs mixed −1.3 [−4.2, +1.6]) |
| JUDGE + SOLVE layers 6–23 | 67.0 | 84.2 (vs JUDGE +6.1 [+2.1, +10.4]) |
| JUDGE + mixed layers 12–23 | 73.6 | 81.3 |
| JUDGE | 68.9 | 78.1 |

- Voting adds about 10 F1 for mixed (+10.2 [+6.9, +13.9] over a single answer).
- Voting changes the ranking: JUDGE + SOLVE layers 6–23 is the weakest single-answer judge but clearly beats JUDGE
  under voting. Its single answers often give no verdict, but its committed answers are usually right.
- Pooling mixed's and the best swap's answers (16 votes) gives 88.6, not significantly above mixed alone.

---

## 5. Attempts to raise SOLVE accuracy (informative negatives)

| Attempt | Idea | Result | Why it failed |
|---|---|---|---|
| Hints for always-wrong problems | 11% of GRPO problems are always wrong; JUDGE / RECONSTRUCT write hints so they become learnable | No hint beat "an earlier attempt got X, which is wrong" (7 vs 6 correct of 184 retries; RECONSTRUCT hint 2; JUDGE hint 0 of 40). JUDGE found a usable wrong step in 0 of 39 failed attempts | Same-size specialists share the learner's blind spot |
| Failure-driven GRPO | Turn current GRPO failures into JUDGE / RECONSTRUCT training items instead of replaying them as SOLVE | Step 24: converting vs replaying +1.0 [−2.8, +4.9]; both vs plain SOLVE n.s. Replaying helps early (step 16: +5.1 [+1.4, +8.9]) | Converting costs 1.6× the GPU time for no gain |
| Judge picks the answer (self-trained judge) | Pick among 4 answers by the trained judge's confidence | Test: 75.2 vs majority vote 74.0, +1.2 [−0.5, +3.0] (dev had shown +2.0 [+0.5, +4.0]) | A 0.1 AUROC gain does not overturn a wrong majority |
| Judge on short rewrites | The model rewrites its own attempts briefly before judging | Dev: 78.0 vs majority 77.5, not significant; 30% of rewrites change the answer | Rewriting is lossy |
| Solve in numbered steps | Make own attempts look like JUDGE inputs | SOLVE accuracy −6 points (69.75 → 63.75); judging still near chance | Format costs more than it gains |
| Repair flagged attempts | Regenerate from the judge's flag | 70.13 vs 69.75 | Judge cannot find the wrong attempts (section 4.3) |

---

## 6. Conclusions

1. **Skills learned by RL are localized and movable.** JUDGE RL builds its checking skill in layers 0–3; copying those
   layers into another adapter transfers it, with clean controls. How well the skill is used sits in layers 6–23 and
   depends on whether those layers saw checking data.
2. **Weight surgery reaches but does not exceed joint training.** Every swap or addition that improves JUDGE lands at
   the mixed adapter's level; transplanting into SOLVE costs solving accuracy. Inference-time voting gives a larger
   gain (+10 F1) than any weight surgery.
3. **Cross-task transfer can be mostly bias.** RECONSTRUCT training "transfers" to checking by making the model
   suspicious, not by improving discrimination.
4. **Learned checking does not transfer to the model's own solutions,** for verbal judging and for an internal
   feature alike. The cause is the length and kind of errors, not self-blindness.
5. **Outcome-labelled self-training fixes judging cheaply** (AUROC +0.097 on test, replicated), but the improvement is
   too small to raise SOLVE accuracy through answer selection.

## 7. Limitations

- One training run (seed) per adapter; all Phase-1 adapters are single runs with somewhat different recipes.
- Section 2.2 uses one answer per item (repeat runs differed by up to 4.7 F1 on 400 items); sections 2.3, 2.4 and 4.6
  use 8 answers per item. Layer swaps into JUDGE were scored on the JUDGE test set only; the addition experiment
  (2.4) covered 300 of 400 items and used weights merged in bfloat16.
- SOLVE accuracy was measured for few hybrids and with 2–4 answers per problem.
- ProcessBench scores use this project's prompt and temperature-1 sampling and are not comparable with published ones.
- Tutor wrong-question items and drift checks rely on Qwen3.8-27B judgements.
- Dev sets have 200 problems; differences of 1–2 points are within noise.

## 8. Compute and code

About 99 GPU-hours for the experiments in this report, plus 25 for the failure-driven GRPO pilot (at most 4 GPUs at a time).

| What | Code | Results |
|---|---|---|
| Layer transplants (2.2) | `phase2/next/transplant.py`, `transplant_ci.py` | `phase2/results/phase2b/transplant*` |
| Swaps and additions into JUDGE, voting (2.3, 2.4, 4.6) | `transplant.py` (`--judge-samples`), `transplant4.sbatch`, `merge_variant.py`, `judge_eval_model.py`, `judge_swap_report.py` | `phase2/runs/transplant4/` |
| Bias vs skill (3) | `phase2/next/sdt.py` | `phase2/results/sdt.json` |
| Tutor, self-checking solver, ProcessBench, hints (4.1–4.3, 5) | `phase2/scripts/` | `phase2/results/{functional,processbench,hint-pilot}` |
| Error feature, length analysis (4.3, 4.4) | `phase2/next/crosscoder.py`, `feature_check.py`, `crossjudge.py` | `phase2/results/phase2b/` |
| Self-trained judge (4.5) | `phase2/selfjudge/` | `phase2/runs/selfjudge/` |
| Failure-driven GRPO (5) | `phase2/failure_driven/` | `phase2/results/failure-driven/` |
