# Novelty map and paper framing (literature review, 2026-10-29)

Each of our findings is checked against published or preprint work. **Status:**
- **Known:** do not claim.
- **Partly known:** claim the specific delta only.
- **New:** no prior work found; verify again before submission.

## 1. Finding-by-finding novelty

| # | Our finding (evidence) | Closest prior work | Status | What we can still claim |
|---|---|---|---|---|
| F1 | Pooled AUROC is between-question; selection needs within-question discrimination (pair-share 0.076%; test pooled 0.72 → within 0.61) | [Landesberg 2026, "When LLM Judge Scores Look Good but Best-of-N Decisions Fail"](https://arxiv.org/abs/2603.12520): Arena best-of-4, global r = 0.47 vs within-prompt r = 0.27, recovers 21% of the oracle gain. [Bulut 2026](https://arxiv.org/abs/2609.03436): probes, pooled 0.85 vs within 0.50. [Rethinking RM Evaluation (ICLR 2025)](https://arxiv.org/abs/2410.05584): multi-response metrics predict best-of-N better. | **Known** | (a) The *exact* identities: the pair-share formula, and **Theorem 1**, which shows selection *and repair* are invariant to between-question information, with the exact repair identity Δ = −E Cov(f, Z \| x). (b) **Contested** within-question AUROC: test 0.47–0.51, near chance, where all the headroom lies. (c) Judge-free trace features reach a trained judge's pooled AUROC (0.65–0.70) and are at chance on contested questions. |
| F2 | Leniency + verdict sampling hide signal: sampled AUROC 0.565/0.635 vs probability 0.69–0.72; verdicts over-dispersed (12×) | Signal detection for judges: [Cacioli 2026](https://arxiv.org/pdf/2603.14893). P(True) and token-probability confidence: [Kadavath 2022](https://arxiv.org/abs/2207.05221), [CISC (ACL Findings 2025)](https://arxiv.org/abs/2502.06233). Coarse scores cause ties: Landesberg 2026 (67% ties). | **Partly known** | A *quantitative* account on own attempts. A latent judge fitted only to Phase-2 single-verdict flag rates **predicted** the 4-verdict AUROC (0.568 = 0.568) and the latent AUROC (0.715 vs 0.69–0.72 observed). The Phase-2 self-judge's "training gain" (0.568 → 0.665) is reproduced by a **criterion shift alone**, a new explanation of a published-style negative result. |
| F3 | Majority vote saturates; selection is capped well below pass@N; argmax falls below majority (76.7 vs 79.8) | [Brown et al. 2024 (Large Language Monkeys)](https://arxiv.org/abs/2407.21787). [Bay & Yearick 2026, modal and correlation ceilings](https://arxiv.org/abs/2606.28661): the vote settles within a few dozen draws; "the bottleneck is recognizing a right answer". [Stroebl et al. (ICLR 2026)](https://arxiv.org/abs/2411.17501). [Chen et al. 2024](https://arxiv.org/abs/2403.02419). | **Known** | Only the *prospective forecast*: a 3-parameter Beta + attractor model fitted to **N = 4 aggregates** predicted test majority@8 / @16 / pass@16 (77.5 / 78.2 / 90.8 vs 77.5 / 78.7 / 90.2) and the configuration shares. The forecasting style follows [Schaeffer et al. (ICML 2025)](https://arxiv.org/abs/2502.17578) for pass@k; ours extends it to *majority vote and selection*. |
| F4 | Verification pays only after self-consistency saturates; the crossover depends on verification cost | Compute allocation under imperfect verifiers: [Iyengar 2026, "Sample, Mix, or Verify?" (SPLIT)](https://arxiv.org/abs/2610.23255), an exact selection formula with difficulty, shared blind spots and correlated calls, planned from a pilot. [When to Solve, When to Verify (2025)](https://arxiv.org/abs/2504.01005). [Snell et al. 2024](https://arxiv.org/abs/2408.03314). | **Partly known** (crowded) | The *empirical* crossover refinement: with prefill-only direct reads, verification beats compute-matched majority already at about 6 units (+1.35 [+0.84, +1.88]). Do not claim the allocation theory as new; position against SPLIT. |
| F5 | **CAV**: verify only questions where the first 4 answers disagree; judge only the top-2 answer groups; log-odds aggregation with a vote prior. Pre-registered +1.6 [+0.5, +2.6] vs majority, +1.2 [+0.05, +2.3] vs adaptive-consistency. The gain comes from overturning wrong pluralities. | Adaptive stopping: [Adaptive-Consistency (EMNLP 2023)](https://arxiv.org/abs/2305.11860), [ESC (ICLR 2024)](https://arxiv.org/abs/2401.10480). Weighted voting: [DIVERSE (ACL 2023)](https://arxiv.org/abs/2206.02336), [CISC](https://arxiv.org/abs/2502.06233), [DeepConf (ICLR 2026)](https://arxiv.org/abs/2508.15260), [self-certainty (NeurIPS 2025)](https://arxiv.org/abs/2502.18581). Pairwise: [V1 (ICML 2026)](https://arxiv.org/abs/2603.04304), [PairJudge](https://arxiv.org/abs/2501.13007). | **New as a combination** (no paper found that gates verification on sample disagreement and restricts it to the top-2 groups); components known | The procedure, its compute profile (half the questions get zero verification cost), the pre-registered result, and the gain decomposition (+1.18 of +1.60 from minority-right questions, 0 on unwinnable). **Must be compared** with CISC, DeepConf, self-certainty, V1 and a reward model before claiming superiority. |
| F6 | The **gain was predicted before judging** from the real answer structure and the judge's dev within-question AUROC (≈ +1.3 predicted, +1.6 observed) | SPLIT plans budgets from a labelled pilot (closest). No paper found that registers a numeric selection-gain prediction from a discrimination metric and then tests it. | **New** (methodological) | "Predict-then-verify": a metric (contested / within-question AUROC) plus a model forecast the selection gain of a verifier *before* deployment. |
| F7 | Trained self-judge (Phase 2): AUROC up, picking flat | [Self-[In]Correct (2024)](https://arxiv.org/abs/2404.04298): models struggle to discriminate their own responses. [STV (NeurIPS 2026)](https://arxiv.org/abs/2605.30290): verdict-only RL has limited downstream benefit. [Variation in Verification (ICLR 2026)](https://arxiv.org/abs/2509.17995): difficulty and generator dependence. | **Partly known** | Our *explanation* of it (F2 criterion shift + F1 invariance) is new; the phenomenon is not. |
| F8 | Liveness: 98–99% of right traces contain self-corrections, so "an error occurred" detection fails; the Gumbel length law | [Anatomy of R1 math reasoning (2026)](https://arxiv.org/pdf/2606.07410): reflection rates don't separate right from wrong. [Know When to Stop (2026)](https://arxiv.org/pdf/2607.00482): unproductive reflection is denser in wrong traces. | **Partly known**; our length/liveness test was **null** within 4k–16k tokens | Appendix only: the closed-form dilution law and the liveness model as theory. Do not headline. |
| F9 | Per-question balance removes a difficulty shortcut in verdict training (Proposition 3) | Gradient starvation ([Pezeshki 2021](https://arxiv.org/abs/2011.09468)); pairwise training (V1, PairJudge) | **Partly known**; **untested** (arms trained, not evaluated) | Future work only. |

**Removed from the claims:** "pooled AUROC is misleading" as a headline (F1), majority saturation as a discovery (F3), and allocation theory (F4).

## 2. What is genuinely novel and important

1. **Predictive account of self-verified selection, validated prospectively (F3 forecast + F2 + F6).** A small calibrated model, fitted to cheap 4-attempt aggregates, predicted out of sample:
   - the 16-attempt majority and pass curves;
   - configuration shares;
   - the AUROC of a judge under three scoring schemes;
   - the CAV gain, registered before any judging.

   Closest: Schaeffer (pass@k only), SPLIT (allocation from a labelled pilot). Neither forecasts verifier-driven selection gains from a discrimination metric.
2. **A diagnosis of why self-verification "fails" that reverses its reading (F2 + F1 deltas).** On the model's own attempts:
   - the judge carries real signal (latent AUROC about 0.7), hidden by leniency and verdict sampling;
   - a training "improvement" can be a pure criterion shift;
   - the signal vanishes exactly on contested questions, where selection needs it. Theorem 1 makes this exact for both selection and repair.

   Closest: Landesberg 2026 (Arena, judges) and Bulut 2026 (probes) have the pooled/within point. The contested restriction, the repair identity, the criterion-shift explanation and the own-attempt maths setting are ours.
3. **CAV: a cheap, disagreement-gated, verifier-agnostic selection procedure** that beats compute-matched majority vote and adaptive-consistency in a pre-registered test, by the predicted amount. Gains come from overturning wrong pluralities. Prefill-only variants win at small budgets.

## 3. Recommended framing

**Title options:**
- *Predicting When Self-Verification Helps Answer Selection* (preferred)
- *Better Judges, Same Answers: A Predictive Account of Self-Verification for Answer Selection*

**One-sentence thesis.** Whether a model's judgement of its own attempts improves the answer it picks is predictable in advance from one quantity, its discrimination *within contested questions*. A small model of solve-rate heterogeneity and judge leniency forecasts it, and a disagreement-gated procedure built on the forecast beats compute-matched voting.

**Contributions in priority order:**
1. **Model + prospective validation:** forecasts of selection curves, judge AUROCs and verification gains, registered before data (F3 delta, F2, F6).
2. **Diagnosis:** leniency/criterion shift, the contested-discrimination collapse, and the invariance theorem with the repair identity (F2, F1 deltas).
3. **Method:** CAV, compared at matched compute to CISC, DeepConf, self-certainty, adaptive-consistency/ESC, V1 and a reward model; presented as a verifier-agnostic wrapper (F5).

**Positioning paragraph (must cite):** Landesberg 2026 and Bulut 2026 (within-prompt signal); Bay & Yearick 2026 and Brown 2024 (selection ceilings); Iyengar 2026 (allocation under imperfect verifiers); Stroebl 2026 (resampling limits); CISC / DeepConf / self-certainty (confidence-weighted voting); Adaptive-Consistency / ESC (adaptive sampling); V1 / PairJudge (pairwise selection); STV, Self-[In]Correct and Variation in Verification (self-verification limits).

## 4. Experiments the framing needs (from the plan)

- **Baselines at matched cost, also run inside CAV:** CISC-P(True) (free), adaptive-consistency + ESC (free), DeepConf + self-certainty (prefill), Qwen2.5-Math-PRM-7B (prefill), V1-Infer (contested questions).
- **Generality:** a second model (16 attempts) and a second benchmark (8 attempts). Each gives a new prospective prediction-vs-outcome point, the core evidence for contribution 1.
- **Robustness:** 2 extra seeds of the primary test experiment.
- **Free analyses:** gain vs contested within-question AUROC across all verifiers (does it predict and pooled AUROC not?); worst-case gap to majority vote; swapped tuning and evaluation.
