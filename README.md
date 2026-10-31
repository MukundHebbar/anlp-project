# ANLP Mathematical Reasoning Evaluation

This repository contains reproducible generation, verification, and evaluation
tools for DeepMath SOLVE, JUDGE, and RECONSTRUCT tasks.

## Final dataset

[`data/manifests/final-v3/`](data/manifests/final-v3/README.md) holds the training and testing data
for all three tasks: **4,000 questions each, 3,600 train / 400 test**. The three tasks use completely
separate DeepMath-103K questions, matched by topic and difficulty distribution rather than by
item, and every row has a `training` block (`input`, `chain_of_thought`, `final_answer`).
The reported transfer experiments use Dr. GRPO; historical OPD code and records are retained for provenance. See the
[study design](docs/design/reasoning-transfer-study.md#fixed-design-decisions). The files are stored as `.jsonl.gz`. Check them with
`.venv/bin/python scripts/audit_final_dataset.py`; this needs the DeepMath parquet files in
`data/datasets/deepmath-103k/`, which are re-downloadable from HuggingFace `zwhe99/DeepMath-103K`.

## Layout

- `src/anlp_project/` — reusable generation, verification, manifest, and report code.
- `scripts/` — stable command-line entry points.
- `data/manifests/` — tracked problem manifests and evaluation subsets.
- `data/prompts/` — versioned SOLVE, EXPLAIN, and PLAN prompts.
- `artifacts/` — curated model outputs, reports, and evaluation evidence.
- `docs/` — tracked experiment design and dataset notes.
- `tests/` — deterministic unit tests.

The local DeepMath Arrow dataset, wheelhouse, virtual environment, API secrets,
logs, and superseded runs are intentionally excluded from Git. Superseded files
remain under the ignored `local/archive/legacy/` directory when they are useful
for historical reference.

`docs/guides/turing.md` is a local operational guide and is intentionally
ignored. It is not required to install, test, or inspect the repository.

## Setup

Python 3.12 is the supported local version.

```bash
uv sync
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

The optional local-data and notebook dependencies are available with:

```bash
uv sync --extra data --extra notebooks
```

Set `DEEPINFRA_API_KEY` in the ignored `.env` file before running DeepInfra
generation. No API keys are stored in manifests or artifacts.

## Common commands

```bash
uv run scripts/build_manifest.py --help
uv run scripts/generate_solve.py --help
uv run scripts/generate_explain.py --help
uv run scripts/verify_deepseek.py --help
uv run scripts/run_qwen.py --help
uv run scripts/verify_qwen.py --help
uv run scripts/run_reconstruct.py --help
```

Run any command with `--help` before a new experiment to inspect its required
inputs and defaults. Generation commands require `DEEPINFRA_API_KEY`; local
verification commands do not make provider requests.

RECONSTRUCT uses local `Qwen/Qwen3-4B` in explicit non-thinking mode for the
student and DeepSeek V4.1 Flash through DeepInfra for conversion, independent
bank auditing, and source-blind scoring. Its current protocol and adaptive
experiment plan are in
[`docs/design/reconstruct/SKILL.md`](docs/design/reconstruct/SKILL.md) and
[`docs/plans/2026-09-20-reconstruct-adaptive-eight-hour-plan.md`](docs/plans/2026-09-20-reconstruct-adaptive-eight-hour-plan.md).
The completed development pilot and stopping decision are in
[`docs/research/reconstruct/pilot-2026-09-20.md`](docs/research/reconstruct/pilot-2026-09-20.md).
The [final operational version](docs/design/reconstruct/FINAL_V1.md) is frozen at
**four clues plus the final answer**, using the repaired PC-v4 judges. The
[100-source run and question/answer export](artifacts/reconstruct/final-100-v1/questions-answers.md)
records every selected source and its validity, response and rating status.
The completed [100-source results](artifacts/reconstruct/final-100-v1/report.md)
contain **52 gate-passed tasks, 50 parsed Qwen responses and 47 resolved scores**.
The mean is **44.41/100**; rating counts from1 to5 are **4,11,29,3,0**.
There are **2 reviewed semantic recoveries and0 fully grounded recoveries**:
the average-score target is met, but the20–40% reconstruction-success target is not.
Download the [question/answer CSV](artifacts/reconstruct/final-100-v1/questions-answers.csv)
or the [complete results bundle](artifacts/reconstruct/final-100-v1/reconstruct-final100-deliverables.zip).
The current [rating policy v4](artifacts/reconstruct/balanced-ratings-v4/report.md)
uses cutoffs18.75,43.75,56.25,75. On the same47 resolved scores, counts are
**3,12,18,12,2**. Only the2/3 boundary changed from v3: six lower-scoring3s
move to2; ratings1,4,5 are unchanged. This is post-hoc development calibration,
not evidence of Gaussian scores or improved model performance.
Use the [updated question/answer CSV](artifacts/reconstruct/balanced-ratings-v4/questions-answers.csv).
Numerical scores and success labels remain unchanged; earlier rating versions
and the original100-source results are preserved.
The [extension to100 completely scored, gate-passed examples](docs/plans/reconstruct-valid-100-extension.md)
is continuing under a [transport-recovery amendment](docs/plans/reconstruct-valid100-transport-recovery.md)
after a connection-failure burst stopped the first phase at53 complete rows.
Prompts and v4 thresholds are unchanged; successful responses are reused, only
transport failures permit one retry, and a circuit breaker prevents request bursts.
It retains47 calibration rows and adds53 new rows in a frozen source order. Follow the
[live cohort summary](artifacts/reconstruct/valid-100-recovery-v1/summary.json) and
[question/answer export](artifacts/reconstruct/valid-100-recovery-v1/questions-answers.csv).
The export is incomplete until `target_met` and `terminal` are both true.
The latest [information-bracket experiment](artifacts/reconstruct/bridge-composition-ax/decision.md)
reached **2 verified recoveries in 6 scheduled development examples** using richer
symbolic clues and a premises-first prompt. One success required a documented
mathematical adjudication; the automatic gate alone accepted one. The mean raw
quality score is66.67/100, but the rating distribution remains polarized. This
meets the immediate recovery goal, not final benchmark validation.
The new [partial-credit specification](docs/design/reconstruct/PARTIAL_CREDIT_V1.md)
is not yet validated. Its [BA distribution check](artifacts/reconstruct/partial-credit-ba/decision.md)
on saved responses found no middle-heavy score distribution and documented judge
equivalence/shortcut errors; it does not validate the new generation prompts.
The [repaired partial-credit judges](docs/design/reconstruct/JUDGE_VERIFICATION.md)
now pass all19 registered development controls, including five saved-response
regressions, under the final prompts and validator. [Full calibration history](artifacts/reconstruct/judge-calibration-be/decision.md)
retains earlier failures and the one whitespace-only quote-validation repair.
This fixes tested grading boundaries; unseen accuracy and the desired score
distribution remain unvalidated.
The current definitions and release criteria are consolidated in
[CURRENT_PROTOCOL.md](docs/design/reconstruct/CURRENT_PROTOCOL.md), with a
[claim-to-evidence report](docs/research/reconstruct/current-evidence.md).
The earlier [three-clue exposure](artifacts/reconstruct/target-prefix-ap/decision.md)
admitted 7/16 sources and averaged 28.57/100, but produced no standalone semantic
recoveries and a five-level histogram of `[2,4,0,0,1]`.
[Repeated seeds](artifacts/reconstruct/student-variance-as/decision.md) preserve
the same comparable ratings; this is seven families, not 21 independent examples.
The [fresh matched SOLVE control](artifacts/reconstruct/matched-solve-aq/decision.md)
returned 7/15 correct answers but only 3/15 strictly reviewed explanations.
No final generator/judge combination is approved.
The earlier [fresh-cohort disclosure-policy comparison](artifacts/reconstruct/constructive-gate-al/decision.md)
admitted six inputs but yielded 0/6 semantic or grounded recoveries, with a mean
score of 10/100 on five readable outputs and one token-cap failure. One response
correctly inferred a missing parameter but changed the requested question.
The earlier [single-premise and output-order report](artifacts/reconstruct/one-gap-ah/decision.md)
tests exactly matched public inputs: neither order produced a correct semantic
reconstruction (0/3 each). The [matched direct SOLVE control](artifacts/reconstruct/matched-solve-ai/decision.md)
got 4/12 answers correct and 3/12 with valid justifications. The [earlier screen](artifacts/reconstruct/richer-exposure-aa/final-report.md)
includes a prompt variant with 1/3 semantic recoveries but 0/3 grounded recoveries.
The 20–40% correctness target and 25-family confirmation remain unvalidated.
After building `llama.cpp` with CUDA and downloading the official Q4_K_M GGUF,
start the loopback-only server with `scripts/run_local_qwen.sh start`. The
resumable runner supports `convert`, `audit`, `disclose`, `audit-disclosure`,
`student`, `evaluate`, `recover`, `validate-judge`, and `report` stages. Run
each subcommand with `--help`; provider stages enforce a configurable cost cap.

For Turing execution, use the shell wrappers in `scripts/` after syncing this
repository to the user-owned project path. They run the package from `src/` and
keep model environments and GPU caches on the configured scratch partition.

The Colab notebook workflow is archived and intentionally not part of the
repository baseline.

## Current evaluation evidence

**Zero-training baselines on FINAL-v3** for the student (Qwen3.5-4B) and teacher
(Qwen3.8-27B), with all three tasks scored by the repository pipelines, are in
[artifacts/baselines/final-v3/REPORT.md](artifacts/baselines/final-v3/REPORT.md). The method is in
[README.md](artifacts/baselines/final-v3/README.md) and every decision and incident is in
[RUN_LOG.md](artifacts/baselines/final-v3/RUN_LOG.md).

The earlier results below use Qwen3-4B on pilot pools, not FINAL-v3. The retained SOLVE
results and their non-identical evaluation denominators are summarized in
[artifacts/solve-evaluation-summary.md](artifacts/solve-evaluation-summary.md).

- DeepSeek V4 Flash SOLVE: full 146-problem manifest, verifier-v2 results and
  report under `artifacts/deepseek-v4-flash/solve/146/`.
- DeepSeek V4 Flash EXPLAIN-v2: retained generation artifacts under
  `artifacts/deepseek-v4-flash/explain/v2-113/`.
- Qwen3-4B SOLVE: 113-problem subset, independently scored only against
  dataset gold answers under `artifacts/qwen3-4b/solve/113/`.

## Reproducibility policy

Tracked artifacts are curated evidence for the current evaluations: DeepSeek
V4 Flash SOLVE verification v2, DeepSeek EXPLAIN-v2 output, and Qwen3-4B SOLVE
results. Raw transport logs, temporary bundles, old pilot runs, and incomplete
experiments are retained locally only. Reports are stored beside the result they
describe rather than in a separate unstructured report directory.

## Consolidated project results (30 October 2026)

- [Latest Phase 2 report](docs/reports/phase2-full-report.md) and [separately named working report](docs/reports/phase2-full-report_yashas.md).
- [Completed Llama GRPO transfer matrix](artifacts/baselines/llama3b/grpo-matrix.md), [evidence](artifacts/baselines/llama3b/README.md), and [reproduction instructions](phase2/llama_transfer/README.md).
- [Task-mixture experiment and SOLVE-only controls, including both seeds](phase2/mix_control/README.md).
- [Local judge calibration](phase2/local_judge_calibration/README.md), [Ministral baseline](phase2/results/ministral-baseline/README.md), and [adapter archive inventory](phase2/results/adapter-archive/README.md).

This collection is based on `phase2-experiments`. Independent Phase 3 verification work remains on
[`phase3-verification-2026-10`](https://github.com/MukundHebbar/anlp-project/tree/phase3-verification-2026-10);
its separate trainer/reward changes have not been merged here. Existing branches were not rewritten.
