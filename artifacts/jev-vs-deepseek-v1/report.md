# Jev vs DeepSeek on the FINAL-v3 test evaluations

Jev `jev-1.13.0` re-scored the 8 saved checkpoints in `artifacts/baselines/final-v3/test/matrix-*`. DeepSeek V4.1 Flash scores are the saved `judged-scores.jsonl`. They are a reference, not ground truth. Item-level numbers use items both judges scored.

## JUDGE: item level (3190 responses from 8 checkpoints)

| Dim | Exact | Mode baseline | Within 1 | Weighted κ | Spearman | MAE | DeepSeek mean | Jev mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V | 94% | 59% | 94% | 0.87 | 0.88 | 0.25 | 2.36 | 2.12 |
| L | 91% | 55% | 91% | 0.85 | 0.80 | 0.31 | 1.72 | 1.54 |
| E | 81% | 54% | 87% | 0.80 | 0.78 | 0.45 | 1.57 | 1.54 |
| M | 49% | 33% | 82% | 0.62 | 0.79 | 0.72 | 1.86 | 2.45 |

- Total 0–100: Pearson 0.87, Spearman (weighted) 0.87, MAE 10.2; means DeepSeek 46.9 vs Jev 47.8. 1–5 rating (v4) exact agreement 79%.
- Scored by Jev but unresolved by DeepSeek: 10. Inputs shortened for length: 4.

### JUDGE: checkpoint level

| Checkpoint | n | DeepSeek mean | Jev mean | Δ vs base, DeepSeek [95% CI] | Δ vs base, Jev [95% CI] |
|---|---:|---:|---:|---:|---:|
| base | 398 | 46.5 | 48.6 | — | — |
| opd-judge-s104 | 399 | 50.9 | 51.0 | +4.3 [+0.6, +8.2] | +2.4 [-1.1, +5.8] |
| opd-judge-s52 | 396 | 47.8 | 47.7 | +1.0 [-2.8, +4.9] | -1.2 [-4.7, +2.4] |
| opd-reconstruct-s104 | 398 | 43.5 | 45.5 | -3.0 [-6.2, +0.4] | -3.2 [-6.0, -0.6] |
| opd-reconstruct-s52 | 400 | 44.0 | 46.2 | -2.6 [-5.7, +0.5] | -2.4 [-5.1, +0.2] |
| opd-solve-s52 | 400 | 49.1 | 47.2 | +2.5 [-0.5, +5.6] | -1.4 [-3.7, +1.0] |
| sft-judge | 399 | 50.5 | 51.0 | +4.1 [+0.4, +7.7] | +2.6 [-0.1, +5.5] |
| sft-reconstruct | 400 | 43.2 | 45.2 | -3.3 [-6.6, +0.0] | -3.4 [-6.3, -0.5] |

- Checkpoint ranking, Kendall τ (DeepSeek vs Jev means): 0.71.

### JUDGE: same question, different checkpoints

For each question, every pair of checkpoint answers that DeepSeek scored differently (8489 pairs): Jev orders them the same way 57.3%, the opposite way 7.3%, and gives a tie 35.4%. On close pairs (DeepSeek within 12.5 points, 4130 pairs): same 39.0%, opposite 9.2%. This is the comparison a GRPO reward makes inside a group of samples.

## RECONSTRUCT: item level (2380 responses from 8 checkpoints)

| Dim | Exact | Mode baseline | Within 1 | Weighted κ | Spearman | MAE | DeepSeek mean | Jev mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P | 70% | 41% | 91% | 0.66 | 0.78 | 0.41 | 1.95 | 1.70 |
| T | 59% | 33% | 86% | 0.68 | 0.79 | 0.57 | 2.26 | 2.00 |
| E | 61% | 60% | 90% | 0.55 | 0.64 | 0.49 | 1.86 | 2.07 |
| M | 72% | 64% | 95% | 0.63 | 0.69 | 0.37 | 0.94 | 1.12 |

- Total 0–100: Pearson 0.77, Spearman (weighted) 0.80, MAE 9.7; means DeepSeek 40.9 vs Jev 41.4. 1–5 rating (v4) exact agreement 56%.
- Scored by Jev but unresolved by DeepSeek: 550. Inputs shortened for length: 36.
- Shortcut flags: DeepSeek 218, Jev 104, agreement 93.8%. Same question: DeepSeek 173, Jev P4∧T4 144 (both 115), Jev yes/no 252.

### RECONSTRUCT: checkpoint level

| Checkpoint | n | DeepSeek mean | Jev mean | Δ vs base, DeepSeek [95% CI] | Δ vs base, Jev [95% CI] |
|---|---:|---:|---:|---:|---:|
| base | 312 | 37.3 | 39.3 | — | — |
| opd-judge-s104 | 309 | 40.6 | 41.0 | +2.6 [-0.7, +5.7] | +0.2 [-2.7, +2.9] |
| opd-judge-s52 | 274 | 40.4 | 39.9 | +5.3 [+1.8, +8.5] | +1.3 [-1.3, +3.8] |
| opd-reconstruct-s104 | 329 | 42.4 | 40.3 | +3.9 [+1.0, +6.8] | +0.8 [-1.7, +3.3] |
| opd-reconstruct-s52 | 310 | 46.5 | 45.9 | +9.9 [+6.4, +13.3] | +7.0 [+4.3, +9.9] |
| opd-solve-s52 | 298 | 39.9 | 40.6 | +3.4 [+0.6, +6.1] | +1.9 [-0.6, +4.4] |
| sft-judge | 268 | 37.7 | 38.9 | +2.0 [-1.7, +5.7] | +0.6 [-2.2, +3.7] |
| sft-reconstruct | 280 | 41.9 | 45.6 | +5.0 [+1.3, +8.5] | +6.5 [+3.8, +9.2] |

- Checkpoint ranking, Kendall τ (DeepSeek vs Jev means): 0.64.

### RECONSTRUCT: same question, different checkpoints

For each question, every pair of checkpoint answers that DeepSeek scored differently (5327 pairs): Jev orders them the same way 69.5%, the opposite way 13.9%, and gives a tie 16.6%. On close pairs (DeepSeek within 12.5 points, 2313 pairs): same 53.8%, opposite 21.3%. This is the comparison a GRPO reward makes inside a group of samples.

