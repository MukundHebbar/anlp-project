# Qwen3.8-27B judge calibration against DeepSeek

Cutoffs on the probability-weighted level; held-out = fitted on 4 checkpoints, tested on the other 4. Jev's held-out numbers for comparison: JUDGE M 0.88, RECONSTRUCT P 0.68, T 0.74, E 0.63, M 0.72.

| Dimension | n | held-out κ (nearest level) | held-out κ (calibrated) | mean DeepSeek / 27B |
|---|---:|---:|---:|---|
| judge.M | 339 | 0.81 | 0.82 | 1.99 / 1.88 |
| judge.E | 220 | 0.86 | 0.87 | 2.75 / 2.72 |
| reconstruct.P | 461 | 0.55 | 0.68 | 2.06 / 1.94 |
| reconstruct.T | 461 | 0.69 | 0.71 | 2.34 / 2.32 |
| reconstruct.E | 461 | 0.62 | 0.62 | 2.00 / 1.95 |
| reconstruct.M | 461 | 0.69 | 0.76 | 1.06 / 0.98 |

Shortcut stage (answers that pass the gate): DeepSeek flags 14, 27B catches 8, extra flags 6.
Label probability mass: median 0.977.

## Manual spot check (2026-10-06)

30 stratified answers from the 2B baseline, sample 0: 8 scored, 4 shortcut and 3 gated RECONSTRUCT; 10 scored
and 5 gated JUDGE. **28 of 30 judgments look right.**

Debatable:
- reconstruct-60022: the coefficient of x^10 with the x^3 factor dropped got T2; T4 is arguable, since the
  requested coefficient is the same.
- reconstruct-57531: answer "B" against a convoluted but genuine question was flagged as a shortcut; this is
  likely a false positive.

All 5 gated JUDGE answers contain conflicting Decision lines. The template echo
"First wrong step: the step ID" is correctly ignored.

## Total-score agreement on held-out checkpoints (the decision that matters)

| | JUDGE r / rating exact | RECONSTRUCT r / rating exact |
|---|---|---|
| Qwen3.8-27B | 0.940 / 91% | 0.840 / 62% |
| Jev | 0.939 / 88% | 0.849 / 65% |

Adopted as the final test judge.
