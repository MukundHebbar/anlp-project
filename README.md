# Specialization, Transfer and Composition of Mathematical Skills with GRPO

Aryama V Murthy, Mukund Hebbar, Yashas Nataraj Kotre, Anivarth Varma Penumetcha. Advanced NLP, Monsoon 2026, IIIT
Hyderabad.

We train Qwen3.5-2B with Dr. GRPO (LoRA) on three forms of the same mathematics, **SOLVE** (write a solution),
**JUDGE** (find the first wrong step in a solution) and **RECONSTRUCT** (recover a question from its answer and four
clues), and measure how each skill transfers to the others. One adapter trained on an equal mixture of the three
tasks is the best model: +17.1 SOLVE, +32.2 JUDGE error-finding and +18.3 RECONSTRUCT over the untrained model, with
no negative transfer. We then locate the checking skill in the network (LoRA layers 0–5) and ask whether the model can
use it to check its own answers: a judge trained on its own attempts improves, and a pre-registered contest-adaptive
verifier beats majority vote by +1.6 points at equal compute, but the gap between "right answer present" (91%) and
"right answer wins the vote" (80%) stays open.

## Released data and models

| What | Link |
|---|---|
| FINAL-v3 dataset: SOLVE, JUDGE, RECONSTRUCT, 4,000 each (3,600 train / 400 test) | [Aryama/deepmath-solve-judge-reconstruct](https://huggingface.co/datasets/Aryama/deepmath-solve-judge-reconstruct) |
| SOLVE adapter (step 66) | [Aryama/qwen3.5-2b-grpo-solve](https://huggingface.co/Aryama/qwen3.5-2b-grpo-solve) |
| JUDGE adapter (step 26) | [Aryama/qwen3.5-2b-grpo-judge](https://huggingface.co/Aryama/qwen3.5-2b-grpo-judge) |
| RECONSTRUCT adapter (step 104) | [Aryama/qwen3.5-2b-grpo-reconstruct](https://huggingface.co/Aryama/qwen3.5-2b-grpo-reconstruct) |
| Mixed-task adapter (step 75), the best model | [Aryama/qwen3.5-2b-grpo-mixed](https://huggingface.co/Aryama/qwen3.5-2b-grpo-mixed) |
| Phase 3: 23,200 own attempts with grades, judge scores and evidence-grid outputs | [Aryama/qwen3.5-2b-self-verification-attempts](https://huggingface.co/datasets/Aryama/qwen3.5-2b-self-verification-attempts) |

All adapters are LoRA r 64 on [Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B). Data: MIT (as DeepMath-103K);
adapters: Apache-2.0 (as Qwen3.5).

## Results at a glance

All numbers are on the 400-question test sets, paired against the untrained model, with 95% bootstrap CIs over
questions; one training seed per arm unless stated.

**Phase 1: cross-task transfer (Qwen3.5-2B).** Bold = own task.

| Trained on | SOLVE acc | JUDGE step % | JUDGE Youden J | RECON PC-v4 |
|---|---|---|---|---|
| SOLVE | **+16.6 [+13.8, +19.1]** | +8.8 [+2.1, +16.1] | +15.4 [+6.2, +23.8] | +3.8 [+1.4, +6.3] |
| JUDGE | −1.1 [−4.1, +1.9] | **+17.2 [+10.2, +24.0]** | **+28.4 [+19.5, +36.9]** | +6.0 [+3.3, +8.6] |
| RECONSTRUCT | −10.7 [−13.7, −7.7] | +14.2 [+7.2, +21.8] | +7.9 [−1.2, +17.0] | **+21.4 [+19.1, +23.5]** |
| Mixed (⅓ each) | **+17.1 [+14.3, +19.9]** | **+32.2 [+25.9, +38.6]** | **+45.4 [+37.4, +52.6]** | **+18.3 [+16.1, +20.5]** |

- **Mixture controls:** against SOLVE-only runs on the same 750 SOLVE questions, steps and learning rate (two seeds),
  the mixed model is +6.1 [+3.8, +8.5] avg@4 on SOLVE test, but the two control seeds differ by 7.2 points.
- **Llama-3.2-3B replication:** own-task gains on every arm (SOLVE +20.1, JUDGE Youden J +43.0, RECONSTRUCT +40.3);
  SOLVE training again transfers positively to the other tasks, but RECONSTRUCT training helps SOLVE (+5.9) here.

**Phase 2: where the checking skill lives.**

- Copying JUDGE's LoRA layers 0–5 into the SOLVE adapter adds +15.3 [+11.5, +19.2] ProcessBench F1, with null
  controls (base weights, wrong-depth layers, RECONSTRUCT layers) and a reverse ablation; it costs −3.9 SOLVE.
- RECONSTRUCT's apparent transfer to checking is response bias (criterion c −0.46, sensitivity at SOLVE level); only
  mixed training adds real sensitivity (d′ 0.73 → 2.32).
- Checkers learned on curated errors are near chance on the model's own long solutions (AUROC 0.50–0.58); a judge
  trained on its own attempts with answer-checker labels reaches 0.665 (+0.097 [+0.066, +0.128], replicated).

**Phase 3: self-verification for answer selection** (pre-registered; 800 questions × 16 attempts).

- Reading the judge's verdict probability instead of sampling verdicts: AUROC +0.067 [+0.047, +0.085].
- Within-question discrimination is at chance on contested questions (0.51 / 0.47 on test).
- Contest-adaptive verification: 81.0%, **+1.59 [+0.51, +2.59]** over majority vote at equal compute.
- The vote ceiling (91.4% present vs 79.8% chosen) resists 12 evidence sources and 4 sampling changes (best +0.85).

## Reports

| Report | Contents |
|---|---|
| [Dataset generation](docs/reports/dataset-generation/dataset_generation_report.pdf) | how FINAL-v3 was built, with emphasis on RECONSTRUCT |
| [Phase 1: GRPO transfer report](docs/reports/2026-10-08-grpo-transfer-report.md) ([PDF](docs/reports/2026-10-08-grpo-transfer-report.pdf)) | recipes, transfer matrix, mixed run, checkpoint selection |
| [Phase 2 report](docs/reports/phase2-full-report.md) and [full Phase 2 log](phase2/docs/phase2-full-report.md) | layer transplants, bias vs skill, error features, self-judge, all negatives |
| [Mixture controls](phase2/mix_control/README.md) · [Llama study](artifacts/baselines/llama3b/README.md) | SOLVE-only controls with two seeds; the Llama-3.2-3B transfer matrix |
| [Phase 3 results](phase3/RESULTS.md), [narrative](phase3/FULL-REPORT.md), [pre-registration](phase3/PREREGISTRATION.md) | self-verification, CAV, evidence grid, sampling |
| [Phase 3 paper draft](paper/main.pdf) | the self-verification paper (ACL format) |
| [Mid-project submission](docs/reports/mid-submission/mid_submission.pdf) | as submitted ([LaTeX source](docs/reports/mid-submission/source/)) |
| [Consolidation note](docs/reports/project-consolidation-2026-10-30.md) · [project history](docs/project-history.md) | provenance of the merged results; the earlier README log |

## Repository map

| Path | What |
|---|---|
| `src/anlp_project/` | library: GRPO trainer (`opd_train.py`, `opd.py`; historical names), rewards (`rewards.py`), SOLVE checker v3 (`solution_verification.py`), strict format gates (`strict_gates.py`), LLM judges (`jev_judging.py`, `qwen_judging.py`, `gemma_judging.py`), evaluation (`baseline.py`) |
| `scripts/` | entry points; `scripts/turing/` launches training and evaluation on the Slurm cluster (`launch.py`, `opd_run.py`, `eval_matrix.py`, `qwen_judge_run.py`) |
| `data/manifests/final-v3/` | the dataset (`*.jsonl.gz`), dev slices and training orders; `data/prompts/` the student prompts |
| `artifacts/baselines/` | per-model test answers and scores (`final-v3/test/`, `llama3b/`), generated matrices |
| `artifacts/opd/evals/` | training metrics and checkpoint-selection records for every GRPO run |
| `phase2/` | Phase 2 experiments: `next/` (transplants, bias, error features), `selfjudge/`, `failure_driven/`, `mix_control/`, `llama_transfer/`, results under `results/` |
| `phase3/` | Phase 3 pipeline (generation, judging, grading, analysis, evidence grid, sampling, sandbox) and its outputs in `runs/` |
| `paper/` | Phase 3 paper source, tables and figures |
| `docs/` | reports, plans, designs, research notes |
| `tests/` | unit tests (245) |

## Setup

Python 3.12 with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
```

Training and evaluation need GPUs (we used 2 × L40S per arm) and vLLM; see `requirements-turing-qwen3.in`. The LLM
judges need either the Jev API (`JEV_KEY`, training rewards) or a local Qwen3.8-27B (test scoring); keys go in an
ignored `.env`.

## Reproduce

```bash
# Check the dataset against DeepMath-103K (parquet files in data/datasets/deepmath-103k/)
.venv/bin/python scripts/audit_final_dataset.py

# One GRPO arm (2 GPUs): SOLVE recipe shown; --task judge|reconstruct|mixed for the others
python3 scripts/turing/launch.py submit --name <run> --gpus 2 --hours 14 -- \
  python scripts/turing/opd_run.py --task solve --config grpo --steps 106 \
    --set prompts_per_step=32 --set optimizer.lr=1e-5 --set optimizer.warmup_steps=5 \
    --set async_rollouts=true --set best_window=8 --set best_keep=3 --out <dir>

# Evaluate an adapter on all three test sets, judge with the 27B, rebuild the matrix
python scripts/turing/eval_matrix.py --name <n> --adapter <adapter> --split test --samples 4 --samples-tasks solve --out <dir>
python scripts/turing/qwen_judge_run.py --eval-dir test:<dir>/s0 --out <log>/answers.jsonl
uv run python scripts/report_grpo_matrix.py

# Offline reproductions of the consolidated results (no GPU)
python phase2/llama_transfer/validate_results.py && python phase2/llama_transfer/report.py
python phase2/mix_control/reproduce.py
```

Phase-specific commands: [Phase 1 runbook](docs/reports/2026-10-07-status-and-runbook.md) §3,
[phase2/README.md](phase2/README.md), [phase3/README.md](phase3/README.md).

## Known gaps

- One training seed per Qwen arm; the single-task arms use different recipes and amounts of data.
- The Phase 2 self-judge adapters and the original own-attempt converter were lost; Phase 3 rebuilt the converter
  and retrained two judges (Stage 2), whose selection evaluation was not run.
- Adapter weights and raw training logs are not in Git; the adapters are on Hugging Face (above).
