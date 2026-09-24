# JUDGE task contract

JUDGE tests whether a student can inspect a proposed mathematical solution,
decide whether it is correct, and—when it is not—identify the **first** wrong
step and explain the mathematical error. It is not a SOLVE task: the student
must check the visible derivation in order rather than independently solve the
source problem.

## Public/private boundary

The generator receives a verified source problem and reference derivation. Its
private output has the target label, first-error annotation, error taxonomy,
reference provenance, and teacher target response. The student-facing export
contains only:

```json
{
  "source_id": "...",
  "source_index": 0,
  "split": "development",
  "public": {
    "problem": "...",
    "proposed_solution": [
      {"step_id": "S1", "text": "..."},
      {"step_id": "S2", "text": "..."}
    ],
    "instruction": "Decide whether the proposed solution is correct. If it is incorrect, identify the first wrong step and explain the mathematical error."
  },
  "public_sha256": "..."
}
```

`reference_solution`, `label`, `first_error_step_id`, private explanations,
and teacher targets must never appear in a public export. The exporter rejects
unfinished or schema-invalid generations and writes a separate audit ledger.
For final splits, use exactly one accepted item per source; paired correct and
incorrect candidates are permitted only during prompt development.

## Generator requirements

- Use stable, consecutive step IDs `S1`, `S2`, ... .
- Correct proposals have valid steps and null first-error metadata.
- Incorrect proposals preserve all steps before the first error and contain one
  identifiable local error at the requested type and position.
- The visible proposal should preserve the source method and avoid shortcuts
  such as always making incorrect solutions longer or giving them absurd final
  answers.
- Correct and incorrect examples should be balanced within split, topic, and
  difficulty where the source pool permits.

The current development taxonomy is `arithmetic_algebra`,
`sign_inequality`, `invalid_theorem_condition`, `unjustified_implication`,
`missing_case`, `domain_restriction`, `counting_bijection`, and `other`.
Positions are `early`, `middle`, and `late`. An impossible type/topic
combination must be recorded and regenerated rather than forced silently.

## Student response and scoring

The fixed response format is:

```text
Decision: correct|incorrect
First wrong step: <step ID or none>
Explanation: <concise mathematical justification>
```

The local scorer checks parsing, decision equality, and first-error-step
equality. Explanation correctness is semantic and must be evaluated by the
independent grader using `data/prompts/judge/judge_grader.md`, then calibrated
against human annotations. Report decision accuracy, first-error accuracy
conditional on incorrect items, explanation accuracy, and strict full-task
accuracy. Malformed outputs must be reported separately and must not be silently
converted into incorrect mathematics.

## Construction stages

1. Verify source answers and reference derivations.
2. Generate paired candidates on the 60-source pilot with all four prompt
   candidates.
3. Blind-audit schema validity, first-error correctness, method preservation,
   error coverage, length, and shortcut cues.
4. Stress-test the two best prompts on a fresh development set, then freeze the
   generator checkpoint, prompt hash, decoding settings, and grader rubric.
5. Generate assigned one-per-source variants for train, development, DeepMath
   test, and external test splits.
6. Run deterministic checks, stratified human review, leakage diagnostics, and
   public/private export before any student training or final evaluation.
