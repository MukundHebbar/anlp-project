# Phase 3b checkpoint: evidence grid and sampling (test ∪ extra)

## Evidence grid (group level; higher AUROC = flags the wrong group)

| Source | top-2 AUROC (pairs) | coverage | right vs attractor | right vs one-off | dev top-2 |
|---|---|---|---|---|---|
| self: direct P(incorrect) | 0.677 (421) | 100% | 0.530 (100) | 0.641 (170) | 0.717 |
| trained judge (global), direct | 0.667 (421) | 100% | 0.550 (100) | 0.629 (170) | 0.774 |
| trained judge (per-question), direct | 0.663 (421) | 100% | 0.560 (100) | 0.629 (170) | 0.736 |
| combination (dev-fitted logistic, top-3 dev sources) | 0.653 (421) | 100% | 0.550 (100) | 0.659 (170) | 0.755 |
| program-of-thought agreement (PROVE) | 0.631 (183) | 43% | 0.415 (47) | 0.532 (63) | 0.583 |
| solver: -sum log p | 0.627 (421) | 100% | 0.520 (100) | 0.594 (170) | 0.623 |
| length | 0.618 (421) | 100% | 0.480 (100) | 0.618 (170) | 0.613 |
| answer-only (P no) | 0.606 (421) | 100% | 0.450 (100) | 0.482 (170) | 0.557 |
| program check (share INCORRECT) | 0.605 (110) | 26% | 0.421 (19) | 0.667 (6) | 0.580 |
| pairwise A/B | 0.587 (421) | 100% | 0.562 (64) | — (0) | 0.590 |
| self: judge chain | 0.570 (421) | 100% | 0.650 (100) | 0.600 (170) | 0.500 |
| solver: max window uncertainty | 0.561 (421) | 100% | 0.560 (100) | 0.541 (170) | 0.547 |
| solver: -mean log p | 0.537 (421) | 100% | 0.540 (100) | 0.547 (170) | 0.528 |
| solver: tail uncertainty | 0.513 (421) | 100% | 0.570 (100) | 0.553 (170) | 0.509 |
| backward check (1 - recovery) | 0.500 (1) | 0% | — (0) | — (0) | 1.000 |

Combination: trained judge (global), direct, trained judge (per-question), direct, self: direct P(incorrect); coefficients +0.22, +0.71, +0.14, +1.13 (last = intercept), fitted on 94 dev groups of contested questions.

## Downstream, ESC-2 gated (stop when the first two attempts agree): argmax n_g + w·logit(1 − suspicion), w tuned on dev

| Source | w | accuracy | vs majority [95% CI] |
|---|---|---|---|
| answer-only (P no) | 2 | 79.58 | +0.23 [-0.27, +0.74] |
| backward check (1 - recovery) | 0.25 | 79.35 | +0.00 [+0.00, +0.00] |
| length | 0.25 | 79.58 | +0.23 [-0.15, +0.65] |
| pairwise A/B | 2 | 79.89 | +0.54 [-0.19, +1.36] |
| program check (share INCORRECT) | 0.25 | 79.14 | -0.21 [-0.92, +0.48] |
| program-of-thought agreement (PROVE) | 0.25 | 79.32 | -0.03 [-0.48, +0.42] |
| self: direct P(incorrect) | 1 | 79.87 | +0.52 [-0.04, +1.13] |
| self: judge chain | 0.25 | 80.01 | +0.66 [+0.15, +1.23] |
| solver: -mean log p | 0.25 | 79.23 | -0.12 [-0.49, +0.25] |
| solver: -sum log p | 0.25 | 79.64 | +0.29 [-0.06, +0.69] |
| solver: max window uncertainty | 0.25 | 79.22 | -0.13 [-0.52, +0.27] |
| solver: tail uncertainty | 0.25 | 79.12 | -0.23 [-0.60, +0.14] |
| trained judge (global), direct | 1 | 80.07 | +0.72 [-0.01, +1.47] |
| trained judge (per-question), direct | 1 | 80.01 | +0.66 [-0.05, +1.41] |
| combination (dev-fitted logistic, top-3 dev sources) | 1 | 80.01 | +0.66 [-0.05, +1.41] |
| majority | — | 79.35 | cost 6.86 |

## Downstream, all 16 attempts (vs majority@16: beyond the vote ceiling?): argmax n_g + w·logit(1 − suspicion), w tuned on dev

