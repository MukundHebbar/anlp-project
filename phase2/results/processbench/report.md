# JUDGE on synthetic vs natural errors

F1 = harmonic mean of exact-first-error accuracy on wrong solutions and accuracy on correct ones.

| Model | Synthetic F1 | GSM8K F1 | MATH F1 | OlympiadBench F1 | Omni-MATH F1 | ProcessBench avg F1 |
|---|---|---|---|---|---|---|
| base | 44.7 | 48.0 | 45.7 | 38.6 | 32.3 | **41.1** |
| solve | 52.0 | 51.8 | 51.4 | 42.8 | 36.2 | **45.5** |
| judge | 68.9 | 64.2 | 58.7 | 53.5 | 41.9 | **54.6** |
| reconstruct | 50.4 | 64.3 | 57.7 | 51.4 | 47.4 | **55.2** |
| mixed | 79.5 | 67.8 | 69.9 | 55.1 | 46.4 | **59.8** |
| qwen3.5-9b | 84.1 | 82.7 | 80.5 | 70.9 | 64.1 | **74.5** |

| Model | Subset | Exact first error (wrong solutions) | Says correct (correct solutions) | Says incorrect (wrong solutions) | No verdict | Capped |
|---|---|---|---|---|---|---|
| base | synthetic | 33.5 | 67.0 | 51.0 | 26.5 | 3.5 |
| base | gsm8k | 33.8 | 82.4 | 50.2 | 19.2 | 1.5 |
| base | math | 31.6 | 82.3 | 55.2 | 22.8 | 2.8 |
| base | olympiadbench | 26.0 | 74.6 | 54.8 | 27.6 | 4.3 |
| base | omnimath | 20.8 | 71.8 | 51.3 | 31.5 | 6.2 |
| solve | synthetic | 41.0 | 71.0 | 53.5 | 20.0 | 3.2 |
| solve | gsm8k | 36.2 | 90.7 | 51.7 | 14.8 | 1.2 |
| solve | math | 36.2 | 88.9 | 58.6 | 19.6 | 2.3 |
| solve | olympiadbench | 28.9 | 82.3 | 55.4 | 24.0 | 4.2 |
| solve | omnimath | 23.3 | 81.3 | 49.4 | 30.1 | 5.7 |
| judge | synthetic | 57.0 | 87.0 | 69.0 | 3.8 | 0.5 |
| judge | gsm8k | 47.3 | 99.5 | 68.1 | 0.5 | 0.0 |
| judge | math | 42.3 | 96.3 | 72.4 | 3.5 | 0.3 |
| judge | olympiadbench | 37.1 | 95.9 | 69.3 | 3.7 | 0.5 |
| judge | omnimath | 26.7 | 96.7 | 62.8 | 5.2 | 0.7 |
| reconstruct | synthetic | 48.5 | 52.5 | 76.0 | 12.5 | 0.0 |
| reconstruct | gsm8k | 51.7 | 85.0 | 73.9 | 9.8 | 0.0 |
| reconstruct | math | 46.1 | 77.1 | 79.3 | 11.7 | 0.2 |
| reconstruct | olympiadbench | 39.3 | 74.3 | 77.3 | 13.7 | 0.1 |
| reconstruct | omnimath | 37.9 | 63.1 | 75.4 | 15.4 | 0.0 |
| mixed | synthetic | 70.0 | 92.0 | 83.0 | 4.8 | 2.5 |
| mixed | gsm8k | 52.2 | 96.9 | 66.7 | 4.8 | 0.0 |
| mixed | math | 55.4 | 94.6 | 80.0 | 7.2 | 1.6 |
| mixed | olympiadbench | 38.9 | 94.7 | 67.9 | 11.5 | 4.1 |
| mixed | omnimath | 30.8 | 93.4 | 60.1 | 15.0 | 6.9 |
| qwen3.5-9b | synthetic | 88.0 | 80.5 | 91.5 | 7.8 | 2.2 |
| qwen3.5-9b | gsm8k | 73.9 | 93.8 | 86.5 | 3.2 | 0.2 |
| qwen3.5-9b | math | 73.6 | 88.9 | 92.9 | 4.0 | 1.1 |
| qwen3.5-9b | olympiadbench | 64.4 | 78.8 | 92.1 | 6.3 | 1.2 |
| qwen3.5-9b | omnimath | 57.0 | 73.0 | 89.9 | 8.5 | 1.1 |
