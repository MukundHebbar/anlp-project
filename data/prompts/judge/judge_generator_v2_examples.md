# JUDGE generator candidate B: rubric with contrastive examples

Generate one public/private JUDGE item from the supplied problem and verified
solution. The public item contains a numbered proposed solution. A student must
decide whether it is correct; for an incorrect proposal the student must name
the first invalid step and explain why.

<problem>
{problem}
</problem>
<verified_reference_solution>
{reference_solution}
</verified_reference_solution>
<target_label>{target_label}</target_label>
<requested_error_type>{error_type}</requested_error_type>
<requested_error_position>{error_position}</requested_error_position>

## Two miniature examples of the required distinction

Example A (correct): if S1 establishes `x > 0` and S2 concludes `x^2 > 0`,
the proposal is correct because squaring a positive real preserves strict
positivity.

Example B (incorrect): if S1 only establishes `x != 0` and S2 concludes
`x^2 > 0` over the reals, the conclusion happens to be true, but the proposal
must still be marked incorrect if S1's stated justification claimed that
positivity followed from `x != 0`; the first wrong step is that implication.

These examples illustrate that a correct final value does not repair an invalid
intermediate inference. They are not templates for the source problem.

## Rules

- Preserve the reference solution's main method and problem answer.
- Build stable steps S1, S2, ... and make the first-error location explicit in
  the private fields.
- For `correct`, every visible step must be valid.
- For `incorrect`, all visible steps before the requested position must be
  valid, and the requested step must contain exactly one defensible error.
- Do not create label shortcuts through wording, formatting, or solution length.
- Use error types `arithmetic_algebra`, `sign_inequality`,
  `invalid_theorem_condition`, `unjustified_implication`, `missing_case`,
  `domain_restriction`, `counting_bijection`, or `other`; use position
  `early`, `middle`, or `late`.

Return JSON only with this shape:

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

Do not expose the reference solution or private metadata in `public`.
