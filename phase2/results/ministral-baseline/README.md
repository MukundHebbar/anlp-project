# Ministral Instruct BF16 SOLVE baseline

Completed 2026-10-27. 400 FINAL-v3 SOLVE test questions, four samples each; no training.

| Metric | Ministral | Qwen3.5-2B | Paired difference, points (95% CI) |
|---|---:|---:|---:|
| Mean accuracy | 27.6% | 52.6% | -25.1 [-28.8, -21.4] |
| pass@4 | 53.8% | 80.2% | -26.5 [-31.8, -21.2] |

Paired bootstrap over 400 questions, 10,000 resamples, seed 0. Both use the unchanged SOLVE prompt, BF16, temperature 1, top-p 1, top-k disabled, evaluation seed 0, and 16k generation with continuation to 32k. Scores use the existing checker and strict gates. Ministral uses its native Instruct checkpoint/chat serialization; Qwen uses its non-thinking template.

The same per-model token cap does not imply the same amount of text or compute because tokenizers and architectures differ. This is a comparison under the shared evaluation recipe.

See [the frozen protocol](../../ministral_baseline/README.md). Full generated responses are backed up under `local/ministral-baseline/test/responses-solve.jsonl.gz`.
