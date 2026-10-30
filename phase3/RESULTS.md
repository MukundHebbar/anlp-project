# Phase 3 results (live)

Theory: `docs/research/verification-theory/theory-and-plan.md`. Protocol: `PREREGISTRATION.md`. Full numbers:
`runs/analysis/report.md` (generated). Paper: `paper/`.

**Data.** Qwen3.5-2B + `mixed-step75`, 16 attempts per question (T 1.0, 16k cap):

| Set | Questions | Attempts | Single-attempt accuracy |
|---|---|---|---|
| dev | 200 | 3,200 | 69.8% |
| test | 400 | 6,400 | 67.0% |
| extra | 400 | 6,400 | 68.2% |
| train (Stage 2) | 450 | 7,200 | 69.5% |

All dev/test/extra attempts were judged by the same adapter. Test attempts 0–3 have 4 chains each.

## Reproduction and model validation

- **Pipeline matches Phase 2.** Dev 69.8 / 86.3 / 78.1 (single / pass@4 / majority@4; Phase 2: 69.8 / 86.5 / 77.5).
  Test 67.0 / 82.8 / 74.9 (Phase 2: 67.4 / 82.8 / 74.0).
- **Model predicts the scaling curves.** The model is fitted only to Phase-2 4-attempt aggregates.

  | Test | Predicted | Observed |
  |---|---|---|
  | Majority@8 | 77.5 | 77.5 |
  | Majority@16 | 78.2 | 78.7 |
  | pass@16 | 90.8 | 90.2 |
  | Configurations: majority right / unwinnable | 71.7% / 17.2% | 72.3% / 17.3% |

## Stage 0 (test attempts 0–3, 4 chains; 1,486 attempts)

**Lenient judge.** 15.4% "incorrect" verdicts; H = 0.255, F = 0.125, d′ = 0.49.

| Scoring | AUROC |
|---|---|
| 1 sampled verdict | 0.565 |
| Share of 4 sampled verdicts | 0.635 |
| Verdict probability, 1 chain | 0.689 |
| Verdict probability, mean of 4 chains | 0.694 |
| Direct probability (no reasoning) | 0.717 |

**P-0a confirmed.** Paired over questions:
- probability (4 chains) − sampled share (4): **+0.067 [+0.047, +0.085]**;
- direct − sampled share: **+0.090 [+0.049, +0.130]**;
- one chain's probability − sampled share (4): **+0.062 [+0.029, +0.090]**.

**P-0c confirmed.** P(4 of 4 "incorrect" | wrong) = 4.2% vs 0.35% for independent verdicts (12×).

The model's latent AUROC, inferred from Phase-2 flag rates alone, was 0.715. Probability scoring recovers 0.69–0.72.

## Pooled vs within vs contested (all 16 attempts; chain / direct)

| Set | Pooled | Within | Contested within |
|---|---|---|---|
| dev | 0.692 / 0.730 | 0.620 / 0.634 | 0.612 / 0.596 |
| test | 0.682 / 0.718 | 0.611 / 0.614 | **0.511 / 0.469** |
| extra | 0.713 / 0.746 | 0.668 / 0.661 | 0.631 / 0.641 |

**Judge-free trace features** (test; pooled / within / contested):
- length: 0.655 / 0.573 / 0.486;
- self-corrections: 0.648 / 0.553 / 0.514;
- guess phrases: 0.656 / 0.576 / 0.568.

So trace features alone reach the Phase-2 trained self-judge's pooled AUROC (0.665) and are at chance on contested
questions. 98–99% of right attempts contain self-corrections (about 25 per attempt).

## Stage 1 (test ∪ extra, 800 questions; dev-tuned)

- **Vote-only plateau.** Majority@16 79.8%; adaptive-consistency 79.8% at 10.4 attempts; pass@16 91.4%.
- **Primary (pre-registered).** CAV-chain (N₁ = 16, m = 8, β = 2.0) reaches 81.0% at 11.3 units.
  - Against majority at the same cost: **+1.59 [+0.51, +2.59]**.
  - At matched decoded tokens: **+1.42 [+0.35, +2.45]**.
  - Against adaptive-consistency: **+1.22 [+0.05, +2.28]**.
  - The registered prediction for dev within-question AUROC 0.62–0.63 was about +1.3.
- **Cheap CAV-direct** (N₁ = 8, m = 4): 79.2% at 6.1 units; **+1.35 [+0.84, +1.88]** over majority at the same cost.
  Adaptive-consistency is on par at that budget.
- **Argmax@16 is 76.7%, below majority@16 (79.8%).** Bayes aggregation@16 reaches 80.9% at 20.5 units.
- **Exploratory learned combiner.** Within-question AUROC rises (extra 0.717, test 0.666) with no CAV gain.

## Mechanism checks (test ∪ extra; `runs/mechanisms.json`)

- **By solve rate:** within-question AUROC is lowest at 4–7 right out of 16 (0.57–0.59, the contested region) and
  0.65–0.68 elsewhere.
