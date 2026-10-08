# Dr. GRPO transfer matrix (Qwen3.5-2B, FINAL-v3 test)

Eval folders (eval_matrix.py layout, s0 ... s<K-1>) under artifacts/baselines/final-v3/test/:
  v3-pass4-2b                  the untrained 2B (4 samples on every task)
  v3-drgrpo-<task>-step<k>     trained arms (SOLVE 4 samples, JUDGE and RECONSTRUCT 1)
Which step is "selected" comes from artifacts/opd/evals/v3-drgrpo-dev/selection.json; step 104 is the fixed
endpoint. JUDGE headline: step % (on a solution with an error, verdict "incorrect" AND the exact first wrong step;
always answering one verdict cannot score), false alarm % (a correct solution called incorrect; lower is better)
and Youden's J (verdict accuracy on incorrect keys + on correct keys - 100; 0 for a one-verdict model; on this
balanced 200/200 test set it equals 2 x verdict accuracy - 100).
Per question, a model's value is the mean over its samples (pass@1), so a 4-sample baseline and a
1-sample checkpoint estimate the same expected single-sample score. Deterministic metrics use the strict gates;
JUDGE V/L/E/M and RECONSTRUCT PC-v4 use the Qwen3.8-27B judge (judged-scores.qwen.jsonl). Δ is paired on the
same questions; 95% bootstrap intervals over questions (2,000 resamples).

## Scores (pass@1 unless noted)

| Model | SOLVE acc % | SOLVE pass@4 % | JUDGE verdict % | JUDGE step % | JUDGE false alarm % (lower better) | JUDGE Youden J % | JUDGE V/L/E/M | RECON PC-v4 | RECON same Q % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Untrained 2B | 52.6 [48.9, 56.2] | 80.2 [76.2, 84.0] | 64.3 [61.7, 67.1] | 34.8 [30.9, 38.5] | 37.2 [33.2, 41.1] | 28.6 [23.4, 34.1] | 53.9 [51.6, 56.5] | 40.1 [38.4, 41.9] | 2.9 [1.9, 4.0] |
| Dr. GRPO on SOLVE, step 104 (dev-selected) | 50.4 [46.4, 54.3] | 72.5 [68.2, 76.8] | 65.0 [60.5, 69.5] | 31.5 [25.5, 37.5] | 18.5 [13.0, 24.0] | 30.0 [21.0, 39.0] | 58.0 [54.1, 62.0] | 33.4 [31.1, 35.8] | 1.8 [0.5, 3.2] |
| Dr. GRPO on JUDGE, step 26 (dev-selected) | 51.6 [48.0, 55.1] | 76.0 [72.0, 80.2] | 78.5 [74.2, 82.5] | 52.0 [45.0, 58.5] | 13.0 [8.5, 18.0] | 57.0 [48.5, 65.0] | 72.2 [68.5, 75.8] | 46.1 [43.4, 48.8] | 5.8 [3.5, 8.0] |
| Dr. GRPO on JUDGE, step 104 (fixed endpoint) | 48.4 [44.8, 52.1] | 71.5 [67.0, 75.8] | 72.2 [68.0, 76.5] | 41.5 [35.0, 48.0] | 10.5 [6.5, 15.0] | 44.5 [36.0, 53.0] | 67.3 [63.5, 71.1] | 36.6 [33.5, 39.5] | 3.5 [1.8, 5.5] |
| Dr. GRPO on RECONSTRUCT, step 104 (dev-selected) | 41.9 [38.4, 45.6] | 66.2 [61.8, 71.0] | 68.2 [63.7, 72.8] | 49.0 [42.5, 56.0] | 47.5 [40.5, 54.5] | 36.5 [27.5, 45.5] | 55.7 [52.0, 59.5] | 61.4 [59.3, 63.3] | 2.5 [1.0, 4.2] |
| Dr. GRPO on SOLVE, lr 1e-5 recipe, step 66 (selected by training reward, dev-checked) | 69.2 [65.6, 72.9] | 87.5 [84.0, 90.8] | 72.0 [67.5, 76.2] | 43.5 [36.5, 50.5] | 23.5 [17.5, 29.5] | 44.0 [35.0, 52.5] | 62.9 [59.1, 66.7] | 43.9 [41.2, 46.6] | 6.8 [4.5, 9.2] |
| Dr. GRPO on the 1/3-1/3-1/3 mixture, lr 2e-5, step 75 (best by training reward) | 69.8 [66.1, 73.4] | 84.5 [80.8, 87.8] | 87.0 [83.5, 90.0] | 67.0 [60.0, 73.5] | 7.5 [4.0, 11.0] | 74.0 [67.0, 80.0] | 80.8 [77.6, 83.7] | 58.4 [55.9, 60.8] | 10.5 [7.8, 13.5] |

