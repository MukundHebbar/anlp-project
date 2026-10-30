# qwen27b-screen-reference: historical judge calibration

Same saved requests, DeepSeek labels, four-checkpoint fit/four-checkpoint evaluation split, 0.1-spaced threshold grid and quadratic-weighted kappa as the original calibration. No Jev or DeepSeek API calls. Native model chat formatting; otherwise the same one-token label protocol.

| Dimension | Total n | Held-out n | Raw kappa | Calibrated kappa |
|---|---:|---:|---:|---:|
| judge.M | 95 | 48 | 0.767 | 0.757 |
| judge.E | 62 | 29 | 0.820 | 0.890 |
| reconstruct.P | 96 | 48 | 0.342 | 0.616 |
| reconstruct.T | 96 | 48 | 0.698 | 0.741 |
| reconstruct.E | 96 | 48 | 0.693 | 0.735 |
| reconstruct.M | 96 | 48 | 0.613 | 0.710 |

## Total scores on held-out checkpoints

| Task | n | Pearson r | Mean absolute error /100 |
|---|---:|---:|---:|
| judge | 48 | 0.931 | 8.59 |
| reconstruct | 48 | 0.814 | 7.81 |

Held-out shortcut checks: 4 reference positives, 2 caught, 1 false positives.
The candidate is eligible for both training tasks under the initial correlation screen (JUDGE >=0.90; RECONSTRUCT >=0.80).
This tests compatibility with the original one-token recipe, not the model's best possible performance with its separately recommended critique-generation templates.

Historical calibration examples are test-derived, following the user-requested original recipe. This is checkpoint-held-out calibration, not an untouched-question test of judge generalization. Final Qwen27B calibration and evaluation remain unchanged.
