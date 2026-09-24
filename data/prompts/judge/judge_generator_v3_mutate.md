# JUDGE generator candidate C: draft then mutate one step

You are a careful mathematics dataset generator. Produce one JUDGE example.
The student sees a problem and a step-numbered proposed solution, then decides
whether it is correct. If incorrect, the student identifies and explains the
first wrong step.

<problem>
{problem}
</problem>
<verified_reference_solution>
{reference_solution}
</verified_reference_solution>
<target_label>{target_label}</target_label>
<requested_error_type>{error_type}</requested_error_type>
<requested_error_position>{error_position}</requested_error_position>

Work privately in this order:

1. Draft a concise, valid step-by-step solution using the same method as the
   verified reference.
2. If the target is `correct`, use that draft unchanged after checking every
   step and the final answer.
3. If the target is `incorrect`, select the requested position and replace the
   corresponding step with one local error of the requested type. Re-check all
   earlier steps, ensure the error is the first error, and ensure the proposed
   solution remains understandable. Do not silently change the problem or
   introduce an earlier mistake.
4. Write a private explanation that identifies the exact invalid statement and
   the mathematical fact that refutes it. A final answer matching the source
   does not make an invalid derivation correct.

Use stable IDs `S1`, `S2`, ... . Use `none` for all error metadata on a
correct item. For incorrect items, use one of these error types:
`arithmetic_algebra`, `sign_inequality`, `invalid_theorem_condition`,
`unjustified_implication`, `missing_case`, `domain_restriction`,
`counting_bijection`, `other`; and one position: `early`, `middle`, `late`.

Return JSON only:

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

Never include private reasoning, the verified reference, or hidden annotations
inside `public`.
