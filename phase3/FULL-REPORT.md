# Phase 3: full report on everything run so far, and the next plan

29 October 2026. Model: Qwen3.5-2B with the `mixed-step75` LoRA adapter (from Phase 1). All GPU work ran on IIIT
Turing (node09, at most 4 L40S GPUs at once). Code: `phase3/`. Theory: `docs/research/verification-theory/`.
Paper draft: `paper/`.

---

## 1. The question

Phase 2 ended with a puzzle. Training the model to judge its own maths attempts raised its AUROC from **0.57 to
0.67**. Picking the best of 4 attempts with that judge stayed at **75.2%**, no better than majority vote, and
"flag a wrong attempt and redo it" recovered only 0.4 of the 7 points perfect flags would give.

**Phase 3 asked:**
1. Why doesn't a better judge give better answers?
2. Can we predict when judging will help?
3. Can we build something that actually beats voting at equal compute?

---

## 2. What was done (in order)

| Step | What | Output |
|---|---|---|
| 1 | **Theory, no GPU.** A small model of answer selection: question difficulty ~ Beta, a "favourite wrong answer", and a judge with leniency, a difficulty signal and a real within-question signal. 13 simulation scripts; proofs. | `docs/research/verification-theory/` |
| 2 | **Pre-registration** of question sets, sampling, judging, the primary method, the comparison and the success test, before any data. 3 deviations logged later. | `phase3/PREREGISTRATION.md` |
| 3 | **Pipeline rebuilt** (the Phase-2 code was lost): generation, step-split judging with verdict probabilities, grading, analysis. Smoke-tested. | `phase3/*.py` |
| 4 | **Generation.** 16 attempts per question for dev 200, test 400 and extra 400 (held-out training questions), plus 450 training questions. **23,200 attempts.** | `runs-out/p3-main/attempts` (Turing), `phase3/runs/main` (local) |
| 5 | **Judging.** Every answered attempt of dev/test/extra judged by the same adapter: a reasoning chain → verdict probability, plus a "direct" probability with no reasoning. Test attempts 0–3 got 4 chains each. | `…/judge` |
| 6 | **Analysis.** Stage 0 (what the judge knows), Stage 1 (selection methods at matched compute), trace features, mechanism checks, a registered prediction. | `phase3/runs/analysis/report.md`, `phase3/RESULTS.md` |
| 7 | **Stage 2: retraining the judge.** Two Dr. GRPO arms × 32 steps (Phase-2 recipe): `global` (Phase-2 replica) and `perq` (per-question balanced). Evaluation **cancelled**. | adapters in `runs-out/p3-sj2-*/adapters` |
| 8 | **Paper draft** with generated tables and figures; literature review and novelty map; experiment plan. | `paper/`, `docs/research/verification-theory/*.md` |

**Compute.** About 50 GPU-hours on Turing (the ledger shows 216 GPU-hours left of the approval). Jarvislabs: ₹61 spent;
unusable from campus (SSH blocked).

---

## 3. Results

### 3.1 The pipeline reproduces Phase 2

| | Single attempt | pass@4 | Majority@4 |
|---|---|---|---|
| Dev, Phase 3 / Phase 2 | 69.8 / 69.8 | 86.3 / 86.5 | 78.1 / 77.5 |
| Test, Phase 3 / Phase 2 | 67.0 / 67.4 | 82.8 / 82.8 | 74.9 / 74.0 |

The rebuilt pipeline matches the old one, so the new results are comparable.

### 3.2 The model predicted new data before we saw it

The model was fitted only to Phase 2's 4-attempt numbers (3 numbers → 3 parameters), then checked on new 16-attempt
data:

| Test set | Predicted | Observed |
|---|---|---|
| Majority vote, 8 attempts | 77.5 | 77.5 |
| Majority vote, 16 attempts | 78.2 | 78.7 |
| At least one right in 16 (pass@16) | 90.8 | 90.2 |
| Questions where the majority is already right (N = 4) | 71.7% | 72.3% |
| Questions with no right attempt (N = 4) | 17.2% | 17.3% |

Earlier out-of-sample checks also held:
- the share of questions always right / always wrong over 8 tries: 0.43 / 0.12 predicted, 0.39 / 0.11 observed;
- the repair gain from Phase 2's flags: +0.30 predicted, +0.38 observed.

### 3.3 Stage 0: the judge knows more than its verdicts show

On test attempts 0–3 (1,486 attempts, 4 judge chains each):

