# selene-interim: historical judge calibration

Same saved requests, DeepSeek labels, four-checkpoint fit/four-checkpoint evaluation split, 0.1-spaced threshold grid and quadratic-weighted kappa as the original calibration. No Jev or DeepSeek API calls. Native model chat formatting; otherwise the same one-token label protocol.

| Dimension | Total n | Held-out n | Raw kappa | Calibrated kappa |
|---|---:|---:|---:|---:|
| judge.M | 34 | 15 | 0.899 | 0.747 |
| judge.E | 28 | 11 | 0.439 | 0.522 |
| reconstruct.P | 56 | 26 | 0.311 | 0.294 |
| reconstruct.T | 56 | 26 | 0.167 | 0.256 |
| reconstruct.E | 56 | 26 | 0.428 | 0.598 |
| reconstruct.M | 56 | 26 | 0.693 | 0.761 |

## Total scores on held-out checkpoints

| Task | n | Pearson r | Mean absolute error /100 |
|---|---:|---:|---:|
| judge | 15 | 0.972 | 7.08 |
| reconstruct | 26 | undefined (constant scores) | 44.23 |

Held-out shortcut checks: 2 reference positives, 2 caught, 24 false positives.
The candidate is not eligible for both training tasks under the initial correlation screen (JUDGE >=0.90; RECONSTRUCT >=0.80).
This tests compatibility with the original one-token recipe, not the model's best possible performance with its separately recommended critique-generation templates.

Historical calibration examples are test-derived, following the user-requested original recipe. This is checkpoint-held-out calibration, not an untouched-question test of judge generalization. Final Qwen27B calibration and evaluation remain unchanged.