| Source | w | accuracy | vs majority [95% CI] |
|---|---|---|---|
| answer-only (P no) | 2 | 80.12 | +0.35 [-0.29, +1.02] |
| backward check (1 - recovery) | 0.25 | 79.78 | +0.00 [+0.00, +0.00] |
| length | 0.25 | 80.00 | +0.23 [-0.21, +0.71] |
| pairwise A/B | 2 | 80.38 | +0.60 [-0.28, +1.58] |
| program check (share INCORRECT) | 0.25 | 79.58 | -0.19 [-1.08, +0.67] |
| program-of-thought agreement (PROVE) | 0.25 | 79.78 | +0.00 [-0.50, +0.56] |
| self: direct P(incorrect) | 1 | 80.38 | +0.60 [-0.05, +1.33] |
| self: judge chain | 0.25 | 80.50 | +0.73 [+0.14, +1.38] |
| solver: -mean log p | 0.25 | 79.62 | -0.15 [-0.59, +0.28] |
| solver: -sum log p | 0.25 | 80.12 | +0.35 [-0.06, +0.82] |
| solver: max window uncertainty | 0.25 | 79.62 | -0.15 [-0.59, +0.33] |
| solver: tail uncertainty | 0.25 | 79.50 | -0.27 [-0.71, +0.16] |
| trained judge (global), direct | 1 | 80.62 | +0.85 [+0.00, +1.70] |
| trained judge (per-question), direct | 1 | 80.50 | +0.73 [-0.13, +1.60] |
| combination (dev-fitted logistic, top-3 dev sources) | 1 | 80.50 | +0.73 [-0.13, +1.60] |
| majority | — | 79.78 | cost 16.00 |

## T1 Importance-weighted vote toward p^α (16 attempts, self-normalised)

| Target | accuracy | median ESS | share ESS < 4 |
|---|---|---|---|
| sequence alpha=1 | 79.8 | 16.00 | 0% |
| sequence alpha=1.02 | 74.6 | 1.01 | 99% |
| sequence alpha=1.05 | 74.5 | 1.00 | 100% |
| sequence alpha=1.1 | 74.5 | 1.00 | 100% |
| sequence alpha=1.25 | 74.5 | 1.00 | 100% |
| sequence alpha=1.5 | 74.5 | 1.00 | 100% |
| sequence alpha=2 | 74.5 | 1.00 | 100% |
| per-token alpha=1 | 79.8 | 16.00 | 0% |
| per-token alpha=5 | 79.4 | 15.32 | 1% |
| per-token alpha=10 | 79.8 | 13.55 | 1% |
| per-token alpha=20 | 78.1 | 9.62 | 8% |
| per-token alpha=50 | 74.0 | 3.49 | 59% |
| per-token alpha=100 | 71.6 | 1.71 | 93% |

## T2 Lock-in: continuations from a prefix (271 questions)

| Source | right | attractor | other | no answer |
|---|---|---|---|---|
| fresh attempts (cached 16) | 46.9 | 29.1 | 15.8 | 8.3 |
| attractor @ 0.25 | 41.1 | 31.4 | 20.3 | 7.2 |
| attractor @ 0.50 | 35.6 | 39.8 | 17.2 | 7.5 |
| attractor @ 0.75 | 34.2 | 42.8 | 16.1 | 6.9 |
| right @ 0.25 | 57.7 | 19.6 | 16.2 | 6.5 |
| right @ 0.50 | 56.1 | 21.3 | 15.6 | 7.0 |
| right @ 0.75 | 67.3 | 13.8 | 12.4 | 6.5 |

## Program-of-thought as a second voter (403 questions, 4 programs each)

- language plurality is a single wrong group on 62 questions; there the PoT plurality differs from it 73% of the time and is right 6% of the time
- PoT plurality alone: 36.7%
- majority@16 + PoT votes (weight 0.5, tuned on dev): 81.47 vs 81.47, +0.00 [-0.37, +0.37]

## T3 Temperature (400 test questions × 8)

| Sampler | questions | single | attractor share | pass@8 | majority@8 | Δ majority vs T 1.0 (mean of both cached draws) [95% CI] |
|---|---|---|---|---|---|---|
| T 1.0 (cached, attempts 0-7) | 400 | 67.1 | 17.6 | 87.2 | 77.2 | — |
| T 1.0 (cached, attempts 8-15) | 400 | 68.0 | 17.6 | 86.2 | 78.0 | — |
| T 0.7 | 400 | 68.0 | 15.7 | 90.8 | 79.1 | +1.43 [-0.84, +3.89] (base 77.6) |
| T 1.3, min-p 0.05 | 400 | 67.8 | 17.2 | 88.5 | 75.3 | -2.30 [-4.29, -0.36] (base 77.6) |
| hot start (1.3 → 0.8) | 400 | 67.8 | 16.7 | 88.5 | 78.8 | +1.15 [-1.06, +3.22] (base 77.6) |
