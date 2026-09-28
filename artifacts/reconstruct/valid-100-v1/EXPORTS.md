# Extension export guide

The requested target is100 rows with accepted automatic input gates, a parsed Qwen response, and two complete validated judgments. It is not100 correct reconstructions. Files are provisional until both `terminal` and `target_met` are true in `summary.json`.

- `questions-answers.csv`: selected questions, source reference answers, four public clues, Qwen reconstructed questions and justifications, component scores, numerical totals and current v4 ratings. Rows carry a `calibration` or `extension` label.
- `questions-answers.jsonl`: full selected records. **Use the top-level `rating_v4` for the current1–5 display.** The nested `score.rating_1_to_5` is retained from the historical v1 aggregator; it is not the current display policy. Numerical `score.score_100` and dimension scores are unchanged.
- `questions-answers.md`: readable final export, generated after completion.
- `public-tasks.jsonl`: only the final answer and four observations, plus a dataset ID. The ID is not part of the student prompt. Do not supply the private source question/reference solution to Qwen.
- `extension-attempts.jsonl`: every processed new source, including rejected/uncertain inputs and failed or incomplete model outputs. This provides the attempt/coverage denominator.
- `overflow-complete.jsonl`: any completely scored rows beyond the first53 additions in the last finished batch. They are preserved separately, not selected by score.
- `calibration-47.jsonl`: immutable copy of the47 previously scored calibration rows before adding cohort/current-display fields.
- `manifest.json`: ordered candidate queue, exact prompts, model settings, source references, acquisition hashes and fixed selection/stopping policy.
- `run.json`: all raw extension calls, validation errors, input bindings and execution checkpoints. Failed judgment proposals do not count as accepted scores.
- `manual-review.json`: targeted assistant mathematical review, separate from raw automated decisions. It is not independent human annotation.
- `verification.json`: completion, source order, prompt binding, score and export checks, generated after completion.

The reference questions and original numerical answers are research answer-key material. Source and judge checks remain fallible. Do not interpret a gate-passed label as an independent certificate of correctness or non-leakage. Grade5 denotes high partial credit, not necessarily original-question recovery.
