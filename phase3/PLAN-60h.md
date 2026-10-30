# Plan for the next 60 GPU-hours (Phase 3b): evidence that self-verification lacks, and sampling

29 October 2026. Supersedes `PLAN-next-50h.md`.

**Main question.** What does self-verification of one's own attempts actually carry? Which kinds of evidence supply
the within-question information it lacks, and does that make picking substantially better?

---

## 1. Where we are (Phase 3b CPU analyses, done; `runs/cpu_analyses.md`)

Test ∪ extra, 800 questions, 16 attempts each:

| Signal | Pooled AUROC | Within question | Contested | Contested: right vs the solver's **attractor** wrong answer | Contested: right vs **one-off** wrong |
|---|---|---|---|---|---|
| Self-judge, chain | 0.697 | 0.641 | 0.574 | **0.555** | 0.678 |
| Self-judge, direct | 0.732 | 0.639 | 0.559 | **0.545** | 0.637 |
| Length | 0.672 | 0.585 | 0.515 | 0.491 | 0.655 |
| Self-corrections | 0.655 | 0.553 | 0.522 | 0.499 | 0.649 |
| Difficulty only (other 15 attempts' solve rate) | **0.906** | 0.5 | 0.5 | — | — |

- **Difficulty dominates pooled AUROC.** A question-only predictor (0.906) beats the judge (0.73); adding the judge
  moves it only to 0.917.
- **Shared bias.** On contested questions the self-judge can barely tell the right answer from the wrong answer the
  solver itself keeps producing (0.55). It does better against one-off wrong answers (0.64–0.68).
- **Correlated verdicts.** Within a wrong-answer group, the direct score's intraclass correlation is **0.75** (0.28 in
  right groups). The judge gives the same verdict to every attempt reaching the same wrong answer, so judging more of
  them adds almost nothing.
- **Free baselines** (dev-tuned, vs majority at matched cost):
  - CISC-P(True): +1.0 at N=4, +0.7 at N=8, +1.0 at N=16.
  - **Early-stopping self-consistency (window 2): 79.1% at 4.2 units, +2.8 vs majority at that cost**, the strongest
    low-budget baseline. Any new method must be built on ESC-style stopping, not on the 4-unanimity gate.

**Implication.** The missing information is exactly what self-verification shares with the solver. Better picking
needs evidence that is **independent of the solver's reasoning**.

---

## 2. Literature: evidence types to test (what is established)

