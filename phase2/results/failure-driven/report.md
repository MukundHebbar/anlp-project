# Failure-driven cross-task GRPO pilot

Qwen3.5-2B, Dr. GRPO (Aryama's recipe: 32 prompts x 8 samples, lr 1e-5, 16k rollouts). SOLVE pool: 768
JUDGE-train questions (their JUDGE items reused as-is). Shared round 1 = steps 1-8 SOLVE-only; then three arms
for steps 9-24, with 32 prompts per step:

- **A**: 32 SOLVE.
- **B**: 24 SOLVE + 8 auxiliary: each buffered failure's JUDGE item and a RECONSTRUCT item (FINAL-v3 pipeline,
  clues targeted at the diagnosed mistake). Reward judge for these: Qwen3.8-27B.
- **D**: 24 SOLVE + 8 replayed failures as plain SOLVE (same buffer, schedule and refresh as B).

Buffer: <= 1/8 strictly correct and >= 5 verified-wrong, finished, ungated answers. Refreshed after step 16:
recheck (8 samples) with the arm's own step-16 adapter, plus the arm's new failures.

## SOLVE dev (200 questions x 4 samples)

| Model | Mean pass@1 | pass@4 |
|---|---|---|
| Untrained 2B | 52.4 | 78.5 |
| Shared step 8 | 54.2 | 79.5 |
| A step 16 | 55.0 | 81.5 |
| B step 16 | 59.5 | 83.5 |
| D step 16 | 60.1 | 83.0 |
| A step 24 | 59.9 | 85.0 |
| B step 24 | 62.1 | 85.0 |
| D step 24 | 61.1 | 84.5 |

Paired differences in mean pass@1, 95% bootstrap CI over questions:

| | Step 16 | Step 24 |
|---|---|---|
| B - A | +4.5 [+0.6, +8.1] | +2.2 [-1.2, +6.0] |
| D - A | +5.1 [+1.4, +8.9] | +1.2 [-3.0, +5.5] |
| D - B | +0.6 [-3.1, +4.2] | -1.0 [-4.9, +2.8] |

Matched GPU-hours (B step 16 vs A step 24, about 7.6 GPU-h each): -0.4 [-4.4, +3.5].

## Recovery of the 28 round-1 failures (secondary)

| Arm | Step 16 | Step 24 |
|---|---|---|
| A | 9/28 | 9/28 |
| B | 12/28 | 15/28 |
| D | 11/28 | 15/28 |

## Compute

```
GPU-hours (Slurm-charged)
  shared round 1 (steps 1-8)       2.583
  arm A (steps 9-24)               4.967
  arm B round 2 (steps 9-16)       5.117
  arm B round 3 (steps 17-24)      5.233
  arm D (steps 9-24)               5.334
  failed setup attempts (not charged to an arm): [('fd-r1-solve', 0.033), ('fd-armB-r2', 0.083), ('fd-armB-r2b', 0.017), ('fd-armB-r2c', 0.083), ('fd-armB-r2d', 1.317)]
  cumulative: arm A step 24 = 7.55; arm B step 16 = 7.70; arm B step 24 = 12.93; arm D step 24 = 7.92
Student rollout tokens (generated)
  shared round 1   solve: 16.47M tokens in 2048 rollouts
  arm A            solve: 35.12M tokens in 4096 rollouts
  arm B            aux: 6.98M tokens in 1024 rollouts, solve: 25.67M tokens in 3072 rollouts
  arm D            solve: 36.25M tokens in 4096 rollouts
Conversion (DeepSeek V4.1 Flash, arm B)
  230 calls, 1.64M prompt + 0.86M completion tokens
```

## Reading

Practising current failures (B or D) speeds up SOLVE gains early (step 16), but by step 24 no arm differs from
another beyond noise. Converting failures to JUDGE/RECONSTRUCT (B) gives no measurable benefit over replaying them as
SOLVE (D), and costs about 1.6x the GPU time (the 27B judge) plus DeepSeek conversion. One seed; 200 dev questions.

Records: `dev-scores.jsonl.gz` (5600), `recheck-scores.jsonl.gz` (1344), `buffers.jsonl.gz` (69),
`conversion.jsonl.gz` (52), `train-metrics.jsonl.gz` (56). Code: `../../failure_driven/`.
