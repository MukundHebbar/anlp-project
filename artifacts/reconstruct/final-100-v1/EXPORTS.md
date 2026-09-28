# Export guide

- `questions-answers.csv`: the full100-source cohort with original question/reference answer, validity status, public clues, Qwen question/verification and scores when available.
- `questions-answers.jsonl`: the full research export, including component grades, missingness, raw Qwen output and manual-review annotations in the final export.
- `questions-answers.md`: the same material for reading in the IDE.
- `public-tasks.jsonl`: accepted student inputs only. The student sees the answer and four observations; the ID is dataset metadata, not part of its prompt.
- `reconstruct-qa.jsonl`: accepted inputs paired with their canonical original questions, Qwen outputs and ratings. Here the task's question is the answer-plus-clues bundle; its reference answer is the original mathematical question. This reference is not claimed uniquely identifiable.
- `source-question-answer-key.jsonl`: original source questions and dataset reference answers for all100 allocations. It includes rejected/invalid sources and is NOT an audited training set. Use the status-bearing exports above when selecting usable tasks.
- `manifest.json`: frozen sources, prompt text and configuration.
- `run.json`: raw model responses, failures, source/input bindings and progress.
- `manual-review.json`: human-readable assistant review kept separate from automatic gates and scores; not independent human annotation.

The run is complete. The full export contains100 source rows; the automatic gate-passed subset contains52 tasks, with50 parsed Qwen responses and47 resolved scores. Completion and counts are recorded in `summary.json` and `report.md`. Do not treat rejected inputs or missing judgments as student zero scores. Gate-passed is an automatic status, not a claim of independent certification; known gate disputes remain in the manual-review annotations.
