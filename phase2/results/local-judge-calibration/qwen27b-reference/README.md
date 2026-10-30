# qwen27b-reference: historical judge calibration

Same saved requests, DeepSeek labels, four-checkpoint fit/four-checkpoint evaluation split, 0.1-spaced threshold grid and quadratic-weighted kappa as the original calibration. No Jev or DeepSeek API calls. Native model chat formatting; otherwise the same one-token label protocol.

| Dimension | Total n | Held-out n | Raw kappa | Calibrated kappa |
|---|---:|---:|---:|---:|
| judge.M | 339 | 176 | 0.805 | 0.821 |
| judge.E | 220 | 111 | 0.860 | 0.865 |
| reconstruct.P | 461 | 241 | 0.552 | 0.675 |
| reconstruct.T | 461 | 241 | 0.687 | 0.710 |
| reconstruct.E | 461 | 241 | 0.622 | 0.616 |
| reconstruct.M | 461 | 241 | 0.688 | 0.755 |

## Total scores on held-out checkpoints

| Task | n | Pearson r | Mean absolute error /100 |
|---|---:|---:|---:|
| judge | 176 | 0.938 | 7.53 |
| reconstruct | 241 | 0.803 | 8.74 |

Historical calibration examples are test-derived, following the user-requested original recipe. This is checkpoint-held-out calibration, not an untouched-question test of judge generalization. Final Qwen27B calibration and evaluation remain unchanged.