- **By length** (4k to over 12k tokens) and **by self-correction count:** no degradation. The length law's
  short-vs-long contrast (Phase 2) is outside this range.

## Stage 2 (trained, not evaluated)

- **Arms:** `global` (Phase-2 replica, 410 questions) and `perq` (per-question balanced, 271 questions). 1,024 prompts
  each; Dr. GRPO 32 × 32 × 8, lr 1e-5, from `mixed-step75`.
- **Training:** verdict reward 40% → 57% (global) and 48% → 53% (perq); response length 3.9k → 1.2k and
  4.2k → 1.6k; truncation → 0.
- **Not done:** the evaluation of both arms on the selection pools, and direct scoring with the base, SOLVE and JUDGE
  adapters. Both were cancelled on 2026-10-29 by the user's decision; they are not needed for the paper's claims.
- **Adapters (steps 8/16/24/32):** `~/anlp-project/runs-out/p3-sj2-{global,perq}/adapters/` on Turing.

## Phase 3b checkpoint: evidence grid and sampling (2026-10-29; `runs/evidence_grid.{md,json}`)

Wave 1 and the sampling wave (replacing the Gemma judges) ran on Turing node09, 4 × L40S, about 18 GPU-hours. Every
number below is on test ∪ extra (800 questions) unless stated. Dev was used only for choosing w, λ and the combination.
Generator: `evidence_grid.py`. Three jobs show FAILED in Slurm only because `wave1.sh` was replaced while they ran
("Stale file handle" after the last step); every output chunk is complete. The dev and test program checks ran under the
earlier denylist-only sandbox; the later kinds ran in user/mount/network namespaces (`sandbox.py`).

**Evidence grid** (group level; P(wrong group scored more suspicious)). *Top-2* = questions whose two largest groups
are one right and one wrong (421). *Attractor* = right vs the largest wrong group (≥ 2 attempts) on contested questions
(100). *One-off* = right vs single-attempt wrong groups (170).

| Source | top-2 | coverage | vs attractor | vs one-off |
|---|---|---|---|---|
| self, direct P(incorrect) | **0.677** | 100% | 0.530 | 0.641 |
| trained judge (global), direct | 0.667 | 100% | 0.550 | 0.629 |
| trained judge (per-question), direct | 0.663 | 100% | 0.560 | 0.629 |
| combination (registered; dev-fitted) | 0.653 | 100% | 0.550 | 0.659 |
| program-of-thought agreement (PROVE) | 0.631 | 43% | 0.415 | 0.532 |
| solver −sum log p | 0.627 | 100% | 0.520 | 0.594 |
| length | 0.618 | 100% | 0.480 | 0.618 |
| answer-only (E-A) | 0.606 | 100% | 0.450 | 0.482 |
| program check (E-D) | 0.605 | 26% | 0.421 | — (6 pairs) |
| pairwise A/B (E-B, both orders) | 0.587 | 100% | 0.562 | — |
| self, judge chain | 0.570 | 100% | **0.650** | 0.600 |
| solver max-window uncertainty (DeepConf) | 0.561 | 100% | 0.560 | 0.541 |
| solver −mean log p | 0.537 | 100% | 0.540 | 0.547 |
| solver tail uncertainty | 0.513 | 100% | 0.570 | 0.553 |
| backward check (E-C) | — | 0% | — | — |

- **The attractor column is the finding.** No source separates the right group from the attractor by much.
  - The best is the self judge chain at 0.65 (n = 100, wide CI); everything else is 0.42–0.56.
  - The non-self checks (programs, PoT, answer-only) *favour* the attractor: 0.42–0.45.
  - Sources that do well on top-2 do it by flagging one-off wrong answers, which majority voting already handles.
- **Training the judge** (Stage 2, both arms) gives the same picture as the untrained direct read: 0.67 top-2, 0.55
  against the attractor.
- **The backward check is infeasible here:** 97% of the inverse-problem attempts hit the 4k cap (42 of 1,488 finished).
- **The program check** produces a CORRECT/INCORRECT verdict for only 26% of top-2 pairs; programs are truncated or
  uncheckable.

**Downstream** (argmax n_g + w·logit(1 − suspicion), w tuned on dev; paired bootstrap 95% CI vs majority):

| Rule | ESC-2 gated (majority 79.35, cost 6.9) | all 16 (majority@16 79.78) |
|---|---|---|
| trained judge (global) | +0.72 [−0.01, +1.47] | +0.85 [+0.00, +1.70] |
| self judge chain | +0.66 [+0.15, +1.23] | +0.73 [+0.14, +1.38] |
| combination (registered) | +0.66 [−0.05, +1.41] | +0.73 [−0.13, +1.60] |
| self direct | +0.52 [−0.04, +1.13] | +0.60 [−0.05, +1.33] |
| pairwise A/B | +0.54 [−0.19, +1.36] | +0.60 [−0.28, +1.58] |
| answer-only / −sum log p / length | +0.2 to +0.3 (CIs include 0) | +0.2 to +0.35 |
| program check / PoT / uncertainty | −0.2 to 0 | −0.3 to 0 |

