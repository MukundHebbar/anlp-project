# OPD trial records

These are the reverse-KL on-policy distillation trials on dev slices. Student: Qwen3.5-2B. Teacher: Qwen3.8-27B.
The method, results and analysis are in
[baselines-and-opd-method.md](../../docs/research/transfer-study/baselines-and-opd-method.md#5-opd-trials-dev-slices-september-2026).

## Training runs

| Folder | Task | Steps | Notes |
|---|---|---:|---|
| `probe-solve-20260929T200558Z` | SOLVE | 2 | Memory, timing and LoRA hot-swap probe |
| `trial-solve-20260930T032839Z` | SOLVE | 16 | Dev accuracy 52.0% → 61.5% |
| `trial-judge-20260930T100917Z` | JUDGE | 12 | Cancelled by the client after step 12 |
| `trial-judge-20260930T100917Z-resume12` | JUDGE | 13–14 | Resumed from the step-12 adapter, fresh optimiser state |
| `trial-reconstruct-20260930T100915Z` | RECONSTRUCT | 5 | Automatic stop: truncation 0% → 50% (repetition loops) |
| `fix-reconstruct-drop-20260930T135756Z` | RECONSTRUCT | 5 | Fix A: drop truncated rollouts. Stopped by the repetition rule |
| `fix-reconstruct-kl0.1-20260930T135809Z` | RECONSTRUCT | 5 | Fix B: KL anchor β 0.1. Stopped by the truncation rule |

Each folder holds:
- `config.json`: the exact configuration.
- `metrics.jsonl`: one row per step, with loss, reverse KL, vLLM/trainer log-prob gap, mean and maximum length, truncation rate, repetition, rollouts used, anchor KL and time per phase.
- `events.log`: the run's event log.
- The vLLM server logs.

The LoRA adapters are not in git. They are in the Modal Volumes, under `opd/<run>/adapters/step<N>`: `anlp-opd-cache` in the ARYAMA workspace, and `anlp-final-v3-hf-cache` in SANGHA for the KL-anchor trial.

## Dev evaluations (`evals/`)

Protocol v2: T 1.0, top_p 1.0, top_k off, 32k cap, one sample. Each task has 200 dev questions.

| Folder | Model |
|---|---|
| `dev-solve-base-T1.0` | Untrained student, SOLVE |
| `dev-solve-trial-step16-T1.0` | SOLVE step-16 adapter |
| `dev-judge+reconstruct-base` | Untrained student, JUDGE and RECONSTRUCT |
| `dev-judge-trial-step14` | JUDGE step-14 adapter |
| `dev-reconstruct-trial-step5` | RECONSTRUCT step-5 adapter |
| `dev-solve-base`, `dev-solve-trial-step16` | The same SOLVE pair under the superseded protocol v1 (T 0.7, top_p 0.8, top_k 20) |

`responses.jsonl` and `judgments.jsonl` are stored gzipped. Run `gunzip -k` on them before re-scoring or re-judging with `scripts/judge_baseline.py --split dev`.
