# JUDGE dataset plan

Status: execution plan, 21 September 2026. Scope: design, generate, validate, and freeze the JUDGE task dataset required by the [project proposal](docs/references/ministry-of-superintelligence-proposal.pdf). The proposal's 12 single-form training runs (3 forms × 2 methods × 2 seeds) and transfer analysis follow this dataset work.

Current execution status: the repository contains a deterministic private 60-source development manifest, generator prompt candidates, student and grader prompts, a resumable vLLM runner, schema/privacy validation, public-only export, structural reporting, local tests, and a two-checkpoint Transformers smoke test. The four prepared Qwen artifacts each have 120 requests but no generated responses. **24 September update:** the initial matched four-source prompt comparison has been run with GPT-Luna agents: 31/32 candidates were produced, independently reviewed by GPT-Luna, and three requested-position mismatches plus an unnatural error-type assignment were found. A revised fifth prompt and stricter position validator now address these issues; see `docs/design/judge-luna-pilot.md`. These exploratory outputs have separate GPT-Luna provenance. Qwen3-8B still supplies the proposal's teacher-generated dataset; Qwen3-1.7B remains the student baseline. The Slurm wrapper is `scripts/run_judge_slurm.sh`.

## Goal and constraints

For each retained source mathematics problem, the student sees the problem and a proposed, step-numbered solution. It must decide whether the solution is correct. If it is incorrect, it must identify **the first wrong step** and explain the mathematical error. A correct proposal has no first-error step.

The proposal calls for 4,096 DeepMath training source problems, a separate DeepMath development set, and a final test set of 1,024 held-out DeepMath plus 500 text-only OlympiadBench/MathBench problems. SOLVE, PLAN, and JUDGE variants of one source share a split. The target is one JUDGE item per source, with approximately half correct and half incorrect proposed solutions in each split; thus the nominal JUDGE counts are 4,096 train and 1,524 final test items. The development size is not specified in the proposal; use **256 DeepMath sources as a planning target**, subject to feasibility and coordination with the other task owners. Reserve extra candidate sources for failures. Record the final split sizes before prompt tuning.

The student is **Qwen3-1.7B** and the teacher is **Qwen3-8B**, both in instruction-following mode with `enable_thinking=False`. An independent strong model, such as the existing DeepSeek V4 Flash endpoint, grades open-ended JUDGE outputs; it must not generate training targets or provide distillation probabilities. Freeze its model, prompt, rubric, and decoding settings before final evaluation. The proposal's maximum generation length for training experiments is 4,096 tokens; measure actual Judge prompt and response lengths during dataset construction so the later training setup is feasible.

## Models and resources to obtain first

