# Jev vs DeepSeek agreement on saved Qwen3-4B responses

Jev model `jev-1.13.0`. DeepSeek V4.1 Flash scores are the existing saved ratings, not ground truth.
Exact/within-1 use Jev's most probable level; Spearman uses Jev's probability-weighted score.

## JUDGE (78 items)

| Dim | Exact | Mode baseline | Within 1 | Weighted κ | Spearman | MAE | DeepSeek mean | Jev mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V | 99% | 65% | 99% | 0.97 | 0.97 | 0.05 | 2.62 | 2.56 |
| L | 97% | 54% | 97% | 0.97 | 0.87 | 0.08 | 2.18 | 2.15 |
| E | 90% | 44% | 94% | 0.95 | 0.91 | 0.18 | 1.92 | 1.95 |
| M | 64% | 46% | 86% | 0.75 | 0.88 | 0.54 | 2.46 | 3.00 |

- Total 0–100: Pearson 0.98, Spearman (weighted) 0.93, MAE 5.0; means DeepSeek 57.4 vs Jev 60.4. 1–5 rating (v4) exact agreement 92%.
- Jev's read of the student's decision matches the regex parser on 92.3%; named step matches on 100.0%.
- Verdict accuracy: parser 67.9%, DeepSeek 65.4%, Jev 64.1%.

## RECONSTRUCT A: source-blind validity (same as DeepSeek) (100 items)

| Dim | Exact | Mode baseline | Within 1 | Weighted κ | Spearman | MAE | DeepSeek mean | Jev mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P | 68% | 66% | 89% | 0.41 | 0.51 | 0.45 | 2.20 | 2.05 |
| T | 43% | 47% | 81% | 0.54 | 0.63 | 0.78 | 2.76 | 2.46 |
| E | 72% | 74% | 86% | 0.41 | 0.46 | 0.42 | 2.17 | 2.45 |
| M | 76% | 48% | 100% | 0.78 | 0.75 | 0.24 | 0.61 | 0.67 |

- Total 0–100: Pearson 0.77, Spearman (weighted) 0.66, MAE 8.1; means DeepSeek 44.6 vs Jev 44.5. 1–5 rating (v4) exact agreement 53%.
- Shortcut flags: DeepSeek 9, Jev 8, both 8; agreement 99.0%.
- Semantic equivalence: DeepSeek 2; Jev yes/no question 14 (both 2); Jev P4 and T4 4 (both 2).

## RECONSTRUCT B: validity judge also sees the source (100 items)

| Dim | Exact | Mode baseline | Within 1 | Weighted κ | Spearman | MAE | DeepSeek mean | Jev mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E | 63% | 74% | 80% | 0.24 | 0.41 | 0.58 | 2.17 | 2.53 |
| M | 72% | 48% | 99% | 0.70 | 0.63 | 0.29 | 0.61 | 0.66 |

- Total 0–100: Pearson 0.78, Spearman (weighted) 0.61, MAE 9.1; means DeepSeek 44.6 vs Jev 44.7. 1–5 rating (v4) exact agreement 45%.
- Shortcut flags: DeepSeek 9, Jev 9, both 9; agreement 100.0%.
- Semantic equivalence: DeepSeek 2; Jev yes/no question 14 (both 2); Jev P4 and T4 4 (both 2).
