# Paper outline: *Predicting When Self-Verification Helps Answer Selection*

**Citation rule.** A prior paper is cited as overlapping only if it directly did what we did; we narrow our claim to
the distinct part. Otherwise the result is ours, stated narrowly.

**Status markers.**
- ✅ in hand
- 🧪 needs the planned runs (second model, second benchmark, baselines, seeds)

---

## Title and abstract
- **Title:** *Predicting When Self-Verification Helps Answer Selection* (alternative: *Better Judges, Same Answers*).
- **Abstract:**
  - A 2B model's self-judge improved AUROC without improving picking; we explain why with a small calibrated model.
  - The model forecast new results before they were measured, and they held: 16-attempt curves, judge AUROCs, and a
    pre-registered +1.6 gain of disagreement-gated verification over compute-matched voting.
  - The usable quantity is the judge's discrimination on contested questions, which collapses where pooled metrics
    look good.

## 1. Introduction
- **Puzzle.** Phase 2: AUROC 0.57 → 0.67, picking flat at 75.2, repair recovered 0.4 of 7 points.
- **Thesis.** Selection gain is governed by within-question discrimination on contested questions, is predictable from
  cheap aggregates, and is invisible to pooled AUROC and sampled verdicts.
- **Contributions:**
  1. A calibrated model whose forecasts held prospectively.
  2. A diagnosis of own-attempt self-verification: leniency, criterion shift, the contested collapse, and an
     invariance theorem.
  3. Contest-adaptive verification (CAV), pre-registered, compute-matched.

## 2. Related work (only directly overlapping work is positioned against)
- **Within-prompt vs pooled judge signal.** Landesberg 2026 shows global agreement overstates best-of-N usefulness for
  Arena judges; Bulut 2026 the same for probes.
  - *Ours, distinct:* own maths attempts; the contested-question restriction; exact invariance for repair as well as
    selection.
- **Selection ceilings and allocation.** Bay & Yearick 2026 (modal ceiling); Iyengar 2026 (budget allocation from a
  labelled pilot).
  - *Ours, distinct:* forecasts from unlabelled 4-attempt aggregates, validated on a held-out 16-attempt pool;
    gating on disagreement.
- **Confidence-weighted and adaptive voting** (CISC, DeepConf, self-certainty, Adaptive-Consistency, ESC, V1): cited
  as baselines, compared in §7. Background works that don't do what we do get one line at most.

## 3. Setting and protocol
- **Model and data:** Qwen3.5-2B mixed adapter as both solver and judge; DeepMath dev 200, test 400, extra 400 held
  out; 16 attempts per question; rule-based answer checker. ✅
- **Scores:** sampled verdict, verdict probability after a reasoning chain, and direct P(incorrect) with no reasoning.
  ✅
- **Protocol:** every rule averaged over 100 random orders, bootstrap over questions, pre-registered sets, rules and
  success criterion; deviations logged. ✅

## 4. A model of self-verified selection
- **Solver:** Beta-distributed solve rates plus an "attractor" wrong answer; three parameters fitted to single-attempt
  accuracy, pass@4 and majority@4. ✅
- **Judge:** a latent score with leniency c₀, between-question signal γ, within-question signal d, and per-attempt
  persistent noise; verdicts sampled from it. ✅
- **Table 1 (out-of-sample checks):** 8-try shares, repair gain (+0.30 vs +0.38), 4-verdict AUROC (0.568 vs 0.568),
  dev/test majority@8, @16 and pass@16. ✅ Second-model and second-benchmark rows 🧪.

## 5. Theory: what selection can use
- **Theorem 1 (invariance):** repair gain = −E Cov(flag, correct | question). Selection depends only on
  within-question likelihood ratios, so any difficulty-only signal gives exactly zero gain. ✅
- **Pair-share identity (stated as a narrow technical lemma):** pooled AUROC is about 99.9% between-question at
  typical pool sizes. ✅
- **Headroom and aggregation:**
  - a closed form for the tie-breaking gain, and a never-below-majority guarantee for the lexicographic rule;
  - summed log-odds aggregation is consistent while argmax is not;
  - the vote-only limit P(p > ρ(1−p)). ✅

## 6. Diagnosis on own attempts (Stage 0)
- **Leniency hides signal.**
  - Sampled-verdict AUROC is 0.57/0.64; probability scoring gives 0.69–0.72, the latent value the model predicted
    from Phase-2 flag rates alone.
  - Paired gain +0.07 to +0.09; verdicts are over-dispersed 12×. ✅
- **Criterion shift.** The model reproduces Phase 2's trained-judge "gain" by moving only the leniency criterion.
  ✅ (model). The direct test with trained judges is future work.
- **Contested collapse.**
  - Pooled 0.72 → within-question 0.61 → contested about 0.5 on test.
  - Judge-free trace features (length, self-corrections) reach the trained judge's pooled AUROC (0.65–0.70) and are
    at chance on contested questions. ✅

## 7. Contest-adaptive verification (Stage 1)
- **Procedure:** stop on unanimous 4 (about 50% of questions); otherwise sample to N₁, judge only the top-2 answer
  groups, and score groups by size × (β + mean logit). β is tuned on dev. ✅
- **Primary pre-registered result** on test ∪ extra:
  - +1.6 [+0.5, +2.6] over compute-matched majority;
  - +1.4 at matched tokens;
  - +1.2 [+0.05, +2.3] over adaptive-consistency;
  - above the 79.8% vote-only plateau with 29% less compute.

  The prefill-only variant gains +1.35 at about 6 units. ✅
- **Mechanism:** the gain comes from overturning wrong pluralities (+1.18 of +1.60) and is exactly 0 on unwinnable
  questions. ✅
- **Baselines and wrapper:** each competitor's signal (CISC P(True), DeepConf, self-certainty, V1),
  used natively vs inside CAV, at matched cost. 🧪

## 8. Predicting the gain (headline figure)
- **Registered prediction:** the semi-synthetic model, given the judge's dev within-question AUROC, predicted +1.3;
  observed +1.6. ✅
- **Across conditions:** predicted vs observed gain for every verifier, model and benchmark; contested
  within-question AUROC predicts gain, pooled AUROC does not. 🧪
- **Robustness:** 2 extra seeds of the primary result; swapped dev/test tuning; worst-case gap to majority vote. 🧪
  (the swap is free)

## 9. Limitations and conclusion
- **Limitations:**
  - one solver family (until 🧪);
  - outcome labels;
  - our own step conversion;
  - the length/liveness mechanism was not supported within 4k–16k-token traces;
  - judge training is untested.
- **Conclusion:** measure verifiers within contested questions, score them by probability, and spend them only where
  sampled answers disagree after voting saturates; their value can then be forecast before deployment.

## Appendices
- **A.** Proofs: invariance, pair share, tie closed form, overturn probability, consistency, misalignment
  proposition, Gumbel length law.
- **B.** Model robustness. **C.** Experimental details and costs. **D.** Pre-registration and deviations.
- **E.** Phase-2 negative results (context). **F.** Length/liveness theory and null test; trained-judge curves (future
  work).

## Figures and tables
- **Figures:**
  1. Teaser: one latent judge reproducing three Phase-2 AUROCs.
  2. Pooled vs within-question vs contested AUROC, including trace features.
  3. Predicted vs observed scaling curves.
  4. Accuracy vs decoded tokens (all methods).
  5. **Predicted vs observed gain across conditions** (headline).
- **Tables:**
  1. Out-of-sample checks.
  2. Stage 0.
  3. Trace features.
  4. Selection results with baselines.
  5. Gain decomposition.