## Δ against the untrained 2B (paired; **bold** = own task)

| Model | SOLVE acc % | SOLVE pass@4 % | JUDGE verdict % | JUDGE step % | JUDGE false alarm % (lower better) | JUDGE Youden J % | JUDGE V/L/E/M | RECON PC-v4 | RECON same Q % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Dr. GRPO on SOLVE, step 104 (dev-selected) | **-2.2 [-5.8, +1.1]** | -7.8 [-11.8, -3.5] | +0.7 [-4.1, +5.7] | -3.2 [-9.9, +3.6] | -18.8 [-25.1, -12.4] | +1.4 [-8.2, +11.4] | +4.1 [+0.2, +8.0] | -6.7 [-9.3, -4.1] | -1.1 [-2.6, +0.4] |
| Dr. GRPO on JUDGE, step 26 (dev-selected) | -1.1 [-4.1, +1.9] | -4.2 [-8.0, -0.2] | +14.2 [+9.8, +18.4] | **+17.2 [+10.2, +24.0]** | **-24.2 [-29.2, -19.4]** | **+28.4 [+19.5, +36.9]** | **+18.3 [+14.7, +21.8]** | +6.0 [+3.3, +8.6] | +2.9 [+0.8, +4.9] |
| Dr. GRPO on JUDGE, step 104 (fixed endpoint) | -4.2 [-7.4, -1.3] | -8.8 [-13.0, -4.8] | +7.9 [+3.3, +12.8] | **+6.8 [+0.0, +13.2]** | **-26.8 [-32.0, -21.2]** | **+15.9 [+6.6, +25.6]** | **+13.5 [+9.6, +17.4]** | -3.5 [-6.6, -0.6] | +0.6 [-1.1, +2.5] |
| Dr. GRPO on RECONSTRUCT, step 104 (dev-selected) | -10.7 [-13.7, -7.7] | -14.0 [-18.2, -9.8] | +3.9 [-0.6, +8.5] | +14.2 [+7.2, +21.8] | +10.2 [+3.9, +16.5] | +7.9 [-1.2, +17.0] | +1.8 [-2.0, +5.6] | **+21.4 [+19.1, +23.5]** | **-0.4 [-2.2, +1.4]** |
| Dr. GRPO on SOLVE, lr 1e-5 recipe, step 66 (selected by training reward, dev-checked) | **+16.6 [+13.8, +19.1]** | +7.2 [+3.8, +10.8] | +7.7 [+3.1, +11.9] | +8.8 [+2.1, +16.1] | -13.8 [-19.8, -8.1] | +15.4 [+6.2, +23.8] | +9.0 [+5.1, +12.6] | +3.8 [+1.4, +6.3] | +3.9 [+1.9, +5.9] |
| Dr. GRPO on the 1/3-1/3-1/3 mixture, lr 2e-5, step 75 (best by training reward) | +17.1 [+14.3, +19.9] | +4.2 [+1.0, +7.8] | +22.7 [+18.7, +26.3] | +32.2 [+25.9, +38.6] | -29.8 [-34.2, -25.5] | +45.4 [+37.4, +52.6] | +26.9 [+23.7, +29.9] | +18.3 [+16.1, +20.5] | +7.6 [+4.9, +10.3] |

## JUDGE by answer-key label (pass@1, 200 questions each)

Combined accuracy favours a model that answers "correct": on a correct solution "correct, none" earns full credit, while on an incorrect one the first wrong step must also be found. Read it with this split.

| Model | verdict, key correct % | verdict, key incorrect % | combined, key correct % | combined, key incorrect % |
|---|---:|---:|---:|---:|
| Untrained 2B | 62.7 | 65.9 | 57.6 | 34.8 |
| Dr. GRPO on SOLVE, step 104 (dev-selected) | 81.5 | 48.5 | 78.5 | 31.5 |
| Dr. GRPO on JUDGE, step 26 (dev-selected) | 87.0 | 70.0 | 87.0 | 52.0 |
| Dr. GRPO on JUDGE, step 104 (fixed endpoint) | 89.5 | 55.0 | 89.5 | 41.5 |
| Dr. GRPO on RECONSTRUCT, step 104 (dev-selected) | 52.5 | 84.0 | 52.0 | 49.0 |
| Dr. GRPO on SOLVE, lr 1e-5 recipe, step 66 (selected by training reward, dev-checked) | 76.5 | 67.5 | 71.5 | 43.5 |
| Dr. GRPO on the 1/3-1/3-1/3 mixture, lr 2e-5, step 75 (best by training reward) | 92.5 | 81.5 | 89.0 | 67.0 |
