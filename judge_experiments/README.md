# Judge prompt experiments

This folder is the entry point for the Judge-task prompt experiments. The
canonical prompts, source manifest, generated outputs, and runnable code stay
in their existing repository locations so the current scripts keep working.
This folder records what was tested and links to every experiment artifact.

## Scope and provenance

- Goal: generate step-numbered mathematical solutions for which a judge must
  decide correctness and, if incorrect, identify the first wrong step.
- Proposal-aligned final data still requires Qwen3-8B teacher generation and
  Qwen3-1.7B student evaluation. **No final Judge dataset has been generated.**
- All initial prompt outputs so far were made by GPT-Luna agents, not Qwen.
  Their labels and math have not been human-adjudicated.
- Inputs were four sources from the 60-source private development manifest,
  itself derived from the existing DeepSeek V4 Flash SOLVE results. The
  reference solutions are model-generated and are not human gold proofs.

## Tested problems

| Source | Area | Problem | Reference answer |
| --- | --- | --- | --- |
| `pilot-0` | Algebra | Polynomial/integral identity; find `3(alpha-beta)^2` | `4` |
| `pilot-10` | Number theory | Find `51! mod 61` | `27` |
| `pilot-38` | Discrete math | Tower of Hanoi recurrence via generating functions | `2^n - 1` |
| `pilot-41` | Calculus | Sum `n^2/3^n`, `n >= 1` | `3/2` |

Each prompt was asked for one correct and one incorrect proposed solution per
source. These four sources are a smoke test, not a representative quality
sample.

## Results as of 24 September 2026

| Prompt | Generated / requested | Structural result | Main observed problem |
| --- | ---: | --- | --- |
| v1 rubric | 8 / 8 | 8 initially valid | One requested error position mismatch; some appended false claims |
| v2 examples | 8 / 8 | 8 initially valid | Miniature example in prompt is mathematically wrong; appended false claims |
| v3 mutate | 8 / 8 | 8 initially valid | Position mismatch and an error-type mismatch |
| v4 self-check | 7 / 8 | 7 initially valid | One unsuitable error-type request; position mismatch |
| v5 method-preserving | 7 / 8 | 7 pass tightened validator | One `NOT_SUITABLE`; one wrong-step item still ends with the correct numeric answer |

The first four prompts produced 31 of 32 requested outputs. Separate GPT-Luna
reviewers saw shuffled public-only items and agreed with the claimed labels
and first-error steps on all 31. This is **not independent human verification**.
Manual inspection found three error-position mismatches, one error-type
mismatch, and unnatural solutions that first reached the correct answer and
then appended an unrelated false statement. The initial validator missed
position mismatches; it was tightened before the v5 run.

V5 is the current **development candidate**, not a frozen or proven ideal
prompt. In its four-source smoke test it avoided the appended-false-claim
pattern, but refused the requested late theorem-condition error on `pilot-10`.
The `pilot-41` incorrect item asserts `1/3 > 1` and then gives the correct
numeric answer; this needs a dataset-policy decision and human review.

## Canonical files

| Material | Location |
| --- | --- |
| Full project plan | [`../judge_plan.md`](../judge_plan.md) |
| Judge task/schema design | [`../docs/design/judge-task.md`](../docs/design/judge-task.md) |
| Detailed pilot write-up | [`../docs/design/judge-luna-pilot.md`](../docs/design/judge-luna-pilot.md) |
| Development inputs | [`../data/manifests/deepmath/judge-dev-60-generator.json`](../data/manifests/deepmath/judge-dev-60-generator.json) |
| Generator prompts v1-v5; student/grader prompts | [`../data/prompts/judge/`](../data/prompts/judge/) |
| GPT-Luna raw generations, blind audits, key, and comparison | [`../artifacts/gpt-6-luna/judge/`](../artifacts/gpt-6-luna/judge/) |
| Prepared Qwen requests only; **no Qwen generations** | [`../artifacts/qwen3-8b/judge/`](../artifacts/qwen3-8b/judge/) |
| Generation/validation/report implementation | [`../src/anlp_project/`](../src/anlp_project/) (`judge_*.py`, `build_judge_dev_manifest.py`) |
| Command wrappers | [`../scripts/`](../scripts/) (`*judge*`) |
| Unit tests | [`../tests/`](../tests/) (`test_judge_*.py`) |

## Next gate before dataset generation

Run v5 (and any revision) on fresh sources in the development manifest with
GPT-Luna, tracking both output validity and refusals. Blind-review the math,
first-error step, error type/position, and method preservation; then have a
person adjudicate a stratified sample. Decide whether an incorrect proof that
ends in the correct answer is allowed. Freeze the prompt and split only after
these checks. Later, confirm the frozen prompt on Qwen3-8B before producing
the proposal-aligned teacher dataset. Keep GPT-Luna exploratory outputs out
of final train/test data.
