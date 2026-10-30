# Phase 3b CPU analyses (test ∪ extra, 800 questions)

## F0.4 Pooled vs within-question vs contested AUROC (higher = flags wrong attempts)

| Signal | Pooled | Within question | Contested |
|---|---|---|---|
| judge chain | 0.697 | 0.641 | 0.574 |
| judge direct | 0.732 | 0.639 | 0.559 |
| length | 0.672 | 0.585 | 0.515 |
| self-corrections | 0.655 | 0.553 | 0.522 |
| guess phrases | 0.667 | 0.585 | 0.573 |
| difficulty only (LOO solve rate) | 0.906 | 0.500 | 0.500 |

## F0.1 Shared bias: right vs the solver's attractor wrong answer vs one-off wrong answers

| Signal | right vs attractor | right vs one-off | contested: attractor | contested: one-off |
|---|---|---|---|---|
| judge chain | 0.627 (8612 pairs) | 0.659 (6558) | 0.555 | 0.678 |
| judge direct | 0.634 (8644 pairs) | 0.646 (6578) | 0.545 | 0.637 |
| length | 0.560 (8644 pairs) | 0.618 (6578) | 0.491 | 0.655 |
| self-corrections | 0.537 (8644 pairs) | 0.574 (6578) | 0.499 | 0.649 |
| guess phrases | 0.585 (8644 pairs) | 0.586 (6578) | 0.563 | 0.626 |

## F0.2 Within-answer-group error correlation (intraclass correlation of logit scores)

- judge chain: right groups 0.020 (702 groups), wrong groups 0.220 (534 groups)
- judge direct: right groups 0.282 (702 groups), wrong groups 0.749 (535 groups)

## F0.3 Difficulty share (pooled AUROC)

- pooled_auroc_difficulty_only: 0.906
- pooled_auroc_judge_chain: 0.697
- pooled_auroc_judge_direct: 0.732
- difficulty+chain: 0.914
- difficulty+direct: 0.915
- difficulty+chain+direct: 0.917

## F0.6 Free baselines (dev-tuned, test ∪ extra)

| Rule | Accuracy | Cost | vs majority at same cost |
|---|---|---|---|
| CISC-P(True) N=4 (T=2.0) | 77.3 | 4.19 | +1.04 [+0.47, +1.65] |
| CISC-P(True) N=8 (T=2.0) | 79.5 | 8.37 | +0.66 [-0.03, +1.37] |
| CISC-P(True) N=16 (T=2.0) | 80.8 | 16.75 | +0.95 [+0.05, +1.97] |
| ESC window 2 | 79.1 | 4.20 | +2.79 [+2.14, +3.50] |
| ESC window 4 | 79.8 | 8.73 | +0.82 [+0.27, +1.40] |
| ESC window 8 | 79.7 | 12.88 | +0.09 [-0.23, +0.42] |
| majority@16 | 79.8 | 16.00 | — |
