# Plan for the next 50 GPU-hours (Phase 3b)

29 October 2026.

**Main question.** What does a model's judgement of its own attempts actually know? Self-verification looks good on
pooled metrics, so does it carry question difficulty, a bias shared with the solver, or real within-question
discrimination? And which kinds of evidence supply the within-question information it lacks?

**Not the main thing.** Selection methods (CAV and similar). Each evidence type's effect on picking is measured once,
on CPU, with one fixed simple rule (log-odds weighted vote over the 16 cached attempts, vs majority vote), as a
downstream check.

**Budget and rules.**
- About 50 GPU-hours on Turing, at most 4 GPUs at once.
- Cached attempts only wherever possible; probabilities read in a single prefill pass.
- Predictions registered in `PREREGISTRATION.md` before each run.

**Key metrics.** For every evidence source, on test ∪ extra (dev only for any tuning):
- **contested AUROC:** questions whose attempts disagree and where the right answer isn't already the strict majority;
- **attractor AUROC:** right answers vs the solver's own most common wrong answer, against right vs one-off wrong
  answers;
- **within-group error correlation** ρ_s;
- **pooled AUROC**, to show the gap.

---

## Phase 0: free analyses (CPU, today)

| ID | Analysis | Question |
|---|---|---|
| F0.1 | Self-judge AUROC: right vs **attractor** wrong answers, against right vs **one-off** wrong answers | Does self-verification share the solver's bias? |
| F0.2 | Within-answer-group correlation of judge scores (ρ_s) | How correlated are its errors, and what ceiling does that imply? |
| F0.3 | Difficulty share: how much of the judge's pooled AUROC a question-only predictor (solve rate from the other 15 attempts) explains; residual within-question signal | How much of "verification" is just difficulty? |
| F0.4 | The same three numbers for the judge-free trace features and the existing solver-side signals | Reference points |
| F0.5 | Fix the report's seed wording; register Phase 3b | Hygiene |

---

## Phase 1: the evidence grid (≈ 25 GPU-hours, the core)

Each row is one evidence source, run on cached attempts. Contested questions use dev for any tuning and test ∪ extra
for evaluation.

| ID | Evidence | Design | GPU-h |
|---|---|---|---|
| (done) | Pointwise self, 2B | Existing chain and direct probabilities | 0 |
| **P1** | **Contrastive self, 2B** | Top-2 answer groups on contested questions; one attempt from each (up to 3 pairs per question); "Which final answer is correct, A or B?"; P(A) read in one prefill pass, both orders, averaged | ~3 |
| **P2** | **Independently checkable, 2B** | For each top-2 answer on contested questions, the 2B writes a short Python check of that answer against the problem (2 programs, temperature 0.6, 1k cap). Executed in a sandbox (10 s timeout); score = pass rate; "no check possible" = neutral (coverage reported) | ~7 |
| **P3** | **Independent model, 9B** | Qwen3.5-9B on the cached 2B attempts: direct P(incorrect) for all answered attempts (prefill), plus the P1 pairwise prompt on contested questions | ~9 |
| **P4** | **Trained self-judges** (adapters exist) | Direct read with the `global` and `perq` step-32 adapters: does training change leniency (criterion shift) or within-question/contested signal? | ~2 |
| **P5** | **Solver confidence** (no judge) | One prefill pass of the 2B saving token log-probs → DeepConf-style confidence, self-certainty, CISC response-probability | ~4 |

**Layout:** P1, P4, P5 on 3 GPUs and P2 on 1 GPU at the same time (about 6–7 hours), then P3 on 4 GPUs (about 2.5
hours).

**Analysis (CPU).** One table and one figure: for each source, pooled / within-question / contested / attractor AUROC
and ρ_s. Then a one-line downstream check per source (weighted-vote gain vs majority, matched cost), and its gain
predicted from contested AUROC vs observed.

**Expected shape (registered beforehand):**
- pointwise self-verification and solver confidence are high pooled, near chance contested, and weakest against
  attractor answers;
- contrastive, executed and independent-model evidence raise contested and attractor AUROC;
- downstream gain tracks contested AUROC, not pooled AUROC.

---

## Phase 2: is it general? (≈ 25 GPU-hours)

| ID | Experiment | Design | GPU-h |
|---|---|---|---|
| **R1** | **Second benchmark** | MATH-500 (or an Olympiad subset), 400 questions × 8 attempts with the 2B. Then the cheap grid rows on it: pointwise direct (self), contrastive (P1) and 9B direct. | ~8 |
| **R2** | **Second solver** | Qwen3.5-4B as solver, 400 test questions × 8; same cheap grid rows, with the 4B as its own judge plus 9B direct. Does the difficulty/shared-bias pattern hold for another model? | ~10 |
| **R3** | **Seed** | Fresh 8 attempts on the 400 test questions (2B) and the cheap grid rows: is the grid stable across draws? | ~5 |
| | Slack | | ~2 |

Phase 2 deliberately skips judge chains and CAV variants; only cheap prefill reads.

---

## Budget

| Phase | GPU-h | Cumulative |
|---|---|---|
| 0 | 0 | 0 |
| 1 Evidence grid | ~25 | 25 |
| 2 Generality (benchmark, solver, seed) | ~23 | **~48** |

**Wall time:** about 14–17 hours at 4 GPUs.

## Deliverables

1. **The evidence grid** (main result): what self-verification captures vs what contrastive, checkable and independent
   evidence add, on contested questions and against the solver's own wrong answers.
2. **The difficulty and shared-bias analysis** (F0.1–F0.3) for self-verification.
3. **Generality:** the same grid pattern on a second benchmark, a second solver and a second draw.
4. **A downstream check per source** (one fixed rule) and predicted-vs-observed gain: supporting evidence that the
   grid matters for decisions.

## Fallbacks

| Problem | Fallback |
|---|---|
| Pairwise prompts too long | Last 3k tokens of each attempt plus the answer; logged as a deviation |
| Code checks rarely applicable | Report coverage; evaluate on the checkable subset |
| 9B memory | Prefill only, 32k context, small batch |
| Nothing restores the contested signal | Still a clear result: self-verification on own attempts is difficulty plus shared bias, and even independent evidence fails on contested questions. Phase 2 confirms how general that is. |
