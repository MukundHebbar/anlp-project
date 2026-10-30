# selene-screen-reference: historical judge calibration

Same saved requests, DeepSeek labels, four-checkpoint fit/four-checkpoint evaluation split, 0.1-spaced threshold grid and quadratic-weighted kappa as the original calibration. No Jev or DeepSeek API calls. Native model chat formatting; otherwise the same one-token label protocol.

| Dimension | Total n | Held-out n | Raw kappa | Calibrated kappa |
|---|---:|---:|---:|---:|
| judge.M | 95 | 48 | 0.601 | 0.687 |
| judge.E | 62 | 29 | 0.399 | 0.363 |
| reconstruct.P | 96 | 48 | 0.263 | 0.354 |
| reconstruct.T | 96 | 48 | 0.129 | 0.374 |
| reconstruct.E | 96 | 48 | 0.204 | 0.299 |
| reconstruct.M | 96 | 48 | 0.283 | 0.592 |

## Total scores on held-out checkpoints

| Task | n | Pearson r | Mean absolute error /100 |
|---|---:|---:|---:|
| judge | 48 | 0.884 | 11.59 |
| reconstruct | 48 | undefined (constant scores) | 42.32 |

Held-out shortcut checks: 4 reference positives, 4 caught, 44 false positives.
The candidate is not eligible for both training tasks under the initial correlation screen (JUDGE >=0.90; RECONSTRUCT >=0.80).
This tests compatibility with the original one-token recipe, not the model's best possible performance with its separately recommended critique-generation templates.

Historical calibration examples are test-derived, following the user-requested original recipe. This is checkpoint-held-out calibration, not an untouched-question test of judge generalization. Final Qwen27B calibration and evaluation remain unchanged.
