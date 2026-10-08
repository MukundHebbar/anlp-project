# pass@k report

Each eval dir holds s0 ... s<K-1>, one answer per question each. Deterministic metrics use the strict-gated
scores in s<k>/scores.jsonl:
- SOLVE: correct (single agreeing final answer, verifier v2).
- JUDGE: verdict, and verdict + first wrong step on incorrect-label questions.
Judged metrics use s<k>/judged-scores.jev.jsonl (Jev) or judged-scores.qwen.jsonl (27B) when present:
- JUDGE V/L/E/M /100 and RECONSTRUCT PC-v4 /100: mean over samples, and the best of K per question.
- RECONSTRUCT same question: in any of K samples.
pass@1 is the mean over all K samples (the expected single-sample score); pass@K is the share of questions with
at least one success among the K. "16k budget" counts answers that needed the continuation past 16k as wrong.
95% bootstrap intervals over questions (2,000 resamples).

Note: JUDGE verdict is a binary choice, so pass@K saturates even by chance (0.5 per sample gives pass@4 = 94%); read pass@1 for the verdict.

## v3-pass4-2b: Qwen/Qwen3.5-2B, test, 4 samples per question

| Metric | pass@1 (mean of samples) | pass@4 | 16k budget pass@1 |
|---|---:|---:|---:|
| SOLVE accuracy (%) (n=400) | 51.0 [47.4, 54.7] | 77.8 [73.5, 81.8] | 50.6 [47.0, 54.2] |
| JUDGE verdict (%) (n=400) | 64.3 [61.7, 67.1] | 94.8 [92.5, 96.8] | 63.1 [60.4, 65.9] |
| JUDGE first wrong step, incorrect solutions (%) (n=200) | 34.8 [30.9, 38.5] | 74.0 [68.0, 80.0] | 34.2 [30.4, 37.9] |

Judged by 27B; mean over samples and best of 4 per question:

| Metric | mean | best of 4 |
|---|---:|---:|
| JUDGE V/L/E/M /100 (n=400) | 53.9 [51.6, 56.5] | 85.0 [82.6, 87.2] |
| RECONSTRUCT PC-v4 /100 (n=400) | 40.1 [38.4, 41.9] | 61.6 [59.6, 63.6] |
| RECONSTRUCT same question (%) | 2.9 [1.9, 4.0] | 8.0 [5.5, 10.8] |

| Task | gate failures (% of answers) | mean tokens | continued past 16k (%) | still capped at 32k (%) |
|---|---:|---:|---:|---:|
| solve | 6.9 | 8089 | 2.6 | 0.1 |
| judge | 13.8 | 5087 | 4.1 | 1.4 |
| reconstruct | 12.6 | 5337 | 1.4 | 0.8 |

## v3-pass4-9b: Qwen/Qwen3.5-9B, test, 4 samples per question

| Metric | pass@1 (mean of samples) | pass@4 | 16k budget pass@1 |
|---|---:|---:|---:|
| SOLVE accuracy (%) (n=400) | 79.8 [76.4, 83.1] | 89.2 [86.0, 92.2] | 79.8 [76.4, 83.1] |
| JUDGE verdict (%) (n=400) | 87.6 [85.4, 89.7] | 97.8 [96.2, 99.0] | 85.8 [83.6, 87.9] |
| JUDGE first wrong step, incorrect solutions (%) (n=200) | 87.9 [84.9, 90.8] | 98.5 [96.5, 100.0] | 87.8 [84.8, 90.8] |

Judged by 27B; mean over samples and best of 4 per question:

| Metric | mean | best of 4 |
|---|---:|---:|
| JUDGE V/L/E/M /100 (n=400) | 85.7 [83.6, 87.7] | 97.4 [95.9, 98.6] |
| RECONSTRUCT PC-v4 /100 (n=400) | 72.7 [71.0, 74.5] | 84.7 [83.2, 86.2] |
| RECONSTRUCT same question (%) | 19.6 [16.4, 22.8] | 32.5 [28.0, 37.2] |

| Task | gate failures (% of answers) | mean tokens | continued past 16k (%) | still capped at 32k (%) |
|---|---:|---:|---:|---:|
| solve | 3.2 | 4088 | 0.1 | 0.0 |
| judge | 5.4 | 3737 | 2.6 | 2.3 |
| reconstruct | 3.8 | 3889 | 0.5 | 0.1 |