The ceiling (right answer is the plurality: 79.8%; right answer present: 91.4%) moves by at most about +0.9 points.
That is roughly 8% of the 11.6 points where the right answer is present but outvoted.

**Sampling.**

- **T1, importance-weighted vote toward p^α.** On the cached attempts (sampled at T 1, so the weights are exact):
  - Whole-sequence weights degenerate immediately. Median ESS is 1.0 already at α = 1.02, and accuracy falls from
    79.8 to 74.5.
  - Per-token (length-normalised) weights keep ESS above 4 only up to α ≈ 20 and never beat plain majority: 79.8 →
    79.4 / 79.8 / 78.1 at α = 5 / 10 / 20.
  - The solver's own likelihood does not rank the right answer above the attractor (vs attractor 0.52), so
    sharpening toward p^α, the target of MH power sampling, cannot help here.
- **T2, lock-in** (271 questions; 4 continuations per prefix):

  | Prefix taken from | right | attractor | other | none |
  |---|---|---|---|---|
  | fresh attempts | 46.9 | 29.1 | 15.8 | 8.3 |
  | attractor attempt, cut at 25 / 50 / 75% | 41.1 / 35.6 / 34.2 | 31.4 / 39.8 / 42.8 | 20.3 / 17.2 / 16.1 | 7.2 / 7.5 / 6.9 |
  | right attempt, cut at 25 / 50 / 75% | 57.7 / 56.1 / 67.3 | 19.6 / 21.3 / 13.8 | 16.2 / 15.6 / 12.4 | 6.5 / 7.0 / 6.5 |

  - Lock-in is gradual and partial. From an attractor prefix cut at 25%, outcomes are close to fresh attempts. Even
    at 75%, a third of continuations recover the right answer.
  - The attractor is not decided by the first tokens. It is assembled over the reasoning, so restarting from early
    cuts (the MH proposal) mostly re-samples the question's own distribution, attractor included.
- **T3, temperature** (400 test questions × 8; Δ majority@8 is paired against the mean of the two cached T 1.0
  draws, 77.6):

  | Sampler | single | attractor share | pass@8 | majority@8 | Δ [95% CI] |
  |---|---|---|---|---|---|
  | T 1.0 (cached 0–7 / 8–15) | 67.1 / 68.0 | 17.6 / 17.6 | 87.2 / 86.2 | 77.2 / 78.0 | — |
  | T 0.7 | 68.0 | 15.7 | 90.8 | 79.1 | +1.43 [−0.84, +3.89] |
  | hot start (T 1.3 / min-p 0.05 for 512 tokens, then T 0.8) | 67.8 | 16.7 | 88.5 | 78.8 | +1.15 [−1.06, +3.22] |
  | T 1.3, min-p 0.05 | 67.8 | 17.2 | 88.5 | 75.3 | **−2.30 [−4.29, −0.36]** |

  - Heating the whole attempt hurts.
  - Cooling, or heating only the opening, nudges the attractor share down by about 1–2 points and majority@8 up by
    about 1, but within noise. This is the decorrelation lever that `sampling_cpu.py` priced at +1.5 points of
    ceiling for δ = 0.25; the samplers tested reach less than that.
- **Program-of-thought as a second voter.**
  - Where the language plurality is a single wrong group (62 questions), the PoT plurality differs from it 73% of the
    time, but is right only 6% of the time.
  - PoT alone gets 36.7%, and mixing its votes into majority@16 changes nothing (+0.00).
  - A different medium gives a different error, not a right answer.

**Registered predictions** (`PREREGISTRATION.md`, Phase 3b):

1. **Shared bias, confirmed** for the direct, trained, answer-only and pairwise self sources (0.45–0.56 vs the attractor
   ≤ 0.58). The exception is the self judge chain at 0.65 (n = 100).
2. **T1, confirmed:**
   - log p does not favour the right group (0.52);
   - the importance-weighted vote gains nothing (it loses up to 5 points);
   - ESS < 4 for α ≥ 2 (sequence) and α ≥ 50 (per-token).
3. **T2, confirmed:** lock-in grows with prefix length.
4. **T3, confirmed for T 0.7 and the hot start** (+1.4 and +1.2, within ±1.5). **Not confirmed for T 1.3:** −2.3,
   outside the band.
5. **PoT, confirmed** (differs 73% of the time); it does not help.
6. **Combination, confirmed:** +0.73 with CI including 0. No non-self source reached top-2 AUROC 0.65.

**Conclusion for the checkpoint.** Every lever tested leaves the vote ceiling essentially where it is:
- reading the attempts (twelve sources and their combination);
- sharpening (T1);
- re-sampling from a prefix (T2);
- temperature (T3);
- a second reasoning medium (PoT).

The gap between "right answer is present" (91%) and "right answer wins" (80%) is held by attractors that the model's
own signals cannot tell apart from the truth. The reserve full MH / restart sampler is not justified: T2 shows no early
lock-in to exploit, and T1 shows the target p^α is not better than p.
