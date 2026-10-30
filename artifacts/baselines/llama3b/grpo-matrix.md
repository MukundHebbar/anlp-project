# Dr. GRPO transfer matrix (Llama-3.2-3B-Instruct, FINAL-v3 test)

Student meta-llama/Llama-3.2-3B-Instruct, seed 0, the Qwen study's per-task Dr. GRPO recipes. Training rewards for JUDGE / RECONSTRUCT come from Gemma 4 12B (explicit-label calibration) instead of Jev; JUDGE V/L/E/M and RECONSTRUCT PC-v4 use the Qwen3.8-27B judge as in the Qwen study. SOLVE lr 2e-5 (chosen by the 8-step probes on dev; the Qwen study used 1e-5).

## Scores (pass@1 unless noted)

| Model | SOLVE acc % | SOLVE pass@4 % | JUDGE verdict % | JUDGE step % | JUDGE false alarm % (lower better) | JUDGE Youden J % | JUDGE V/L/E/M | RECON PC-v4 | RECON same Q % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Untrained Llama-3.2-3B | 9.0 [7.3, 10.7] | 25.5 [21.2, 29.8] | 36.0 [31.2, 40.5] | 13.5 [9.0, 18.0] | 96.0 [93.0, 98.5] | -28.0 [-37.5, -19.0] | 16.2 [14.3, 18.0] | 16.9 [15.0, 18.8] | 0.2 [0.0, 0.8] |
| Dr. GRPO on SOLVE, step 106 (dev-selected) | 29.1 [25.4, 32.9] | 45.2 [40.0, 50.0] | 42.8 [38.0, 47.5] | 14.5 [10.0, 19.5] | 94.0 [90.5, 97.0] | -14.5 [-24.0, -5.0] | 19.9 [17.9, 22.1] | 28.7 [26.7, 30.7] | 0.8 [0.0, 1.8] |
| Dr. GRPO on JUDGE, step 78 (dev-selected) | 8.4 [6.7, 10.1] | 23.0 [18.8, 27.0] | 57.5 [52.8, 62.3] | 8.0 [4.5, 12.0] | 16.0 [11.0, 21.0] | 15.0 [5.5, 24.5] | 46.5 [42.8, 50.2] | 27.7 [25.8, 29.7] | 0.8 [0.0, 1.8] |
| Dr. GRPO on JUDGE, step 104 (fixed endpoint) | 9.2 [7.4, 11.1] | 24.5 [20.5, 28.7] | 51.2 [46.5, 56.0] | 3.0 [1.0, 5.5] | 3.5 [1.0, 6.0] | 2.5 [-7.0, 12.0] | 47.0 [43.3, 50.9] | 34.6 [32.7, 36.6] | 0.5 [0.0, 1.2] |
| Dr. GRPO on RECONSTRUCT, step 104 (dev-selected) | 14.9 [12.2, 17.6] | 31.2 [26.8, 35.8] | 46.5 [41.8, 51.5] | 13.0 [8.5, 18.0] | 88.5 [84.0, 92.5] | -7.0 [-16.5, 3.0] | 23.0 [20.8, 25.3] | 57.2 [55.3, 58.9] | 2.2 [1.0, 3.8] |

## Δ against the untrained Llama (paired; **bold** = own task)

| Model | SOLVE acc % | SOLVE pass@4 % | JUDGE verdict % | JUDGE step % | JUDGE false alarm % (lower better) | JUDGE Youden J % | JUDGE V/L/E/M | RECON PC-v4 | RECON same Q % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Dr. GRPO on SOLVE, step 106 (dev-selected) | **+20.1 [+16.6, +23.8]** | +19.8 [+14.8, +24.8] | +6.8 [+2.0, +11.2] | +1.0 [-4.5, +6.5] | -2.0 [-6.0, +2.0] | +13.5 [+4.0, +22.5] | +3.7 [+1.5, +5.9] | +11.8 [+9.3, +14.4] | +0.5 [-0.5, +1.5] |
| Dr. GRPO on JUDGE, step 78 (dev-selected) | -0.6 [-2.4, +1.3] | -2.5 [-7.0, +2.2] | +21.5 [+13.8, +29.0] | **-5.5 [-11.0, +0.0]** | **-80.0 [-85.5, -74.0]** | **+43.0 [+27.5, +58.0]** | **+30.3 [+25.6, +35.0]** | +10.8 [+8.3, +13.5] | +0.5 [-0.2, +1.5] |
| Dr. GRPO on JUDGE, step 104 (fixed endpoint) | +0.2 [-1.6, +2.1] | -1.0 [-5.8, +3.8] | +15.2 [+7.0, +24.0] | **-10.5 [-16.5, -5.0]** | **-92.5 [-96.0, -88.5]** | **+30.5 [+14.0, +48.0]** | **+30.8 [+25.8, +36.0]** | +17.7 [+15.2, +20.2] | +0.2 [-0.5, +1.2] |
| Dr. GRPO on RECONSTRUCT, step 104 (dev-selected) | +5.9 [+3.6, +8.2] | +5.8 [+1.0, +10.8] | +10.5 [+5.5, +15.2] | -0.5 [-6.5, +5.5] | -7.5 [-12.5, -2.0] | +21.0 [+11.0, +30.5] | +6.8 [+4.2, +9.4] | **+40.3 [+37.7, +42.7]** | **+2.0 [+0.5, +3.5]** |

## JUDGE by answer-key label (pass@1)

| Model | verdict, key correct % | verdict, key incorrect % | combined, key correct % | combined, key incorrect % |
|---|---:|---:|---:|---:|
| Untrained Llama-3.2-3B | 4.0 | 68.0 | 4.0 | 13.5 |
| Dr. GRPO on SOLVE, step 106 (dev-selected) | 6.0 | 79.5 | 5.0 | 14.5 |
| Dr. GRPO on JUDGE, step 78 (dev-selected) | 84.0 | 31.0 | 84.0 | 8.0 |
| Dr. GRPO on JUDGE, step 104 (fixed endpoint) | 96.5 | 6.0 | 96.5 | 3.0 |
| Dr. GRPO on RECONSTRUCT, step 104 (dev-selected) | 11.5 | 81.5 | 11.0 | 13.0 |
