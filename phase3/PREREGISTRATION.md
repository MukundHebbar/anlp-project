# Phase 3, Stages 0–1: pre-registration

Written 2026-10-28, before any Phase-3 attempt was generated. Theory and predictions:
`docs/research/verification-theory/theory-and-plan.md`. Code: `phase3/`.

## Data

| Set | Questions | Role |
|---|---|---|
| test | FINAL-v3 SOLVE test, 400 | Evaluation (Phase-2 comparability) |
| extra | 400 SOLVE train questions no mixed-model run could have seen | Evaluation |
| dev | the 200-question SOLVE dev slice | **Tuning only** (β, CAV settings, adaptive-consistency threshold) |

Sets are fixed by `phase3/sets.py` (seed 20261028; `phase3/manifests/sets.json`).

## Generation and judging

- **Solver:** Qwen3.5-2B + `mixed-step75`. SOLVE prompt v2, T = 1.0, top-p 1, no top-k, 16,384-token cap, 16
  attempts per question.
- **Judge:** the same adapter with the JUDGE student prompt v2 on the own attempt converted to steps
  (`phase3/common.py`; the Phase-2 converter was lost, so this is a rebuild). T = 1.0, 8,192-token cap. The chain
  stops at "Decision:".
- **Verdict probability:** "Decision:" is appended and P(incorrect) is read from the top-20 next-token logprobs (first
  forced position showing a verdict token).
- **Chains:** 4 per attempt for test attempts k = 0..3; 1 otherwise.
- **Correctness:** the project's SOLVE reward (finished, strict gates, checker v3). Answer groups use checker
  equivalence; a group is right if its answer matches the key.

## Stage 0: measurement (test, attempts 0–3, 4 chains each)

| ID | Prediction (from the theory) | Test |
|---|---|---|
| P-0a | Probability-scored AUROC is well above the 4-sampled-verdict AUROC (model: up to 0.715 vs 0.568) | Paired bootstrap over questions of AUROC(mean p over 4 chains) − AUROC(share of 4 sampled verdicts) > 0 |
| P-0c | Verdicts on the same attempt are over-dispersed: P(4 of 4 "incorrect" \| wrong) ≫ binomial at the same rate | Observed vs binomial share |
| R0-fit | The single-verdict hit and false-alarm rates are lenient (judge flags < 15% of attempts); d′ = z(H) − z(F) > 0.3 | Point estimates |
| H-within | Within-question AUROC (probability, all 16 attempts) is reported with the global AUROC and the contested-question AUROC | Descriptive, with question-cluster bootstrap CIs |

Phase-2 reference values: 4-verdict AUROC 0.568 (untrained mixed judge, test); single-verdict flags 7.4% / 2.2%
(dev).

P-0b (self-judge vs untrained, latent AUROC) is **not testable**: the self-judge adapters were lost. It moves to
Stage 2, where a Phase-2-style judge is retrained.

## Stage 1: contest-adaptive verification (CAV)

- **Primary rule:** CAV with N₁ = 16, m = 8, top-2 groups, verdict-probability scoring, score n_g·(β + mean
  logit P(correct)). β is chosen on dev from {−4, −3.5, …, 3}.
- **Primary comparisons** on test ∪ extra (800 questions). Each rule is averaged over 100 random orders of each
  question's 16 attempts; differences use a paired bootstrap over questions (2,000 resamples).
  1. CAV vs majority at the same average cost (attempt = 1 unit, judge chain = 0.3 units; majority mixed between
     floor and ceil N).
  2. CAV vs adaptive-consistency (Beta stopping) at the closest average cost. The threshold set is
     {0.6, 0.7, 0.8, 0.9, 0.95, 0.99}.
- **Success:** the 95% CI of comparison 1 excludes 0. Comparison 2 is reported either way.
- **Secondary (reported, not decisive):**
  - the other CAV settings (N₁ ∈ {8, 12}, m = 4);
  - non-adaptive Bayes aggregation and argmax at N ∈ {1, …, 16};
  - oracle@N and majority@N curves;
  - the N = 4 configuration table (tie / overturn / unwinnable shares);
  - mean attempt and judge-chain token counts, so costs can be restated in tokens.

## Deviations

Any change after results are seen is listed here with its reason.

1. **2026-10-28, after the 4-question smoke test, before any real run.**
   - *Direct score.* After a full reasoning chain the forced verdict probability is almost always about 0 or 1 (the
     chain has decided), so one chain's probability is close to a sampled verdict. A direct score was therefore
     added: P(incorrect) read right after the prompt, with no reasoning (P(True)-style, `p_direct`), one per
     attempt. CAV with the direct score (unit cost 0.05, prefill only) is reported as a **secondary** rule. The
     primary rule is unchanged.
   - *Costs.* The smoke test's judge chains averaged about 4.5k tokens against about 6.7k for an attempt, so the
     pre-registered 0.3 units per chain flatters chain scoring. Every comparison is also reported at matched
     *decoded tokens* (attempt tokens + chain tokens; prefill excluded).

## Predictions registered before any judging (2026-10-29)

**Vote-only results on dev (16 attempts per question).** Single attempt 69.8%, pass@4 86.3%, majority@4 78.1%
(Phase 2: 69.8 / 86.5 / 77.5). The theory model fitted to Phase-2 4-attempt numbers predicted the 16-attempt curves:

