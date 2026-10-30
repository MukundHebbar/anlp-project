# Llama 3.2 3B cross-task GRPO — completed

All three seed-0 arms completed. [Full transfer matrix](../../artifacts/baselines/llama3b/grpo-matrix.md),
[collected evidence](../../artifacts/baselines/llama3b/README.md), and
[offline validation](../../artifacts/baselines/llama3b/validation.json).

| Arm | Updates | LR | Questions × rollouts/update | Dev-selected step | Test SOLVE avg@4 |
|---|---:|---:|---:|---:|---:|
| Untrained baseline | — | — | — | — | 9.00% |
| SOLVE | 106 | 2e-5 | 32 × 8 | 106 | 29.125% |
| JUDGE | 104 | 5e-5 | 8 × 8 | 78 | 8.4375% |
| RECONSTRUCT | 104 | 5e-5 | 8 × 8 | 104 | 14.875% |

SOLVE LR probes used eight updates followed by the same 200 dev questions × four samples: 1e-5 scored
8.875%, 2e-5 scored 10.75%. The latter was continued with optimizer state from step 8 to 106. JUDGE and
RECONSTRUCT selected among steps 26/52/78/104 using their own-task dev metric; JUDGE step 104 is also
reported as a fixed endpoint. No test result was used for checkpoint or LR selection.

## Models and protocol

Student: `meta-llama/Llama-3.2-3B-Instruct`, revision
`0cb88a4f764b7a12671c53f0838cd831a0843b95`, BF16, native instruct chat. This checkpoint has no separate
thinking-mode switch. LoRA rank/alpha 64, dropout zero, q/k/v/o/gate/up/down projections. All runs use
Dr. GRPO, group-mean advantages without standard-deviation scaling, 16,384-token normalization, IS cap 2,
KL coefficient zero, AdamW (0.9,0.999), weight decay zero, grad clip 1, T=1/top_p=1, and a 16,384 output cap.
SOLVE uses five warm-up updates and asynchronous rollouts. JUDGE/RECONSTRUCT use synchronous rollouts;
RECONSTRUCT drops truncated samples. Training and the 200-item development slices are disjoint.

Training rewards use Gemma 4 12B, revision `707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7`, with the explicit-label
calibration in `phase2/results/local-judge-calibration/gemma-full-explicit/`. Final evaluation uses the same
Qwen3.8-27B judge and existing Qwen calibration as the Qwen study. No OPD training was added: the `opd_train`
filename is the historical shared loop, invoked with `method=grpo` and no distillation teacher.

Two differences from the Qwen study must be reported: SOLVE selected 2e-5 rather than 1e-5, and Gemma replaced
Jev for training/dev rubric scoring. Gemma's full held-out RECONSTRUCT correlation was 0.778 calibrated and
0.763 for the continuous reward, with 3/9 shortcuts caught and one false positive. Its historical calibration
uses test-derived examples held out by checkpoint, not untouched questions. The Llama baseline is also much
weaker on this dataset (9.0% vs Qwen's 52.625%), so this is not a matched-starting-performance comparison.

## Entry points and reproducibility

- `arm.py`: full training, dev selection, and cross-task test generation for one arm.
- `run.py`: one explicit GRPO training run; `probes.py`: LR probes with bounded completed-process teardown.
- `stage.sh` and `submit.py`: isolated Turing staging and project-ledger submission; validate runtime/code
  freshness before any future allocation. `background.py` belongs to the earlier preparation workflow,
  not the finished-results collection.
- `judge27b.sh`: final local Qwen judging. `report.py`: offline transfer matrix with paired bootstrap intervals.
- `validate_results.py`: offline counts, completion, strict metrics, dev selection and split separation.

From the repository root, after installing the regular project dependencies:

```bash
python phase2/llama_transfer/validate_results.py
python phase2/llama_transfer/report.py
```

Both work directly with committed `.jsonl.gz` evidence and make no model/API calls. The collected report
regenerates byte-for-byte. `provenance.json` describes the reviewed publication integration; immutable
per-run provenance and separately labelled collected staged source remain in the training artifacts.

The original October 28 handoff records failures before recovery and is historical. It does not describe
these completed runs. Raw training rollouts and operational logs are archived locally; weights and optimizer
states remain outside Git. No new training or paid judging was performed while collecting these results.