| How the judge is read | AUROC |
|---|---|
| One yes/no verdict | 0.565 |
| Share of 4 yes/no verdicts (Phase 2's method) | 0.635 |
| Verdict probability after one reasoning chain | 0.689 |
| Average probability over 4 chains | 0.694 |
| **Direct probability, no reasoning (one cheap read)** | **0.717** |

- The judge is **lenient**: it says "incorrect" only 15% of the time; d′ = 0.49.
- **Probability beats verdicts:** +0.067 [+0.047, +0.085] (4 chains) and +0.090 [+0.049, +0.130] (direct).
  Pre-registered prediction: confirmed.
- **Verdicts on one attempt stick together:** "4 of 4 incorrect" on a wrong attempt happens 4.2% of the time, against
  0.35% if the verdicts were independent (12×). Pre-registered prediction: confirmed.
- The model, fitted only to Phase 2's flag rates, predicted the hidden ("latent") AUROC as 0.715. Measured 0.69–0.72.
- **Phase 2's training "gain" (0.57 → 0.67) is reproduced in the model by a criterion shift alone:** making the judge
  say "incorrect" more often, with no better discrimination.

### 3.4 The judge is weakest exactly where picking needs it

| Set | All attempts compared (pooled) | Same question only | **Contested questions only** |
|---|---|---|---|
| Dev | 0.69 / 0.73 | 0.62 / 0.63 | 0.61 / 0.60 |
| Test | 0.68 / 0.72 | 0.61 / 0.61 | **0.51 / 0.47** |
| Extra | 0.71 / 0.75 | 0.67 / 0.66 | 0.63 / 0.64 |

Values are chain probability / direct probability. *Contested* means the attempts disagree and the right answer is not
already the clear majority; that is the only place picking can gain.

**Judge-free features** (test): length scores 0.655 pooled but 0.486 contested; "wait / actually" counts 0.648 →
0.514; guess phrases 0.656 → 0.568. Plain features match the trained Phase-2 judge's pooled AUROC (0.665) and are
useless where it matters.

98–99% of *right* attempts contain self-corrections (about 25 each; 36 in wrong ones).

**Theory (proved):** the gain from picking or repairing depends only on within-question discrimination. Any signal
that only knows "this question is hard" gives exactly zero gain.

### 3.5 Voting hits a ceiling

Test ∪ extra, 800 questions:

| Attempts per question | Majority vote | At least one right |
|---|---|---|
| 4 | 76.0 | — |
| 8 | 78.7 | — |
| 16 | **79.8** | **91.4** |

- Adaptive-consistency (the best adaptive voting baseline) reaches **79.8%** with about 10 attempts and no further.
- Picking the single attempt the judge likes most: **76.7%**, *below* majority. Predicted by the theory.
- Adding judge evidence over answer groups (all 16 attempts judged): 80.9%, but at about 20 units of compute.

### 3.6 Stage 1: contest-adaptive verification (CAV), the pre-registered test

**The procedure:**
1. Generate 4 attempts. If all agree, stop: about 50% of questions, right 99% of the time.
2. Otherwise, sample up to 16 attempts.
3. Judge only the attempts behind the 2 most common answers.
4. Pick by group size × judge confidence.

| Comparison (equal compute) | CAV | Other | Difference [95% CI] |
|---|---|---|---|
| **vs majority vote (pre-registered primary)** | 81.0 | 79.4 | **+1.6 [+0.5, +2.6]** |
| vs majority, matched decoded tokens | | | +1.4 [+0.4, +2.5] |
| vs adaptive-consistency | 81.0 | 79.8 | +1.2 [+0.05, +2.3] |
| Cheap CAV (direct probability, ≈6 units) vs majority | 79.2 | 77.9 | +1.35 [+0.84, +1.88] |

- **What the intervals mean:** one seed (one draw of attempts and judgments). Intervals are a bootstrap over the 800
  questions, with each rule averaged over 100 orderings of the cached attempts. Generation and judging seeds are
  **not** yet varied (planned).
- **Predicted before judging:** about +1.3, from the judge's dev within-question AUROC (0.62) plugged into the model.
  Observed +1.6.
- **Where the gain comes from:**
  - questions where the right answer was in the minority (10.6% of questions): +1.18 of the +1.60;
  - ties: +0.28;
  - majority already right: +0.14;
  - no right attempt: exactly 0.
- CAV is the only method above the 79.8% plateau, and it uses about 30% less compute than 16-attempt voting.

### 3.7 Things that did not work or were not finished

| Item | Result |
|---|---|
| Learned combination of judge + text features (exploratory) | Ranks better within questions (extra 0.717), but **no picking gain**. Only contested questions matter. |
| Length / self-correction mechanism (judge worse on long or self-correcting traces) | **Not supported** within 4k–16k-token traces. Reported as a null. |
| Judge retraining (Stage 2) | Trained (verdict reward 40→57% global, 48→53% perq; length 3.9k→1.2k and 4.2k→1.6k), **evaluation cancelled**. |
| Repeating with other adapters, or an external reward model | Cancelled or dropped by decision. |

### 3.8 What is new vs already published (literature review)

- **Already published:** "all-attempts AUROC misleads for picking" (Landesberg 2026, LLM judges; Bulut 2026,
  probes) and "majority vote has a ceiling" (Bay & Yearick 2026; Brown 2024).
- **Ours:**
  1. **forecasting** selection curves, judge scores and the method's gain from cheap 4-attempt numbers, checked
     prospectively;
  2. the **leniency / criterion-shift** explanation, and the collapse on **contested** questions for self-judging;
  3. **CAV** (verify only disagreements, only the top-2 answers), pre-registered and beating equal-compute voting.

---

## 4. Honest assessment

- **Strong:** the diagnosis and the predictions. Everything the model was asked to forecast held, and both
  pre-registered tests passed.
- **Weak:** the size of the gain. **+1.6 points** captures 14% of the 11.6 points between the voting plateau and the
  best possible pick. The theory says why: the 2B self-judge is near chance on contested questions (0.47–0.64). By
  the theory's own curve, more gain needs a judge with contested AUROC around 0.7 (about +3) or 0.85 (about +6).
- **Narrow:** one model, one dataset, one seed; no comparison yet with the closest published methods.

---

## 5. Next steps

### Goal 1: raise contested discrimination, and therefore the gain

| ID | Experiment | Why it should help | GPU-h |
|---|---|---|---|
| **G1** | **Pairwise judging on contested questions.** Show the judge one attempt from each of the top-2 answer groups and ask which is right; both orders; read probabilities. Use it inside CAV. | Compares the two candidates directly, which is the actual contested decision. Pairwise judging is reported to beat single-attempt judging (V1, PairJudge). About one comparison per contested question, so cheap. | 4–6 |
| **G2** | **A stronger judge** (Qwen3.5-9B) on the 2B's cached attempts: direct probability + 1 chain | Tests the prediction curve: higher contested AUROC → a predictably larger gain. Shows the gain isn't capped by the method. | 10–15 |
| **G3** | **Evaluate the per-question-trained judge** (already trained) | It was trained on contested-like questions only; it may lift contested AUROC. Also tests the criterion-shift account (global arm). | ~10 |
| G4 | Answer-level checking: ask the model to verify a *final answer* (substitute it back / re-derive), not the whole trace | Errors on contested questions are often wrong approaches, not a bad step; answer-level checks are less tied to the long trace | 4–6 |

**Decision rule:** register the predicted gain for each before running it. Keep whichever reaches contested AUROC
≥ 0.7; the method then uses that judge.

### Goal 2: make it a full paper (`docs/research/verification-theory/experiment-plan.md`)

| ID | Experiment | GPU-h |
|---|---|---|
| E1 | Second model as solver + self-judge (dev + test × 16) | 18–22 |
| E2 | Second benchmark (MATH-500 / Olympiad subset) × 8 | 6–8 |
| E3 | 2 extra seeds of the primary test experiment | ~24 |
| E4 | Closest baselines, cheap: DeepConf, self-certainty, CISC (prefill over cached attempts) | 6–9 |
| E6 | V1-style pairwise baseline (shares code with G1) | (in G1) |
| CPU | CISC-P(True), early-stopping, adaptive-consistency variants; each signal natively vs inside CAV; predicted-vs-observed gain across all conditions; swapped tuning; worst case vs majority | 0 |

### Suggested order

1. **CPU now:** the free baselines (A1), robustness checks (A4), the leniency refit (A6).
2. **G1 + G3** in parallel (4 GPUs, about 4 hours): the quickest shots at a bigger gain.
3. **G2** (9B judge): the cleanest test of "gain follows contested AUROC".
4. Pick the best judge → rerun the primary comparison with it (pre-registered).
5. **E1, E2, E3, E4** with the chosen judge; then the headline figure (predicted vs observed gain across all
   conditions).
6. Final paper.

**Estimated total:** Goal 1 about 30–40 GPU-hours; Goal 2 about 55–65. That fits the 216 GPU-hours left; about
1.5–2 days of wall time at 4 GPUs.

---

## Addendum (29 October 2026, CPU analyses and the new plan)

See `runs/cpu_analyses.md` and `PLAN-60h.md`.
- A difficulty-only predictor reaches pooled AUROC 0.906, against 0.73 for the judge.
- On contested questions the judge separates right answers from the solver's own attractor wrong answer at only 0.55
  (0.64–0.68 against one-off wrong answers).
- Within-group correlation of the direct score is 0.75 for wrong groups.
- Early-stopping self-consistency (window 2) reaches 79.1% at 4.2 units (+2.8 over majority at that cost), a strong
  low-budget baseline.

The next 60 GPU-hours test which **independent** evidence (executable checks, backward checks, pairwise, answer-only,
a 9B checker, a 9B jury) breaks this shared bias.
