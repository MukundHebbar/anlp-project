# Paper plan: from `theory-and-plan.md` to a paper

October 2026. Format: ACL style (the template in `docs/reports/mid-submission/source/`): 8 pages plus references and an unlimited appendix.
Status markers: ✅ done (proof, model or Phase-2 data), 🧪 needs a Stage 0–2 run, ✂️ appendix candidate.

---

## 1. The pitch (one paragraph)

Training a 2B model to judge its own maths attempts raised AUROC from 0.57 to 0.67, yet picking among its answers did
not improve. We show this is what the mathematics predicts, and that three measurement illusions hide what a
self-verifier can and cannot do:

1. **Leniency.** A judge that almost always says "correct" looks near chance under sampled verdicts even when its
   underlying score discriminates.
2. **Between-question AUROC.** 99.9% of AUROC pairs compare different questions, while picking and repair use only
   within-question information (an exact invariance theorem).
3. **The wrong compute regime.** Majority voting saturates. Verification cannot beat compute-matched majority before
   that point and can after it.

A small model with five parameters reproduces the measured numbers. It also predicts a simple system, contest-adaptive
verification, that beats compute-matched majority with no extra training.

**Working titles** (pick after Stage 1):

- *Better Judges, Same Answers: When Self-Verification Can and Cannot Improve Mathematical Reasoning*
- *Three Illusions in Measuring LLM Self-Verification*
- *Verification Pays After Consistency Saturates*

---

## 2. Closest papers, and what to borrow from each

