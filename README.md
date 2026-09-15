# ANLP Mathematical Reasoning Evaluation

This repository contains reproducible generation, verification, and evaluation
tools for DeepMath SOLVE and EXPLAIN tasks.

## Layout

- `src/anlp_project/` — reusable generation, verification, manifest, and report code.
- `scripts/` — stable command-line entry points.
- `data/manifests/` — tracked problem manifests and evaluation subsets.
- `data/prompts/` — versioned SOLVE, EXPLAIN, and PLAN prompts.
- `artifacts/` — curated model outputs, reports, and evaluation evidence.
- `docs/` — experiment design, dataset notes, and Turing guidance.
- `tests/` — deterministic unit tests.

The local DeepMath Arrow dataset, wheelhouse, virtual environment, API secrets,
logs, and superseded runs are intentionally excluded from Git. Superseded files
remain under ignored `data/legacy-*` or `local/archive/` directories when they
are useful for historical reference.

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
```

For Turing execution, use the shell wrappers in `scripts/` after syncing this
repository to the user-owned project path. They run the package from `src/` and
keep model environments and GPU caches on the configured scratch partition.

The Colab notebook workflow is currently archived and intentionally not part of
the repository baseline.

## Reproducibility policy

Tracked artifacts are curated evidence for the current evaluations: DeepSeek
V4 Flash SOLVE verification v2, DeepSeek EXPLAIN-v2 output, and Qwen3-4B SOLVE
results. Raw transport logs, temporary bundles, old pilot runs, and incomplete
experiments are retained locally only. Reports are stored beside the result they
describe rather than in a separate unstructured report directory.
