> **Status on 2026-10-30:** The subsequent Gemma full calibration completed and was used for the finished
> Llama GRPO runs. See [full calibration](../results/local-judge-calibration/gemma-full-explicit/README.md)
> and [completed Llama runs](../llama_transfer/README.md). Earlier Selene/screen sections below are historical.

# Local replacement judge: historical calibration

Completed on 2026-10-27, following the user's request to check **Selene Mini 8B only** and reuse the previous
calibration recipe. No new Jev or DeepSeek requests were made. Qwen3.8-27B remains the final evaluator.

Model: `AtlaAI/Selene-1-Mini-Llama-3.1-8B`, revision `427792f1c3e2073cb7da216924fd884b1ba496e0`, BF16.
Turing job **52341**, node08, account `priyesh.shukla`: completed successfully in **4m41s**, charged **0.083 GPU-h**.
All 1,947 requests / 4,252 rubric questions completed, with no missing-label failures in the Selene run.

## Gemma follow-up

The subsequently authorized Gemma 4 12B screen completed as job 52389 on node08. It used 192 response groups
(96 per task), with 48 planned held-out responses per task. The original top-20 label extraction failed on
13 requests, reducing valid held-out RECONSTRUCT responses to 40. Its initial r=0.909 JUDGE / r=0.847 RECONSTRUCT
result is provisional; 380/929 individual questions had label mass below 0.5. The original screen comparison
was corrected to disclose that Qwen retained 48 RECONSTRUCT responses and Gemma only 40.

On user authorization, full historical calibration job **52402** was submitted on node08, one GPU with a
30-minute wall limit. Output: `gemma-full-explicit`. It retains the saved prompts, rubrics, non-thinking native
chat, one-token scoring, reference labels and checkpoint split. It changes extraction from top-20-only to
explicit unmasked probabilities for every single-token spelling accepted by the historical label reader.
This avoids silently omitting low-probability valid labels; it does not force the model to emit a valid label.
The engine feature is documented in [vLLM SamplingParams](https://docs.vllm.ai/en/latest/api/vllm/sampling_params/).

The full input contains 1,947 requests / 4,252 rubric questions. Reference filtering previously yielded 176
held-out JUDGE and 241 held-out RECONSTRUCT responses; actual coverage and failures must be reported.
`run_gemma_full.py` stages and submits, waits on a Slurm dependency, retrieves outputs, fits thresholds,
audits production scoring parity, and evaluates saved Qwen predictions on matching complete response groups.
No new reference calls or training are launched. The small screen and original Qwen calibration are preserved.
Label reliability and shortcut errors must be reviewed alongside correlations before adopting a reward judge.

## Result

- JUDGE held-out total-score Pearson correlation: **0.913**, n=176; MAE 9.45/100.
- RECONSTRUCT held-out total-score correlation: **undefined**, n=241, because the existing shortcut rule
  assigned every answer zero. It caught 9 reference shortcuts but falsely flagged all 232 other answers.
- Dimension-level agreement also trails the original Qwen judge. Selene is **not accepted as a drop-in reward
  judge for both tasks**. No training run was launched using it.

See the [full results](../results/local-judge-calibration/selene/README.md), including six dimension-level kappas,
raw label probabilities, fitted thresholds and pinned model metadata. This measures compatibility with the original
one-token prompt and probability-based shortcut rule; it does not establish the model's best possible performance
using its separately recommended critique-generation templates. Further prompt/shortcut changes require another
explicitly documented experiment; none was launched after the user requested a light check.

## Offline audit of RECONSTRUCT

The initial total-score result conflated shortcut-gate failure with rubric-scoring quality. A subsequent
offline audit checks these separately, without further model calls. The manually aggregated scores match
the production `jev_judging.score_record` function exactly on all 241 held-out answers, for both models.

On the **232 reference non-shortcut answers**, bypassing the predicted shortcut gate for this diagnostic,
the continuous P/T/E/M rubric total correlates **0.656 for Selene**, versus **0.840 for Qwen27B** on the same
answers. The gate failure is real, and Selene's underlying rubric agreement is also weaker. These results
apply to the original one-token scoring protocol, not all possible Selene prompting strategies. Full
breakdowns are saved as `reconstruct-audit.json` in each model's result directory.

## Recipe and provenance

The saved requests and DeepSeek labels come from `artifacts/qwen-judge-calibration/` and the eight historical
`matrix-*` evaluation directories. The split, rubric definitions, 0.1-spaced cutoff grid, quadratic-weighted kappa
objective and final all-item threshold fit match `scripts/qwen_judge_calibration.py`.

The original calibration code is unchanged relative to `origin/grpo-transfer-2026-10` and
`origin/phase2-experiments`; its last source-changing commit is
`a49610c19964be02a7a3fa1004bf22728500836e`. Work remains on `phase2-failure-driven` without changing branches or
overwriting the user's uncommitted experiments. The optimized threshold search reproduces **all six existing
Qwen27B final cutoff sets exactly**; its objective is also checked against brute-force search in regression tests.

The [reproduced Qwen reference](../results/local-judge-calibration/qwen27b-reference/README.md) uses the same
new total-score aggregation for a directly comparable diagnostic. Its RECONSTRUCT total correlation differs from
the old report's headline because this diagnostic explicitly applies held-out cutoffs and the shortcut stage.
Original Qwen calibration files and results were not overwritten.

Historical calibration questions are test-derived. The user explicitly requested reuse of that recipe. Results
are held out by checkpoint, not by question, and must not be described as an untouched-question judge evaluation.
The OPD-era response examples remain references even though OPD **adapter weights** are excluded from the archive.
