# gemma-full-explicit: historical judge calibration

Same saved requests, DeepSeek labels, four-checkpoint fit/four-checkpoint evaluation split, 0.1-spaced threshold grid and quadratic-weighted kappa as the original calibration. No Jev or DeepSeek API calls. Native model chat formatting; otherwise the same one-token label protocol.

| Dimension | Total n | Held-out n | Raw kappa | Calibrated kappa |
|---|---:|---:|---:|---:|
| judge.M | 339 | 176 | 0.505 | 0.636 |
| judge.E | 220 | 111 | 0.747 | 0.773 |
| reconstruct.P | 461 | 241 | 0.584 | 0.673 |
| reconstruct.T | 461 | 241 | 0.536 | 0.651 |
| reconstruct.E | 461 | 241 | 0.350 | 0.547 |
| reconstruct.M | 461 | 241 | 0.564 | 0.643 |

## Total scores on held-out checkpoints

| Task | n | Pearson r | Mean absolute error /100 |
|---|---:|---:|---:|
| judge | 176 | 0.930 | 8.84 |
| reconstruct | 241 | 0.778 | 9.91 |

Held-out shortcut checks: 9 reference positives, 3 caught, 1 false positives.
The candidate is not eligible for both training tasks under the initial correlation screen (JUDGE >=0.90; RECONSTRUCT >=0.80).
This tests compatibility with the original one-token recipe, not the model's best possible performance with its separately recommended critique-generation templates.

Historical calibration examples are test-derived, following the user-requested original recipe. This is checkpoint-held-out calibration, not an untouched-question test of judge generalization. Final Qwen27B calibration and evaluation remain unchanged.