| Archetype | Paper | What it does | Borrow for our paper |
|---|---|---|---|
| **Puzzle → simple distributional model → explanation** | [Schaeffer et al., *How Do Large Language Monkeys Get Their Power (Laws)?*, ICML 2025 (oral)](https://arxiv.org/abs/2502.17578) | Per-problem success is exponential in attempts, yet aggregate scaling is a power law. A Beta-Binomial distribution of per-problem success explains it. | **Our closest template.** Same move: Beta-distributed per-question solve rates explain an aggregate puzzle. Open with the puzzle, give the model, show it reproduces the numbers, then show what it predicts. |
| **Theory of voting with mixed difficulty** | [Chen et al., *Are More LLM Calls All You Need?*, NeurIPS 2024](https://arxiv.org/abs/2403.02419) | Voting accuracy can rise then fall with more calls, because easy and hard queries respond differently. An analytic model predicts the best number of calls. | Framing for R4/R5: an analytic scaling model of vote + verifier systems, validated on data, giving a compute-optimal operating point. |
| **One quantity governs self-improvement** | [Song et al., *Mind the Gap*, ICLR 2025 (oral)](https://arxiv.org/abs/2412.02674) | Formalizes the generation–verification gap and shows it governs self-improvement. | Make **within-question (contested) discrimination** our single governing quantity. The invariance theorem is what justifies it. |
| **Imperfect-verifier ceiling** | [Stroebl et al., *The Limits of Inference Scaling Through Resampling*, ICLR 2026](https://arxiv.org/abs/2411.17501) | Verifier false positives cap resampling at any compute. | A bound plus compute-matched plots. Contrast: argmax is capped, but log-odds aggregation is consistent (R4). |
| **Critical / negative framing on self-checking** | [Huang et al., *LLMs Cannot Self-Correct Reasoning Yet*, ICLR 2024](https://arxiv.org/abs/2310.01798); [Stechly et al., *Self-Verification Limitations*, ICLR 2025](https://arxiv.org/abs/2402.08115) | Careful claim discipline showing reported self-correction gains are artifacts. | The tone for Phase-2 negatives, with a twist: we argue self-verification is *under*-measured (R0), not just weak. |
| **Measurement critique** | [Bulut, *It's the Problem, Not the Path*, arXiv 2609.03436](https://arxiv.org/abs/2609.03436); [Miller, *Adding Error Bars to Evals*, arXiv 2411.00640](https://arxiv.org/abs/2411.00640) | Pooled vs within-problem AUROC for probes; paired SEs and power analysis for evals. | Cite as prior work for R1. Use Miller's statistics conventions (clustered and paired SEs, power analysis) throughout. |
| **Judges through signal detection theory** | [*LLMs as Signal Detectors*, arXiv 2603.14893](https://arxiv.org/pdf/2603.14893); [*Beyond Accuracy: procedural traces shift the decision criterion*, arXiv 2609.18204](https://arxiv.org/pdf/2609.18204); [*LLM Judges Have Dark Current*, arXiv 2606.15610](https://arxiv.org/abs/2606.15610) (all preprints) | Split judge accuracy into sensitivity d′ and criterion c, and show prompts and traces move the criterion. | Required prior work for R0. Our addition: verdict *sampling* turns leniency into a near-chance AUROC, and a criterion shift alone reproduces a training "gain". |
| **Methods to position CAV against** | [Aggarwal et al., *Adaptive-Consistency*, EMNLP 2023](https://arxiv.org/abs/2305.11860); [Snell et al., *Scaling Test-Time Compute Optimally*, 2024](https://arxiv.org/abs/2408.03314); [Weaver, NeurIPS 2025](https://scalingintelligence.stanford.edu/pubs/weaver); [Kadavath et al., *Language Models (Mostly) Know What They Know*, 2022](https://arxiv.org/abs/2207.05221) | Adaptive stopping; difficulty-adaptive test-time compute; weighting weak verifiers; reading P(True) from token probabilities. | Baselines and related work. Adaptive-consistency is the must-beat baseline: CAV must win at equal cost, not just beat fixed-N majority. |

The roadmap's direct competitors (STV, V1, PairJudge, Generative Verifiers, Variation in Verification) belong in
related work. They are method papers; ours is a diagnosis paper with a method that follows from it.

**Recommended framing: Schaeffer-style puzzle → model → predictions, with Song-style "one governing quantity".** The
Phase-2 negatives become the motivating evidence (Huang/Stechly tone). CAV is the payoff (Chen/Stroebl-style
compute-matched analysis).

---

## 3. Three framing options and when to choose each

| Option | Headline | Needs | Choose if |
|---|---|---|---|
| **A. Diagnosis + method (recommended)** | Three illusions, an invariance theorem, and CAV that beats compute-matched majority | Stage 0 confirms R0 or R1; Stage 1 gives a significant gain | Stage 1 CI excludes 0 |
| B. Pure diagnosis | Three illusions plus predictions verified in Stage 0; CAV only in simulation | Stage 0 only | Stage 1 gain is within noise |
| C. Method-first | CAV (and the v2 judge) as a test-time scaling method, with the theory as justification | Strong Stage 1 and 2 results on two models | Gains ≥ 4 points on two solver models |

**Decision points:**

- After Stage 0: if P-0a fails (probability scoring stays near 0.57), drop R0 from the headline. The paper then rests
  on R1–R5.
- After Stage 1: choose A or B.
- C needs a second model; do not plan for it unless Stage 1 is strong.

---

## 4. Contributions (draft, Option A)

1. **A model of self-verification for answer selection** (Beta solve rates, attractor wrong answers, a latent judge).
   It reproduces Phase-2 numbers it was not fitted to: the 8-try shares, the repair gain, and the 4-verdict AUROC.
2. **Three measurement illusions**, each with a proof or closed form:
   - (i) leniency under verdict sampling (R0);
   - (ii) global AUROC is between-question, and selection/repair gains are invariant to between-question information
     (Δ = −E_x[Cov(f, Z | x)]);
   - (iii) the N = 4 headroom is mostly ties, with a closed-form tie gain, and is concentrated on hard questions.
3. **When verification pays.** Majority saturates at P(right answer is the mode). Log-odds aggregation is consistent;
   argmax is not. Compute-matched, verification loses before saturation and wins after.
4. **Contest-adaptive verification**: judge only contested questions' top-2 answer groups with probability scoring.
   🧪 +X points over compute-matched majority and adaptive-consistency on N questions.
5. (If Stage 2 runs) **Training for within-question discrimination**: per-question balance removes a provable
   pointwise–selection misalignment. 🧪 Within-question AUROC +Y, while global AUROC falls.

---

## 5. Outline with page budget (8 pages)

| § | Content | Pages | Material | Status |
|---|---|---|---|---|
| 1 | **Introduction.** The puzzle in three numbers (0.57 → 0.67 AUROC, 75.2 → 75.2 picking, 7 → 0.4 repair); three illusions; contributions. **Figure 1 (teaser):** one latent judge reproducing 0.526 / 0.568 / 0.665 by moving only its criterion | 1.0 | R0, Phase-2 §4/§13 | ✅ figure to make |
| 2 | **Setup.** Tasks, model (Qwen3.5-2B mixed adapter), data splits, the Phase-2 measurements | 0.5 | Phase-2 report | ✅ |
| 3 | **A model of selection with a self-verifier.** Solver model, judge model, calibration. **Table 1: model vs Phase-2** (fitted rows marked; out-of-sample rows: 8-try shares, repair +0.30 vs +0.38, 4-verdict 0.568) | 1.0 | `m1`, `m2`, `m4`, `m10` | ✅ |
| 4 | **Three illusions.** 4.1 Leniency and verdict sampling (R0, + Stage-0 verification of P-0a/b/c). 4.2 Global vs within AUROC; invariance theorem (Fig: current `fig1`). 4.3 Headroom anatomy; closed-form tie gain; contested AUROC (Fig: `fig5`) | 2.0 | R0–R3 | ✅ theory, 🧪 Stage 0 |
| 5 | **When verification pays, and CAV.** Saturation limit; consistency vs argmax; compute crossover; CAV design; **Table 2: CAV vs baselines at matched cost** (majority, adaptive-consistency, Phase-2 weighted vote, argmax best-of-N, non-adaptive Bayes); **Fig:** real frontier over the model curve | 1.75 | R4, R5, `m6`, `m8`, `m12` | ✅ theory, 🧪 Stage 1 |
| 6 | **Training for selection** (Option A with Stage 2) or **Implications** (otherwise): misalignment proposition and learning model; real arms if run | 0.75 | R7, `m9` | ✅ theory, 🧪 Stage 2 |
| 7 | **Related work** (the archetypes in §2) | 0.5 | — | |
| 8 | **Limitations and conclusion.** One solver family; outcome labels; model assumptions; what remains (correction needs feedback lift) | 0.5 | R8 | |

**Appendix:**

- A: proofs (pair-share identity, invariance theorem, information dominance, tie closed form, overturn formula,
  majority limit, aggregation consistency, Gumbel length law, misalignment proposition).
- B: model details and fits.
- C: robustness (`m12`).
- D: power analysis and winner's curse.
- E: length and liveness (R6) with interventions ✂️.
- F: the full Phase-2 negative results (hints, step format, rewrites, failure-driven GRPO, transplant) as context ✂️.
- G: prompts and compute.

**What to cut from the main text:** R6 (length/liveness) and R8 (correction) are good results but a second story.
Keep each as a short paragraph in §8 with a pointer to the appendix. They could seed a follow-up paper on verifying
long traces.

---

## 6. Evidence matrix (claim → evidence → gap)

| Claim | Evidence now | Still needed |
|---|---|---|
| Model reproduces Phase 2 | 3 out-of-sample matches | — |
| R0 leniency | Fit to section 4; predicts section 13 | 🧪 Stage 0: probability-scored AUROC (P-0a), self-judge vs untrained latent AUROC (P-0b), verdict-count over-dispersion (P-0c) |
| R1/R2 invariance | Proof + simulation | 🧪 Stage 0: within-question AUROC of both judges (H1) |
| R3 headroom anatomy | Closed form + simulation | 🧪 Empirical configuration table on real 400 × 4 pools |
| R4 saturation / crossover | Theory + simulation | 🧪 Majority curve up to N = 16 on real data |
| R5 CAV | Simulation + robustness | 🧪 **Stage 1**: ≥ 800 questions, paired CI, adaptive-consistency baseline |
| R7 training | Proposition + learning model | 🧪 Stage 2 (optional for Option B) |
| Generality | — | 🧪 One more solver (e.g. Qwen3.5-9B or another family) for CAV only, evaluation-only |

---

## 7. Experiments the paper needs (and nothing more)

1. **Stage 0** (inference): re-judge 400 × 4 own test attempts with both judges, recording verdict-token
   probabilities. Produces Table 1's last rows, §4 numbers and Figure 1's real points.
2. **Stage 1** (inference): mixed model, 4 → 16 attempts on contested questions, ≥ 800 held-out questions. CAV and
   baselines on the *same* cached pools; β tuned on a separate dev split.
3. **Second solver** (inference, smaller): the CAV vs majority vs adaptive-consistency comparison on one more model
   (400–800 questions).
4. *(Option A+)* **Stage 2** training arms, with checkpoint choice fixed in advance by contested within-question AUROC.

Pre-register in the repo before running: metrics, baselines, the β-tuning split, the primary comparison (CAV vs
adaptive-consistency at matched average cost) and the significance test (paired bootstrap over questions).

---

## 8. Reviewer objections and answers

| Objection | Answer to prepare |
|---|---|
| "The model is fitted to the data it explains." | Table 1 separates fitted from out-of-sample rows; there are three out-of-sample matches. |
| "Within-question AUROC is known (Bulut 2026)." | Agreed and cited. Our results are the selection/repair invariance theorem, the closed forms, and the downstream method. |
| "SDT for judges is known." | Cited (2603.14893, 2609.18204, 2606.15610). New here: verdict sampling × leniency on *own* attempts, and a criterion shift reproducing a training gain. |
| "CAV is adaptive-consistency plus a verifier." | Yes, and that is the point: the theory says exactly where a verifier adds value (contested top-2 groups after saturation). We beat adaptive-consistency at equal cost. |
| "One small model." | A second solver for the main comparison; the theory is model-agnostic; state the limitation plainly. |
| "Gains are small." | Show power analysis up front; report paired CIs; use ≥ 800 questions. |
| "Outcome labels ≠ correct reasoning." | Limitation; cite DeepSeekMath-V2 and outcome-reward work; the claims are about answer selection, which outcome labels measure exactly. |

---

## 9. Writing order and milestones

| Step | Output | Depends on |
|---|---|---|
| 1 | Freeze notation; write §3 and Appendix A (proofs) from `theory-and-plan.md` | nothing |
| 2 | Draft §1, §4 theory parts and §7 related work; make Figure 1 (teaser) and Table 1 | step 1 |
| 3 | Pre-register Stage 0/1 in the repo | step 2 |
| 4 | Stage 0 → fill §4 empirical parts; decide on R0's place in the headline | Jarvislabs run |
| 5 | Stage 1 (+ second solver) → §5 tables and figures; choose Option A or B | Stage 0 |
| 6 | Optional Stage 2 → §6 | Stage 1 |
| 7 | Limitations, abstract, title; internal review against §8 | all |

Reuse: the ACL template and `references.bib` in `docs/reports/mid-submission/source/`, the figure script in `model/make_figures.py`, and the
Phase-2 report for the appendix.
