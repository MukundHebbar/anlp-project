# Frozen production outputs under the inference criterion

Same saved outputs under different rubric versions; this measures an evaluator change, not improved student performance.

| Model | Saved outputs | p3 scored | p2 mean /100 | p3 resolved mean /100 | Planned-draw bounds |
|---|---:|---:|---:|---:|---|
| Qwen/Qwen3-4B | 17 | 17 | 30.88 | 16.18 | [15.277777777777779, 20.833333333333332] |
| deepseek-ai/DeepSeek-V4.1-Flash | 8 | 7 | 87.50 | 78.57 | [61.111111111111114, 83.33333333333333] |

Resolved response means; two Qwen draws per source except one missing. Planned bounds include failed student draws and unresolved judgments. Not a confirmation estimate.

| Source | Model | Seed | p2 | p3 | Inference |
|---|---|---:|---:|---:|---|
| 8 | Qwen/Qwen3-4B | 0 | 1 | 1 | substantive |
| 27 | Qwen/Qwen3-4B | 0 | 1 | 1 | substantive |
| 33 | Qwen/Qwen3-4B | 0 | 3 | 0 | copy_only |
| 77 | Qwen/Qwen3-4B | 0 | 1 | 1 | substantive |
| 86 | Qwen/Qwen3-4B | 0 | 1 | 0 | copy_only |
| 112 | Qwen/Qwen3-4B | 0 | 1 | 0 | copy_only |
| 136 | Qwen/Qwen3-4B | 0 | 1 | 1 | substantive |
| 143 | Qwen/Qwen3-4B | 0 | 1 | 1 | uncertain |
| 8 | Qwen/Qwen3-4B | 1 | 1 | 1 | substantive |
| 27 | Qwen/Qwen3-4B | 1 | 1 | 1 | substantive |
| 33 | Qwen/Qwen3-4B | 1 | 3 | 0 | copy_only |
| 77 | Qwen/Qwen3-4B | 1 | 1 | 1 | substantive |
| 86 | Qwen/Qwen3-4B | 1 | 1 | 1 | substantive |
| 112 | Qwen/Qwen3-4B | 1 | 1 | 1 | substantive |
| 136 | Qwen/Qwen3-4B | 1 | 1 | 0 | copy_only |
| 141 | Qwen/Qwen3-4B | 1 | 1 | 1 | substantive |
| 143 | Qwen/Qwen3-4B | 1 | 1 | 0 | copy_only |
| 33 | deepseek-ai/DeepSeek-V4.1-Flash | None | 4 | 0 | copy_only |
| 27 | deepseek-ai/DeepSeek-V4.1-Flash | None | 4 | 4 | substantive |
| 86 | deepseek-ai/DeepSeek-V4.1-Flash | None | 3 | 3 | substantive |
| 8 | deepseek-ai/DeepSeek-V4.1-Flash | None | 4 | 3 | substantive |
| 112 | deepseek-ai/DeepSeek-V4.1-Flash | None | 4 | 4 | substantive |
| 77 | deepseek-ai/DeepSeek-V4.1-Flash | None | 4 | 4 | substantive |
| 141 | deepseek-ai/DeepSeek-V4.1-Flash | None | 4 | 4 | substantive |
| 136 | deepseek-ai/DeepSeek-V4.1-Flash | None | 1 | None | None |

Independent review found one demonstrated 0-versus-1 scoring error. Correcting that single reference case changes Qwen's resolved mean to 17.65/100; raw labels remain unchanged. See production-score-error-136.json.
The revised evaluator remains provisional. Passing authored controls did not establish production accuracy; the unresolved stronger-model set-family judgment also remains in missingness accounting.