| Evidence type | Established by | Our row |
|---|---|---|
| Executable checks of an answer | [CSV (Zhou et al. 2023)](https://arxiv.org/abs/2308.07921); [PROVE (Toh et al. 2024)](https://arxiv.org/abs/2410.12608), effective for 0.5B–13B models | E-D |
| Backward / answer-conditioned checks | [Self-Verification (Weng et al. 2022)](https://arxiv.org/abs/2212.09561); [FOBAR (2023)](https://arxiv.org/abs/2308.07758) | E-C |
| Comparative (pairwise) judging | [V1 (ICML 2026)](https://arxiv.org/abs/2603.04304); [PairJudge (2025)](https://arxiv.org/abs/2501.13007) | E-B |
| Sampling: power / MH, SMC, temperature, diversity | [Karan & Du (ICLR 2026)](https://arxiv.org/abs/2601.21590 ); [Power-SMC](https://arxiv.org/abs/2602.10273); [Rollout Roulette](https://arxiv.org/abs/2502.01618); [selective sampling](https://arxiv.org/abs/2510.01218); [Nitarach 2026](https://arxiv.org/abs/2603.27844) | T1–T3, PoT |
| Trace-free (answer-only) judging, against trace-anchoring | Reasoning chains sway judges ([2604.06756](https://www.alphaxiv.org/abs/2604.06756)); [self-preference bias](https://arxiv.org/abs/2410.21819) | E-A |
| Solver confidence (no judge) | [DeepConf](https://arxiv.org/abs/2508.15260); [self-certainty](https://arxiv.org/abs/2502.18581); [CISC](https://arxiv.org/abs/2502.06233) | E-H |
| Compute: verification vs more samples | [When to Solve, When to Verify (COLM 2025)](https://arxiv.org/abs/2504.01005); [ESC](https://arxiv.org/abs/2401.10480); [Adaptive-Consistency](https://arxiv.org/abs/2305.11860) | baselines |

**What is ours.** No paper measures, on a model's *own* attempts and on *contested* questions, which evidence type
breaks the solver's **shared bias** (attractor AUROC), how correlated each source's errors are within answer groups,
and whether the selection gain follows contested AUROC as a model predicts. PROVE and CSV show program checks help;
the Jury paper shows independence helps; neither isolates contested / shared-bias discrimination.

---

## 3. Experiments

**Models.**
- Qwen3.5-2B + `mixed-step75`: solver and every self-evidence row.
- Qwen3.5-2B + `global` / `perq` adapters: E-G.
- Python executes the E-D programs.
- The rule-based answer checker (not a model) provides correctness labels.

**Common protocol.**
- Contested questions are those whose first attempts disagree. Each top-2 answer group per contested question gets
  evidence. Dev is used for fitting or tuning; test ∪ extra for evaluation.
- Cached 2B attempts throughout.
- **For every row, report:** contested AUROC, attractor vs one-off AUROC, within-group error correlation, coverage,
  extra tokens, and the downstream gain under one fixed rule (log-odds evidence added to vote counts, gated by ESC
  window-2 disagreement), compared with majority, ESC, AC and CISC at matched cost.
- **Registered before running:** each row's predicted gain from its dev contested AUROC, and the shared-bias
  prediction (independent sources show a smaller attractor/one-off gap than self sources).

### Wave 1: self-model evidence and baselines (4 GPUs, ≈ 7 h wall, ≈ 17 GPU-h)

| ID | Evidence | Design | GPU-h |
|---|---|---|---|
| **E-A** | Answer-only check (2B) | "Problem: … Proposed final answer: X. Is this answer correct?" P(yes) by prefill, no trace. Per top-2 answer. | ~1 |
| **E-B** | Pairwise (2B) | Representatives of the top-2 groups (up to 3 pairs), "Which final answer is correct, A or B?", both orders, P(A) by prefill. Attempts truncated to their last 3k tokens if needed. | ~3 |
| **E-C** | Backward check (2B) | FOBAR/condition-masking: mask one given number in the problem, give the candidate answer, ask for the masked number (short generation, 4 samples, up to 2 masks). Score = recovery rate. Numeric questions only; coverage reported. | ~3 |
| **E-D** | Executable check (2B) | CSV/PROVE-style: the 2B writes a Python program that verifies the candidate answer against the problem (substitution, constraints, brute force); 3 programs per answer; sandbox run, 10 s timeout. Score = pass rate; no-check = neutral. **Also the PROVE baseline:** program-consistency filtering over all 16 attempts. | ~7 |
| **E-G** | Trained self-judges (adapters exist) | Direct read with `global` / `perq`: criterion shift vs contested signal | ~2 |
| **E-H** | Solver confidence | 2B prefill over cached attempts saving token log-probs → DeepConf (offline), self-certainty, CISC response-probability | ~4 (overlaps; total wave ≈ 17–20) |

### Wave 2: sampling (replaces the Gemma judges; user decision 2026-10-29)

Different-family judges were dropped: no current outside model is a fair comparison for Qwen3.5-2B, and the question
they answer (self-bias vs difficulty) is answered more directly by changing *what the solver samples*. CPU bounds
(`sampling_cpu.py`, `runs/sampling_cpu.md`): sharpening the answer distribution (π^α, the target of power sampling and
low-temperature annealing) keeps the vote ceiling at 79.8%; moving half the attractor mass to one-off answers raises it to
83.5% (all of it: 86.7%).

| ID | Experiment | Design | GPU-h |
|---|---|---|---|
| **T1** | Importance sampling toward p^α (= E-H prefill) | Exact log p of every cached attempt (attempts were sampled at T 1, top-p 1, so weights p^(α−1) are exact). Weighted vote over α, effective sample size; contested / attractor AUROC of log p and top-1 uncertainty. Tests whether attractors are *high-likelihood* (then power sampling and MH toward p^α amplify them). | ~1 |
| **T2** | Lock-in curve (the MH resample-from-a-cut proposal) | Questions with a right attempt and an attractor: one attempt of each, cut at 25/50/75%, 4 continuations each. P(right / attractor / other) vs fresh attempts. Early lock-in → diversify early; late → restart from a cut fixes it. | ~3 |
| **T3** | Temperature as a decorrelator | 400 test × 8 at T 0.7, T 1.3 + min-p 0.05, and a hot start (1.3 for 512 tokens, then 0.8). Single accuracy, attractor share, pass@8, majority@8 vs T 1.0. | ~6 |
| **PoT** | Program-of-thought answers (also the PROVE baseline) | 4 programs per question computing the answer, executed in a sandbox. Does a different reasoning medium have a different attractor? PROVE = keep groups that a program reproduces. | ~1 |

Langevin (COLD-style continuous relaxation) and Gibbs over steps are not run: the first does not scale to 4k-token
reasoning and does not act on the answer choice; the second is not valid for a left-to-right model except as the
resample-from-a-cut move, which T2 measures. Full Karan–Du MH and particle filtering are gated on T1/T2 and on a source
with contested AUROC well above 0.6.

### Checkpoint (CPU)

**The evidence grid** (the main result). For each of the 9–11 sources, the metrics above. Then a combination: a
log-odds sum of the best two or three sources with weights fitted on dev contested questions, gated by ESC
disagreement. **Registered:** its predicted gain, then evaluated once on test ∪ extra.

### Wave 3: generality and robustness (≈ 20 GPU-h)

| ID | Experiment | GPU-h |
|---|---|---|
| **G-1** | Second benchmark: MATH-500 (100 tune / 400 eval) × 8 attempts with the 2B; then the best 3 evidence rows (cheap ones first) and the combination | ~9 |
| **G-2** | Seed: fresh 8 attempts on the 400 test questions; the best 3 evidence rows and the combination | ~7 |
| Reserve | Reruns, failed jobs, or a full MH / restart sampler if T2 shows late lock-in | ~4 |

---

## 4. Budget

| Block | GPU-h | Wall time (4 GPUs) |
|---|---|---|
| Wave 1 (E-A, B, C, D, G, H) | ~20 | ~6–7 h |
| Wave 2 (sampling T1–T3, PoT) | ~11 | ~5 h (parallel with wave 1) |
| Wave 3 (G-1, G-2) + reserve | ~20 | ~6 h |
| **Total** | **~58–60** | **~17–19 h** |

## 5. Deliverables

1. **Evidence grid** (main): contested and attractor AUROC, error correlation and gain for self, answer-only, pairwise,
   backward, executable, program-of-thought, trained judges and solver likelihood; plus the sampling results T1–T3.
2. **Shared-bias result:** self-sources fail against the solver's attractor answers; independent or checkable sources
   do not (or the honest negative if they also fail).
3. **Prediction figure:** registered predicted vs observed gain across all sources; contested AUROC (not pooled)
   explains it.
4. **Downstream table:** best combination vs majority, ESC, adaptive-consistency, CISC, DeepConf, self-certainty,
   PROVE and V1-style pairwise, at matched cost, on DeepMath and MATH-500 and across seeds.
5. **Paper update:** §6 diagnosis (difficulty, shared bias, correlation) + evidence grid; §7 downstream; §8 prediction.

## 6. Risks

| Risk | Mitigation |
|---|---|
| Executable checks unavailable for proofs or symbolic answers | Report coverage; evaluate on the checkable subset and overall |
| Pairwise prompts too long | Last 3k tokens per attempt + answer (logged deviation) |
| Hot / diverse sampling lowers per-attempt accuracy more than correlation (Nitarach 2026) | Table B of sampling_cpu gives the break-even; reported as such |
| No source beats contested AUROC 0.6 | Clean negative: self-verification is difficulty plus shared bias, and even independent checks fail on contested questions; still a strong diagnosis paper |
