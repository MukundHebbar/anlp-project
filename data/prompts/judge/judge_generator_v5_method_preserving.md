# JUDGE generator candidate E: method-preserving local mutation

Generate one mathematics JUDGE example from the problem and verified solution.
The student will see the problem and a numbered proposed solution, and will
decide whether that proposal is correct. If incorrect, the student must name
the **first** wrong step and explain the mathematical error.

<problem>
{problem}
</problem>

<verified_reference_solution>
{reference_solution}
</verified_reference_solution>

<target_label>{target_label}</target_label>
<requested_error_type>{error_type}</requested_error_type>
<requested_error_position>{error_position}</requested_error_position>

## Construct the proposal

1. Privately draft a concise, correct solution with stable IDs `S1`, `S2`, ...
   using the same method as the reference. Keep enough steps to make the
   requested error position meaningful. Incorrect proposals need at least
   three steps.
2. If the target is `correct`, verify every step, keep the draft valid, and
   set all private error fields to JSON `null`.
3. If the target is `incorrect`, **mutate one existing mathematical step** in
   that draft. All earlier steps must remain valid. The mutated step must make
   exactly one clear error of the requested type. Later steps may propagate
   that error, but they should not introduce an unrelated mistake.
4. Preserve the reference method. Do not finish a valid solution and then
   append an unrelated false theorem, counting claim, or conclusion. Do not
   relabel an arithmetic or indexing mistake as a counting/bijection error.
5. An incorrect proposal may still end with the correct final answer, but the
   first invalid inference must be visible. Avoid consistent label cues in
   length, formatting, or wording.
6. If the requested error type cannot occur naturally within this source
   method, return exactly `NOT_SUITABLE`. Do not manufacture an irrelevant
   step to satisfy the type.

## Requested location

For an `n`-step incorrect proposal, the annotated first wrong step `Si` must
fall in the requested third of the solution: `early` when
`floor(3*(i-1)/n)=0`, `middle` when it equals 1, and `late` when it equals 2.
For example, in a three-step proposal, S1 is early, S2 is middle, and S3 is
late. Keep the requested location even when the number of steps changes.

The requested error type is one of `arithmetic_algebra`, `sign_inequality`,
`invalid_theorem_condition`, `unjustified_implication`, `missing_case`,
`domain_restriction`, `counting_bijection`, or `other`. For a correct item the
requested type and position are `none`.

## Output

Return raw JSON only, with no surrounding prose or code fence:

```json
{
  "public": {
    "problem": "Copy the source problem exactly.",
    "proposed_solution": [
      {"step_id": "S1", "text": "..."},
      {"step_id": "S2", "text": "..."},
      {"step_id": "S3", "text": "..."}
    ],
    "instruction": "Decide whether the proposed solution is correct. If it is incorrect, identify the first wrong step and explain the mathematical error."
  },
  "private": {
    "label": "correct or incorrect",
    "first_error_step_id": null,
    "first_error_explanation": null,
    "error_type": null,
    "error_position": null,
    "teacher_target_response": "Decision: correct|incorrect\nFirst wrong step: S2|none\nExplanation: Concise mathematical justification."
  }
}
```

For an incorrect item, replace the four `null` values with the actual first
wrong step ID, its mathematical explanation, the requested type, and the
requested position. The teacher target must agree with the private annotation.
Do not expose the reference solution or any private metadata inside `public`.
