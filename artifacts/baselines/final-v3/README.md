# FINAL-v3 zero-training baselines (E0)

Write-up with configuration, results, time and cost: [docs/research/transfer-study/baseline-results.md](../../../docs/research/transfer-study/baseline-results.md).

Untrained student and teacher responses on FINAL-v3, before any OPD training.

| Folder | Questions | Purpose |
|---|---|---|
| `pilot-train-100/` | 100 per task from the **train** split ([fixed IDs](../../../data/manifests/final-v3/pilot-train-100.json)) | Check prompts, token cap, parsing and headroom before touching test |
| `test/` | All 400 per task from the **test** split | The E0 row of the transfer matrix |

**Reported baselines (protocol v2):** `test/qwen3.5-2b-final` (student) and `test/qwen3.8-27b-final` (teacher).

The other folders are earlier protocols and checks, described in RUN_LOG.md:

| Folder | What it is |
|---|---|
| `test/qwen3.5-2b-cap32k`, `test/qwen3.8-27b-cap32k` | Protocol v1 (T 0.7 / top_p 0.8 / top_k 20) at a 32k cap |
| `test/qwen3.5-4b`, `test/qwen3.8-27b` | The first runs: Qwen3.5-4B student, 8,192-token cap, protocol v1 |
| `test/qwen3.5-2b`, `test/*-cap16k`, `pilot-train-100/*` | Student-size and cap checks |

**What is in git.** For the two protocol-v2 folders, `responses.jsonl` and `judgments.jsonl` are stored gzipped (`.jsonl.gz`); run `gunzip -k` on them before re-scoring or re-judging. For the older folders, only the scores, summaries and metadata are in git. Their raw responses and judge calls are kept locally and in the Modal Volumes.

Each `<folder>/<model>/` holds:
- `responses.jsonl`: one row per question, with `uid`, `task`, the exact `prompt` sent, its hash, the raw `text`, `finish_reason` and token counts.
- `metadata.json`: model, sampling, prompt-file hashes, vLLM version, GPU and timings.
- `scores.jsonl` / `summary.json`: deterministic scores only.
  - SOLVE: the answer is checked with verifier v2. If an answer contains several `<final_answer>` tags, the last non-empty one is used (`extraction: last_of_multiple_tags`).
  - JUDGE: the regex-parsed verdict and first wrong step are compared with the key.
  - RECONSTRUCT: whether a question can be extracted. `strict_json_rate` is the share of answers that are valid JSON as returned; `parse_rate` also counts the repo parser's repairs and a lenient extraction of the `question`/`justification` strings from broken JSON (field contents are never rewritten).
- `judgments.jsonl`: every DeepSeek V4.1 Flash judge call, with its raw output. `judged-scores.jsonl` / `judged-summary.json` hold the model-judged scores:
  - JUDGE V/L/E/M, from [`judge_eval_p1.md`](../../../data/prompts/judge/judge_eval_p1.md).
  - RECONSTRUCT P/T/E/M, from the [PC-v4 judges](../../../data/prompts/reconstruct/partial_credit_v4/), with certificate validation.
  - Scores are 6.25 × sum; for RECONSTRUCT a shortcut sets the score to 0, and the 1–5 rating is v4.
  - An unusable RECONSTRUCT response (no extractable question) is a failed attempt. It is reported separately and also counted as 0 in `mean_counting_missing_as_0`.

## Fixed settings

- Models: `Qwen/Qwen3.5-2B` (student; earlier `Qwen/Qwen3.5-4B`) and `Qwen/Qwen3.8-27B` (teacher), all bf16, text-only, served with vLLM on one H100 (Modal).
- Non-thinking chat template (`enable_thinking: False`), one sample per question.
- Sampling, **protocol v2** (reported): temperature 1.0, top_p 1.0, top_k off, no presence or repetition penalty, seed 0, at most 32,768 new tokens. This matches the OPD training rollouts. If an answer hits the cap, it counts as a failure.
- Earlier protocol v1: temperature 0.7, top_p 0.8, top_k 20 (Qwen's general non-thinking defaults), at 32,768 tokens, or 8,192 in the first runs.
- Prompts:
  - SOLVE: [`solve_no_reference.md`](../../../data/prompts/solve/solve_no_reference.md)
  - JUDGE: [`judge_student_p1.md`](../../../data/prompts/judge/judge_student_p1.md), which is the FINAL-v3 `training.input` plus the output format the parser and teacher targets use.
  - RECONSTRUCT: [`final_v1/student.md`](../../../data/prompts/reconstruct/final_v1/student.md), the prompt the PC-v4 judges were used with.

These settings must stay the same for every later checkpoint.

## Reproduce

```bash
modal run scripts/modal_baseline.py::download                       # CPU: cache weights once
modal run --detach scripts/modal_baseline.py::main --model qwen3.5-2b  --split test --protocol v2
modal run --detach scripts/modal_baseline.py::main --model qwen3.8-27b --split test --protocol v2
python3 scripts/judge_baseline.py --model qwen3.5-2b-final --split test   # DeepSeek judging (DeepInfra)
```

Code: [`src/anlp_project/baseline.py`](../../../src/anlp_project/baseline.py) (prompts and scoring) and
[`scripts/modal_baseline.py`](../../../scripts/modal_baseline.py) (Modal/vLLM).