| Resource | Purpose | Action |
| --- | --- | --- |
| GPT-Luna agent | Initial prompt design, four-candidate experiments, and early mathematical audits while the cluster is unavailable | Run on development sources only. Record the agent model and prompt hash, retain raw and validated outputs separately, and audit mistakes. These outputs are exploratory and are not Qwen teacher targets. |
| [Qwen/Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) and its tokenizer | Proposal teacher for the dataset and later checkpoint-specific confirmation | Download an exact checkpoint revision to the user-owned model cache; record commit hash, tokenizer revision, dtype, chat template, and generation settings. Run a one-batch non-thinking smoke test. |
| [Qwen/Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B) and its tokenizer | Unchanged student baseline for prompt diagnostics and eventual training | Download an exact revision; run the same chat-template smoke test. Verify tokenizer vocabulary and token IDs match the 8B teacher before planning reverse-KL work. |
| Existing DeepSeek V4 Flash API endpoint | Independent semantic grader and auditing aid | No local checkpoint download. Verify availability and pin the provider model identifier; keep its calls and records separate from teacher generation. |
| [DeepMath-103K](https://huggingface.co/datasets/zwhe99/DeepMath-103K) | Main source pool | Pin a dataset revision. Track row IDs and question hashes. The upstream card documents revised answer-leaking questions, so use one fixed revision and scan for leakage. |
| [OlympiadBench](https://github.com/OpenBMB/OlympiadBench) and [MathBench](https://github.com/open-compass/MathBench) | Final out-of-domain test pool only | Obtain official text-only releases and pin versions. Keep all these problems out of prompt development and student training. |

The repository currently evaluates Qwen3-4B on a 113-problem pilot and uses DeepSeek to generate SOLVE/EXPLAIN artifacts. Those are useful for understanding schemas and exercising code, but they are not the proposal's teacher/student pair. Do not label existing DeepSeek-generated text as Qwen3-8B teacher data. Check model storage and GPU memory on the actual machine before a large download or run; start with the one-batch test.

## Data contract to agree with the other task owners

Store one source record with `source_id`, `source_dataset`, source revision, original question, verified answer, independently checked derivation, main method, assumptions, topic, difficulty, and split. Derivations from DeepMath traces need review: a matching final answer does not prove every intermediate step is valid. If a source lacks a trustworthy solution, repair it or exclude that source from **all three** matched forms.

Each JUDGE item has a public view and a private view. Suggested fields:

```json
{
  "source_id": "...",
  "split": "train",
  "public": {
    "problem": "...",
    "proposed_solution": [
      {"step_id": "S1", "text": "..."},
      {"step_id": "S2", "text": "..."}
    ],
    "instruction": "Decide whether the proposed solution is correct. If incorrect, identify the first wrong step and explain why."
  },
  "private": {
    "label": "incorrect",
    "first_error_step_id": "S2",
    "first_error_explanation": "...",
    "error_type": "invalid_theorem_condition",
    "error_position": "early",
    "verified_reference_solution": "...",
    "teacher_target_response": "...",
    "generation_provenance": {"model": "Qwen/Qwen3-8B", "revision": "...", "prompt_sha256": "..."}
  }
}
```

For a correct item, use `label=correct`, `first_error_step_id=null`, and `error_type=null`. Give steps stable IDs and keep their visible numbering unchanged after annotation. Store hashes for the public prompt and private record. Export a **public prompt-only manifest** for inference; gold fields must never be sent to the student. Use one fixed student response schema, for example `decision`, `first_error_step_id`, and `explanation`, with `null` for the step on correct items. Define how malformed outputs are scored before evaluation.

Avoid generating both a correct and an incorrect item for the same source in the final dataset. Paired candidates are useful during development, but selecting one per source keeps the proposed denominator and avoids near-duplicate evaluation items. Balance labels within source dataset, topic, and difficulty band where feasible. Use an allocation script and seed, not generation order, to decide which source receives which label. Preserve a canonical proposed solution if generating a wrong variant; the mutation and its exact location must be traceable.

## Prompt experiments: choose a generator before scaling

Use only the development pool and a small, manually adjudicated pilot. The existing 146-source manifest can be used as exploratory material **only if those source IDs are assigned to development and excluded from every final test split**. It is currently a pilot, not a locked proposal split.

1. **Build a gold diagnostic set.** Select 60 development sources across the eligible topics and two difficulty bands, including numeric, symbolic, proof, and case-analysis problems. Manually verify their reference derivations. For each, make or adjudicate one valid proposal and one proposal with a known first error. Two annotators should independently label a useful subset, then resolve disagreements. Save these labels separately from generated output.
2. **Define the error taxonomy.** Include arithmetic/algebra, sign or inequality direction, invalid theorem precondition, unjustified implication, missing case, domain restriction, counting/bijection, and geometry/diagram-free reasoning where applicable. Tag first-error position as early, middle, or late. Do not force every type onto every topic; record impossible combinations.
3. **Write four generator prompt candidates** in `data/prompts/judge/`: (A) one-pass generate with explicit rubric, (B) one-pass with two short examples, (C) draft a correct step-numbered proposal then mutate one chosen step, and (D) the two-stage approach with examples and an explicit self-check of earlier steps. Run the initial matched-source comparison with GPT-Luna agents. Keep source inputs and output schema fixed, record prompt hashes and agent provenance, and generate correct/incorrect candidates for the same sources for *prompt comparison only*. Agent experiments do not provide controlled checkpoint decoding settings, so do not compare their token cost or scores directly to Qwen inference.
4. **Score generator quality while blind to prompt identity.** Measure JSON/schema validity; mathematical validity of correct candidates; whether incorrect candidates really fail at the annotated first step; whether all prior steps are sound; whether the intended method is preserved; whether the error is understandable without seeing private metadata; label balance; distribution of error types/positions; answer or label leakage; length and token cost. Review all ambiguous cases manually. Never use mere final-answer disagreement as the only proof of an error.
5. **Stress-test the two best prompts** on a fresh 100-source development set. Include cases with alternative valid proofs, coincidentally correct final answers after invalid reasoning, multiple plausible error locations, and long solutions. GPT-Luna can perform this initial generator stress test. Before freezing Qwen-produced data, run Qwen3-1.7B and Qwen3-8B on identical public Judge prompts with the same non-thinking decoding settings. The 8B teacher should outperform the unchanged 1.7B student on JUDGE; the proposal also requires this check on SOLVE and PLAN, coordinated with those task owners. Diagnose whether the student is exploiting cues such as wrong answers, longer wrong solutions, fixed error positions, or label wording.
6. **Choose a prompt candidate and confirm it with the Qwen teacher.** Prioritize audited first-error correctness and method preservation; then coverage, balanced diversity, prompt length, and student baseline difficulty. Record a GPT-Luna comparison table, prompt hashes, agent provenance, selection rule, and rejected candidates. Once Qwen3-8B is available, confirm the candidate on a fresh development subset and record its checkpoint revision, settings, token cost, and any prompt revision. Freeze only after the Qwen confirmation; do not choose prompts using final-test outputs. If no prompt meets the agreed quality gates, revise and repeat the development experiment.

Suggested gates to set *before* the comparison: at least 95% audited label/first-error correctness and at least 90% correct-method preservation among retained items; no unreviewed ambiguous first-error labels; 100% schema validity after deterministic validation or explicit rejection. These are project decisions, not numbers specified by the proposal. Report confidence intervals for audit estimates and revisit the gates if the target sample is too small to support them.

## Build and validate the full dataset

1. **Lock source splits before bulk generation.** Deduplicate normalized questions and near duplicates across DeepMath and external pools; keep source families together. Reconcile the current four-topic pilot (which includes calculus) with the proposal's target topics (algebra, number theory, combinatorics, discrete mathematics, and text-only geometry). Confirm feasible topic quotas with the other task owners and document any departure. Match difficulty distributions across train/development/test.
2. **Create verified source records.** For each selected source, check the answer, derivation, main method, assumptions, and whether text alone suffices. Avoid image-dependent geometry and problems whose solution cannot be safely repaired. Use a held-out reserve pool so removals do not alter the final targets unpredictably.
3. **Assign labels and error quotas.** Exactly one chosen candidate per source. Aim for 2,048 correct and 2,048 incorrect train items; 512/512 DeepMath test and 250/250 external test if feasible. Balance within topic and difficulty. Allocate incorrect items across error types and early/middle/late positions; keep selection seeded and auditable. The 256-item development target would be 128/128.
4. **Generate in resumable batches.** For each source, ask Qwen3-8B for the assigned variant from the verified solution record. For wrong variants, constrain it to the same mathematical method and one identifiable first error. Generate the teacher's ideal Judge response as a separate private field. Persist raw outputs, parsed outputs, model/prompt revisions, finish reasons, token counts, and failure reasons; re-run only failed or rejected records.
5. **Apply deterministic checks.** Validate schema and step IDs; enforce nonempty steps and private/public separation; check correct-label answers against gold; run safe arithmetic, symbolic substitution, and executable claims where applicable; ensure wrong variants differ from the canonical solution at the annotated step; check final answer tags and question/answer leakage; check duplicate proposals, length limits, error-type/position counts, and split overlap. Mark uncertain mathematics for human review rather than silently accepting it.
6. **Audit mathematical validity.** Blindly review a random, stratified sample from every split, oversampling rare error types and late errors. Verify every step before the marked first error, the alleged error itself, the correctness of the teacher target, and preservation of the source concept. Review all automatic-check disagreements and all ambiguous items. Use two reviewers for a subset, record agreement and adjudication, then correct or remove invalid items. If audit error rates exceed the predeclared gate, inspect that stratum and regenerate or remove affected records.
7. **Run leakage and shortcut diagnostics.** Train simple classifiers on superficial features (length, position, number formatting, words such as “therefore”) and test correct/incorrect predictability. Verify both classes can contain the same final answer and similar solution length where mathematically appropriate. Inspect whether a student can succeed by checking only the last line. Rebalance or regenerate if an obvious cue predicts labels.
8. **Freeze exports.** Produce train, development, DeepMath test, and external test manifests with one item per source and immutable source IDs. Store public prompts separately from restricted labels/reference solutions. Include source and checkpoint revisions, prompt hashes, selection seed, exclusions, audit decisions, per-stratum counts, mean/percentile token lengths, and a manifest checksum. Do not place private references inside prompts, logs shown to students, or training inputs except the intended teacher target response.

## Judge evaluation calibration before final test use

Write a fixed grader rubric that checks: (1) decision, (2) for incorrect proposals, localization to the *first* wrong step, and (3) the mathematical explanation of that error. For correct proposals, require a correct decision and no fabricated error. Accept equivalent descriptions of the same first wrong inference. Score malformed or missing responses explicitly. Report decision accuracy, first-error localization conditional on incorrect items, explanation accuracy, and strict full-task accuracy. Also report per-label, per-topic, per-difficulty, per-error-type, and per-position results.

On a separate development calibration set, compare the independent grader with human annotations. Inspect disagreements, refine the rubric only on development data, freeze model/prompt/decoding, and save a rubric hash. Audit a random sample of final student outputs and report human–grader agreement, as required by the proposal. Keep the final 1,524-source test untouched until all prompts, checkpoint choices, mixtures, and curricula are fixed. Judge data construction ends at the frozen manifests; the later training pipeline uses the same public Judge prompts for off-policy targets and on-policy student rollouts.

## Implementation work in this repository

- Add `data/prompts/judge/` for versioned generator, student, and grader prompts; document the chosen schema and error taxonomy in `docs/design/judge-task.md`.
- Add a source/split builder and `src/anlp_project/judge_generation.py` plus `scripts/generate_judge.py`, reusing the repository's JSON persistence, resumable batch pattern, and prompt hashing.
- Add `src/anlp_project/judge_validation.py` for deterministic checks and public/private export; add a separate audit ledger rather than overwriting raw generations.
- Extend `src/anlp_project/qwen3_turing_eval.py` or add a dedicated Judge runner for both Qwen3 checkpoints, `enable_thinking=False`, batch logging, and prompt-only inference. Update the Turing job wrapper for the new model IDs and cache paths after a GPU smoke test.
- Add a fixed grader runner, report exporter, and tests for schema rejection, step numbering, first-error labels, private-field leakage, split isolation, resumability, and exact scoring of hand-constructed cases.
- Keep the current 113-source verified SOLVE subset as a smoke/development resource only after verifying its source IDs do not enter the final test set. The existing EXPLAIN generator is a structural code template; its prompt content does not define JUDGE correctness.

## Proposed timeline and exit criteria

| Dates | Work and experiment | Exit artifact |
| --- | --- | --- |
| 20–24 Sep 2026 | Confirm shared source IDs/splits and topic quotas; build the 60-source pilot; run initial matched-source GPT-Luna prompt experiments and blind agent review; revise prompts and validators. | Versioned GPT-Luna artifacts, preliminary comparison, known failure modes. |
| 25–28 Sep | Manually verify and adjudicate pilot source derivations; extend GPT-Luna comparison across the development pool; inspect label, position, type, and method preservation. Pin source/model revisions. | Human-adjudicated pilot labels and shortlisted prompts. |
| 29 Sep–2 Oct | Stress-test shortlisted prompts on fresh sources using GPT-Luna. When persistent share and GPU access are available, download both Qwen checkpoints; confirm the selected generator with Qwen3-8B, evaluate Qwen3-1.7B versus Qwen3-8B on identical public tasks, and freeze settings. | Chosen prompt/hash, Qwen confirmation, teacher-student pilot results, rejection rules. |
| 3–6 Oct | Build verified train/development/DeepMath-test/external-test source records; deduplicate; generate assigned Judge variants in batches. Prioritize 4,096 train items for the proposal's planned training run. | Raw and parsed Judge batches with provenance, coverage report. |
| 7–10 Oct | Run executable and schema checks; stratified human audit; regenerate or exclude invalid items; create replacement sources where needed. | Audit ledger, error analysis, corrected candidate set. |
| 11–13 Oct | Calibrate external grading on development data; freeze grader; run final balance/leakage/split checks and public/private export. | Versioned 4,096-item train set, development set, and locked 1,524-item final test set with data card and checksums. |

The dates are an execution target based on the proposal's September/October schedule, not a claim that generation throughput, GPU access, or human review capacity has been secured. If a gate fails, record the delay and repeat that stage; never silently lower the validation standard. The **dataset is ready** only when all retained items have trusted labels and first-error annotations, the target counts and source isolation are verified, the teacher-student pilot is reported, and the final-test prompts and rubric are frozen.
