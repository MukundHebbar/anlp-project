# gemma-screen: historical judge calibration

Same saved requests, DeepSeek labels, four-checkpoint fit/four-checkpoint evaluation split, 0.1-spaced threshold grid and quadratic-weighted kappa as the original calibration. No Jev or DeepSeek API calls. Native model chat formatting; otherwise the same one-token label protocol.

| Dimension | Total n | Held-out n | Raw kappa | Calibrated kappa |
|---|---:|---:|---:|---:|
| judge.M | 95 | 48 | 0.438 | 0.513 |
| judge.E | 62 | 29 | 0.565 | 0.581 |
| reconstruct.P | 83 | 40 | 0.402 | 0.508 |
| reconstruct.T | 83 | 40 | 0.671 | 0.721 |
| reconstruct.E | 83 | 40 | 0.342 | 0.399 |
| reconstruct.M | 83 | 40 | 0.566 | 0.534 |

## Total scores on held-out checkpoints

| Task | n | Pearson r | Mean absolute error /100 |
|---|---:|---:|---:|
| judge | 48 | 0.909 | 11.46 |
| reconstruct | 40 | 0.847 | 8.75 |

Held-out shortcut checks: 3 reference positives, 1 caught, 0 false positives.
The candidate is eligible for both training tasks under the initial correlation screen (JUDGE >=0.90; RECONSTRUCT >=0.80).
This tests compatibility with the original one-token recipe, not the model's best possible performance with its separately recommended critique-generation templates.

Historical calibration examples are test-derived, following the user-requested original recipe. This is checkpoint-held-out calibration, not an untouched-question test of judge generalization. Final Qwen27B calibration and evaluation remain unchanged.
