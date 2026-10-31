# Ministral Instruct BF16: SOLVE baseline

Protocol fixed on 2026-10-27 before the test run, following the user's request to match the Qwen3.5-2B setup.

| Setting | Value |
|---|---|
| Model | `mistralai/Ministral-3-3B-Instruct-2512-BF16` |
| Revision | `b6d637bef2393152b3da2b2fde72eecdee30557e` |
| Mode | Native Instruct checkpoint, separate from Mistral's Reasoning checkpoint; no Qwen-specific thinking switch |
| Precision | BF16, unquantized, text-only |
| Main evaluation | All 400 FINAL-v3 SOLVE test questions, four samples per question |
| User prompt | Unchanged repository SOLVE v2 prompt, no additional system prompt |
| Sampling | Temperature 1, top-p 1, top-k disabled, seed 0, no presence/repetition penalties |
| Output budget | 16,384 first-pass tokens; capped samples continued from their own tokens to 32,768 total, continuation seed 1 |
| Scoring | Existing checker v3 and strict SOLVE gate |
| Reference | Saved Qwen3.5-2B `v3-pass4-2b` SOLVE results on the same 400 questions |
| Metrics | Mean single-sample strict accuracy, pass@4, paired question-bootstrap differences, gates, truncation, length |
| Infrastructure smoke test | Two dev questions, one sample each, same prompt/sampling/token caps; no prompt tuning |

Only the native chat serialization and model loading differ: vLLM's Mistral tokenizer, config and consolidated
weight loader are used. The Instruct checkpoint does not require a non-thinking toggle. Asking for a worked
solution in the common SOLVE prompt remains part of the task.

`download.py` downloads only the pinned native BF16 files, verifies file sizes and LFS SHA-256 values, and saves
`source.json`. `run.sh` performs the infrastructure smoke check and then the fixed test evaluation, on one
allocated GPU through the existing project environment. No training is performed.

The run is staged on node08 because node06 and node07 had all GPUs allocated. Node08 lacks the home mount,
so its runtime, code and checksum-verified model live in this account's scratch directory. Job 52279 stopped
before generation: vLLM 0.30.0 cannot import Pixtral with Transformers 5.17.0. An isolated Transformers 5.16.0
installation fixes the import, while retaining vLLM 0.30.0 and the other existing packages. The original Qwen
environment is unchanged. Retry job: 52290. The failed loading log is saved at
`local/ministral-baseline/failed-52279-worker.log`.

Job 52290 completed successfully in 44m55s on 2026-10-27. All 1,600 test responses were collected and
validated against the 400 expected question IDs and unchanged rendered prompts. The
[results and paired comparison](../results/ministral-baseline/README.md) show 27.5625% mean strict accuracy
and 53.75% pass@4, versus 52.625% and 80.25% for Qwen3.5-2B. This checkpoint is substantially weaker under
the shared evaluation recipe. Collection also reconciled the GPU ledger; this job consumed 0.75 GPU-hours.

The shared evaluator's new `--model-path`, `--model-format mistral` and `--chat-mode instruct` options support
this run. Its existing defaults retain Qwen's `enable_thinking=False` behavior. The continuation regression
test checks both chat paths, unchanged sampling, and continuation from each sampled token prefix.

Official references:

- [Mistral BF16 model card](https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512-BF16)
- [vLLM Ministral Instruct recipe](https://docs.vllm.ai/projects/recipes/en/latest/Mistral/Ministral-3-Instruct.html)
- [vLLM 0.30 / Transformers 5.17 compatibility issue](https://github.com/vllm-project/vllm/issues/58755)
