# JUDGE external grader prompt

You are an independent evaluator of one mathematics JUDGE response. Evaluate
the student's decision, first-error localization, and mathematical explanation
against the public task and private gold annotation. Accept mathematically
equivalent wording and alternative valid explanations. Do not reward matching
phrases, and do not require the student to use the same theorem name as the
gold explanation.

<problem>
{problem}
</problem>

<proposed_solution>
{proposed_solution}
</proposed_solution>

<student_response>
{student_response}
</student_response>

<gold_label>
{gold_label}
</gold_label>

<gold_first_error_step>
{gold_first_error_step}
</gold_first_error_step>

<gold_first_error_explanation>
{gold_first_error_explanation}
</gold_first_error_explanation>

## Rubric

1. `decision_correct` is true only when the student correctly says whether the
   proposed solution is mathematically valid.
2. `first_error_correct` is true only when an incorrect proposal is localized
   to the first invalid step. For a correct proposal, it is true only when the
   student says there is no wrong step.
3. `explanation_correct` is true only when the student's explanation identifies
   the relevant mathematical reason and is sufficient to justify the decision
   or first-error claim. Accept an equivalent valid argument. A correct label
   without a mathematical explanation is not sufficient.

Treat malformed or missing responses as false for every criterion. Do not
continue solving the source problem or penalize concise wording. Return JSON
only:

```json
{
  "decision_correct": true,
  "first_error_correct": true,
  "explanation_correct": false,
  "strict_full_task_correct": false,
  "reason": "Brief mathematical justification for the three decisions."
}
```

`strict_full_task_correct` is true exactly when all three criteria are true.
