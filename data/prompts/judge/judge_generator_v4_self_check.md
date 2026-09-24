# JUDGE generator candidate D: mutate and self-check

Generate one high-quality JUDGE task from a verified mathematics problem and
solution. The student-facing task is to judge a proposed solution, not to solve
the source problem from scratch.

<problem>
{problem}
</problem>
<verified_reference_solution>
{reference_solution}
</verified_reference_solution>
<target_label>{target_label}</target_label>
<requested_error_type>{error_type}</requested_error_type>
<requested_error_position>{error_position}</requested_error_position>

Privately create a concise canonical solution with stable IDs S1, S2, ... .
Then create the requested proposal. Before emitting JSON, perform this
checklist:

- Does the correct proposal have no invalid step and the correct final result?
- For an incorrect proposal, are every step before the annotated step valid?
- Is the annotated step the first actual error, rather than merely the first
  suspicious-looking line?
- Is there exactly one local error of the requested type?
- Can a student prove the error from the problem and visible proposal alone?
- Does the proposal preserve the reference method and avoid label shortcuts in
  formatting, length, or wording?
- Do all step IDs appear once and in order?

For `incorrect`, the error type must be one of
`arithmetic_algebra`, `sign_inequality`, `invalid_theorem_condition`,
`unjustified_implication`, `missing_case`, `domain_restriction`,
`counting_bijection`, or `other`; the position must be `early`, `middle`, or
`late`. For `correct`, set all error fields to null.

Return only this JSON shape:

```json
{
  "public": {
    "problem": "...",
    "proposed_solution": [{"step_id": "S1", "text": "..."}],
    "instruction": "Decide whether the proposed solution is correct. If it is incorrect, identify the first wrong step and explain the mathematical error."
  },
  "private": {
    "label": "correct|incorrect",
    "first_error_step_id": "S1|null",
    "first_error_explanation": "...|null",
    "error_type": "...|null",
    "error_position": "...|null",
    "teacher_target_response": "Decision: ...\nFirst wrong step: ...\nExplanation: ..."
  }
}
```

Do not expose the reference solution, canonical draft, checklist, or any
private metadata in the public object.
