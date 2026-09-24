# GPT-Luna Judge prompt pilot

This is an exploratory prompt experiment on development sources. Its outputs
are **GPT-Luna agent** outputs. They are not Qwen3-8B teacher data and must not
be placed in the final training or test manifests.

## Matched-source smoke test

The first comparison uses source indices `0`, `10`, `38`, and `41` from
`data/manifests/deepmath/judge-dev-60-generator.json`, covering algebra,
number theory, discrete mathematics, and calculus. Each of the four prompt
candidates is applied to both a correct and an incorrect target for every
source. The requested error type and position come from the same assignments
used by `build_generation_items` in `judge_generation.py`.

## First run: 24 September 2026

The four GPT-Luna generator agents produced 31 of 32 requested candidates.
Candidate D rejected the `counting_bijection` request for the Tower of Hanoi
generating-function source. The initial JSON validator accepted all 31
generated objects. Separate GPT-Luna reviewers, shown only shuffled public
problems and proposed steps, agreed with all 31 generated labels and
first-error IDs. The machine-readable comparison is
`artifacts/gpt-6-luna/judge/pilot-comparison.json`; its audit is **not human
adjudication** and does not establish a quality rate from four source problems.

Additional inspection found three requested-position mismatches:

- Candidate A, source `pilot-0`: requested early; first error is S2 of 3
  steps, which is middle under the documented thirds rule.
- Candidate C, source `pilot-41`: requested middle; first error is S4 of 4
  steps, which is late.
- Candidate D, source `pilot-0`: requested early; first error is S3 of 4
  steps, which is middle.

Several incorrect examples derive the correct answer first and append a false
statement later, especially the Wilson-theorem and Hanoi examples. This makes
the task less natural and can provide an easy cue. Candidate C labels an
indexing error in the Hanoi generating-function derivation as
`counting_bijection`; its private type does not match the visible error.
Candidate B's miniature example is itself flawed: for real nonzero `x`,
`x²>0` does follow. These are prompt-design failures even where the local
schema validator and the blinded first-error reviewers agreed.

The next iteration uses `judge_generator_v5_method_preserving.md`, which
specifies exact position thirds, mutates an existing step, rejects unnatural
type/source combinations, and discourages appended false claims. The source
assignment now limits discrete-algorithm problems to arithmetic or inference
errors. Historical first-run artifacts retain their original prompt hashes and
assignments for reproducibility.

For each candidate record the prompt file and SHA-256 hash, agent model,
source ID, target label, requested error type and position, complete public and
private output, and deterministic validation errors. Any regeneration should
be a new version rather than silently replacing the first output.

## Blind mathematical audit

Reviewers should receive the problem and proposed steps without the private
label, prompt name, or claimed first-error step. For each item record:

| Field | Allowed values / check |
| --- | --- |
| `true_label` | `correct`, `incorrect`, `ambiguous` |
| `true_first_error_step_id` | `S1`...`Sn`, `null`, or `ambiguous` |
| `all_prior_steps_valid` | `yes`, `no`, `uncertain` |
| `reference_method_preserved` | `yes`, `no`, `uncertain` |
| `error_type_matches` | `yes`, `no`, `not_applicable`, `uncertain` |
| `error_position_matches` | `yes`, `no`, `not_applicable`, `uncertain` |
| `teacher_target_correct` | `yes`, `no`, `uncertain` |
| `label_shortcut` | free text; note obvious answer/length/wording cues |
| `mathematical_comment` | concise proof of the decision or problem found |

Blind reviews need adjudication before a prompt is ranked. Structural schema
validity is checked by code, but it does not establish that the proposed
mathematics or first-error annotation is sound. A four-source smoke test can
expose prompt failures; it cannot establish a reliable quality rate. Continue
on the rest of the 60-source development set and a fresh stress set before
freezing a generator.

## Model transition

The GPT-Luna comparison informs prompt editing and source-quality checks.
Once persistent model storage and a suitable GPU allocation are available,
confirm the selected prompt using pinned Qwen3-8B and use that checkpoint for
the proposal's teacher-generated data. Independently test Qwen3-1.7B on the
same public Judge tasks. Store the two models' artifacts in separate paths.

## Revised-prompt smoke result

The v5 method-preserving prompt was tested with GPT-Luna on the same four
sources, requesting one correct and one incorrect item per source. Seven of
eight requests returned objects passing the tightened structural validator.
The remaining request (`pilot-10::incorrect`, late theorem-condition error)
returned `NOT_SUITABLE`; the agent judged that particular combination hard
to realize naturally. Keep this refusal in the denominator when comparing
prompts, rather than silently replacing it.

The seven generated solutions no longer use the obvious pattern of completing
the correct answer and appending an unrelated false claim. The arithmetic
mutations in `pilot-0` and `pilot-38` are localized and have the requested
positions. The `pilot-41` incorrect item contains a false claim that
`1/3 > 1`, but still reaches the correct numerical answer. It can be a valid
first-error task, yet this is a potential label/answer shortcut and should be
flagged during human review. These observations are manual spot checks, not
a blinded or human adjudication of all v5 items.

Next, run v5 on fresh development sources with GPT-Luna, record suitability
and all validation failures, blind-audit first-error labels and method
preservation, then human-adjudicate a stratified sample. Do not promote v5
or generate the final dataset from this four-source smoke result alone.