| | Predicted | Observed |
|---|---|---|
| Majority@8 / @16 | 81.6 / 82.5 | 80.2 / 81.3 |
| pass@16 | 94.1 | 92.0 |

**Predicted CAV gain** (`phase3/semisynth.py`, `runs/semisynth_dev.json`). Real dev answer structure with a simulated
judge; N₁ = 16, m = 8; average cost ≈ 11 units; majority at that cost 81.0%:

| Within-question AUROC of the judge | ≈ 0.50 | ≈ 0.66 | ≈ 0.69–0.75 | ≈ 0.85 | ≈ 0.90 |
|---|---|---|---|---|---|
| Predicted gain over majority (pts) | ≈ 0 | +1.3 | +3 | +6 | +7 |

The noise at 200 questions is about ±1 point; β is tuned on the same pool in this simulation.

**Test.** Read the real judge's within-question AUROC on dev, look up the predicted gain, and compare it with the
measured CAV gain on test ∪ extra.

2. **2026-10-29, after 150 dev questions were judged; no test or extra judgments existed yet.**
   - *Exploratory learned combiner* (`analyze.py --attempts`): pairwise logistic regression on same-question
     (wrong − right) differences of six features: logit P(incorrect) after a chain, logit direct P(incorrect), log
     length, log self-correction count, log guess-phrase count, number of final-answer tags. It is fitted on dev only
     and applied to test and extra.
   - *Why:* 5-fold cross-validation over dev questions gave within-question AUROC 0.693, against 0.631 (chain) and
     0.641 (direct).
   - *Two variants:* "combo" (all six features; chain cost) and "combo-cheap" (no chain; prefill-only cost 0.05).
   - *Status:* both are **secondary, exploratory** rules. The primary rule and test are unchanged.

3. **2026-10-29, Stage 2.**
   - *Restart.* The first launch of both arms stopped after step 2: a few judge prompts within Phase 2's
     50,000-character limit exceeded the trainer's 17,408-token prompt room (HTTP 400 from the rollout server). Both
     arms' prompts were rebuilt with an extra 16,000-token limit (same seed and construction) and restarted from step
     0.
   - *Training pool.* Training questions were cut to the 450 generated when workers 0–2 finished (chunks 0–6, 8, 9),
     instead of 600, to free GPUs.

## Phase 3b: evidence grid and sampling (registered 2026-10-29, before any of these runs)

Plan: `PLAN-60h.md` (the Gemma rows are replaced by the sampling rows T1–T3). Scripts: `evidence.py`, `sampling_gen.py`,
`sandbox.py`; worker `turing/wave1.sh`. Dev is used only for tuning (α, weights, combination); results are read once on
test ∪ extra. CPU bounds already computed (`sampling_cpu.py`, `runs/sampling_cpu.md`): answer-level sharpening keeps the
vote ceiling at 79.8%; moving half the attractor mass to one-off answers raises it to 83.5%.

**Metrics per source.** Contested AUROC (group level: right group vs wrong groups on contested questions), right vs
attractor and right vs one-off, coverage, extra tokens; downstream: log-odds evidence added to the vote counts, gated by
ESC window-2 disagreement, against majority / ESC / AC / CISC at matched cost.

**Predictions.**
1. *Shared bias.* Self sources from the same trace (direct, chain, answer-only, solver log p) show contested attractor
   AUROC ≤ 0.58. Sources outside the trace (program checks, backward checks) have a smaller attractor/one-off gap.
2. *T1 (likelihood).* Within contested questions, attractor attempts have mean token log p at least as high as right
   attempts (attractor AUROC of −mean log p ≤ 0.55). The importance-weighted vote toward p^α (α > 1, tuned on dev) does
   not beat majority@16 by more than +0.5 on test ∪ extra. Self-normalised weights over 16 attempts have effective sample
   size < 4 for α ≥ 2 on most questions.
3. *T2 (lock-in).* Resampling from a prefix of an attractor attempt returns the attractor more often than fresh sampling
   does, increasingly so with a longer prefix. From the 25% prefix, the attractor share stays above the fresh-sample
   attractor share for the same questions.
4. *T3 (temperature).* T 0.7 sharpens: single-attempt accuracy rises and majority@8 changes by less than ±1.5 (table A
   bound). T 1.3 and hot start lower the attractor share, but per-attempt accuracy also drops; net majority@8 within
   ±1.5 of T 1.0.
5. *Program-of-thought.* PoT answers have a different error profile: on questions where the language attempts'
   plurality is a wrong attractor, PoT's plurality differs from that attractor more than half the time. Whether mixing
   PoT votes raises the ceiling is open; no prediction.

**Checkpoint combination (registered 2026-10-29, before the evidence grid was run on test ∪ extra).** The three sources
with the best dev top-2 AUROC (dev top-2 coverage ≥ 50%) are combined by an L2 logistic regression (λ = 1) on dev
groups of contested questions, with features = within-question centred scores (logit for probabilities, standardised
otherwise; 0 where unscored). Its P(wrong) enters the same downstream rule (argmax n_g + w·logit(1 − p), w tuned on dev)
and is evaluated once on test ∪ extra, ESC-2 gated and over all 16 attempts. Prediction 6: it beats majority by
< +1.0 point with all 16 attempts (CI includes 0) unless a non-self source (program, PoT, backward) reaches top-2 AUROC
≥ 0.65.
