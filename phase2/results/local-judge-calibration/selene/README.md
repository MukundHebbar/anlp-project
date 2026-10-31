# selene: historical judge calibration

Same saved requests, DeepSeek labels, four-checkpoint fit/four-checkpoint evaluation split, 0.1-spaced threshold grid and quadratic-weighted kappa as the original calibration. No Jev or DeepSeek API calls. Native model chat formatting; otherwise the same one-token label protocol.

| Dimension | Total n | Held-out n | Raw kappa | Calibrated kappa |
|---|---:|---:|---:|---:|
| judge.M | 339 | 176 | 0.717 | 0.721 |
| judge.E | 220 | 111 | 0.560 | 0.552 |
| reconstruct.P | 461 | 241 | 0.440 | 0.529 |
| reconstruct.T | 461 | 241 | 0.247 | 0.374 |
| reconstruct.E | 461 | 241 | 0.190 | 0.324 |
| reconstruct.M | 461 | 241 | 0.432 | 0.561 |

## Total scores on held-out checkpoints

| Task | n | Pearson r | Mean absolute error /100 |
|---|---:|---:|---:|
| judge | 176 | 0.913 | 9.45 |
| reconstruct | 241 | undefined (constant scores) | 45.15 |

Held-out shortcut checks: 9 reference positives, 9 caught, 232 false positives.
The candidate is not eligible for both training tasks under the initial correlation screen (JUDGE >=0.90; RECONSTRUCT >=0.80).
This tests compatibility with the original one-token recipe, not the model's best possible performance with its separately recommended critique-generation templates.

Historical calibration examples are test-derived, following the user-requested original recipe. This is checkpoint-held-out calibration, not an untouched-question test of judge generalization. Final Qwen27B calibration and evaluation remain unchanged.
