# JUDGE generator candidate A: explicit rubric

You are generating one mathematical JUDGE task from a verified source problem
and a trusted reference solution. The student will see only the problem and a
proposed step-numbered solution. The student must decide whether that proposal
is correct. If it is incorrect, the student must identify the *first* wrong
step and explain the error.

<problem>
{problem}
</problem>

<verified_reference_solution>
{reference_solution}
</verified_reference_solution>

<target_label>
{target_label}
</target_label>

<requested_error_type>
{error_type}
</requested_error_type>

<requested_error_position>
{error_position}
</requested_error_position>

## Generation rules

1. Convert the reference solution into a concise, logically ordered solution
   with stable IDs S1, S2, ... . Preserve the original mathematical method.
2. For a `correct` target, write a self-contained valid proposal. Do not add a
   private error marker.
3. For an `incorrect` target, keep every step before the requested first-error
   position mathematically valid, then introduce exactly one clear error of the
   requested type. Continue naturally only if doing so does not create a second
   earlier error. The first wrong step must be identifiable from the visible
   proposal and the original problem.
4. Do not make the label inferable from formatting, length, wording, or a final
   answer that is obviously nonsensical. An incorrect proposal may retain the
   correct final answer if the first invalid inference is still clear.
5. Use `none` for `error_type` and `error_position` on correct targets. Use one
   of `arithmetic_algebra`, `sign_inequality`, `invalid_theorem_condition`,
   `unjustified_implication`, `missing_case`, `domain_restriction`,
   `counting_bijection`, or `other` for incorrect targets. Use `early`,
   `middle`, or `late` for incorrect positions.
6. The private explanation must explain why the annotated step is the first
   failure. It must not rely on hidden information unavailable to a student.

## Output

Return valid JSON only, with exactly these top-level fields:

```json
{
  "public": {
    "problem": "...",
    "proposed_solution": [
      {"step_id": "S1", "text": "..."}
    ],
    "instruction": "Decide whether the proposed solution is correct. If it is incorrect, identify the first wrong step and explain the mathematical error."
  },
  "private": {
    "label": "correct or incorrect",
    "first_error_step_id": "S2 or null",
    "first_error_explanation": "... or null",
    "error_type": "... or null",
    "error_position": "... or null",
    "teacher_target_response": "..."
  }
}
```

The `teacher_target_response` must use this fixed format:

```text
Decision: correct|incorrect
First wrong step: <step ID or none>
Explanation: <concise mathematical justification>
```

Do not include the reference solution, prompt metadata, chain-of-thought, or
any private field inside `public`. Do not solve a different problem.
