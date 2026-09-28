# JUDGE evaluation: Qwen3-4B on the 78-item high-confidence set

Qwen3-4B judged 78 proposed solutions (30 correct, 48 incorrect). DeepSeek V4.1 Flash then
rated each response against the private answer key. Evaluation only: no questions were
created and no model was trained.

- Input: `judge_data/judge-high-confidence-public.jsonl`; key: `judge_data/judge-high-confidence-private-key.jsonl`
- Script: `scripts/evaluate_judge_qwen.py` (`generate` → `rate` → `collect`)
- Rating prompt: `data/prompts/judge/judge_eval_p1.md`
- Student: `Qwen/Qwen3-4B` (local llama.cpp Q4_K_M, non-thinking), each item's `qwen_prompt`
  sent verbatim; temperature 0.7, top_p 0.8, top_k 20, 8,192 tokens, seed 0 (the RECONSTRUCT
  student settings). One draw per item.
- Rater: `deepseek-ai/DeepSeek-V4.1-Flash`, temperature 0, reasoning effort low. Cost $0.03.

## Scoring (same construction as RECONSTRUCT)

DeepSeek scores four dimensions, each 0–4:

| Dimension | Question |
|---|---|
| V verdict | Does the decision match the key? (0 or 4; a self-contradictory decision scores 0) |
| L localization | Is the first wrong step identified? (4 exact, 2 a later step caused by the same error, 0 otherwise; for correct solutions, 4 for "none") |
| E error explanation | Does it name the key's actual error (or, for correct solutions, give a valid reason)? |
| M soundness | Are the explanation's own mathematical claims true? |

A wrong verdict forces L = 0 and E = 0. Score = 6.25 × (V + L + E + M) on 0–100, binned to
1–5 with RECONSTRUCT rating v4 (cutoffs 18.75, 43.75, 56.25, 75).

## Results

| Metric | Value |
|---|---:|
| Mean score | 57.4 / 100 (median 75) |
| Rating histogram (1–5) | 27, 7, 0, 3, 41 |
| Verdict accuracy (parsed from Qwen's text) | 67.9% (53/78) |
| Verdict accuracy (DeepSeek V = 4) | 65.4% (51/78) |
| First wrong step exact, on incorrect solutions | 47.9% (23/48) |
| Dimension means (0–4) | V 2.62, L 2.18, E 1.92, M 2.46 |

| Subset | n | Verdict accuracy | Mean score |
|---|---:|---:|---:|
| Correct solutions | 30 | 63.3% | 63.5 |
| Incorrect solutions | 48 | 70.8% | 53.5 |
| Error early | 14 | 57.1% | 42.9 |
| Error middle | 18 | 66.7% | 56.3 |
| Error late | 16 | 87.5% | 59.8 |

Qwen flags 11 of the 30 correct solutions as wrong, and catches errors less often the earlier
they occur.

## Reading the numbers

- **The 1–5 distribution is bimodal by construction, not a sign of a broken rater.** V is binary
  and a wrong verdict zeroes L and E, so a wrong verdict lands at 1–2 and a right verdict with
  the right step lands at 5. Only three responses fall in between, where the verdict and step
  were right but the explanation was flawed. The v4 cutoffs were calibrated on RECONSTRUCT
  scores, and were not re-tuned here.
- **Report verdict accuracy and first-step accuracy alongside the rating.** They are
  parsed directly from Qwen's text and do not depend on DeepSeek.
- **DeepSeek and the parser disagree on 2 of 78 verdicts.** In both, Qwen wrote
  `Decision: incorrect` but its explanation then argued the solution is correct. DeepSeek scored
  V = 0 as self-contradictory, per the rubric.
- **78 items is small.** A proportion around 68% has a 95% interval of about ±10 points, so
  subset rows (n = 14–18) are descriptive only.

## Files

- `results.jsonl` / `results.csv`: one row per item: problem, proposed solution, key, Qwen's
  response, parsed decision and step, DeepSeek's four scores and reasons, score, 1–5 rating
- `summary.json`: all aggregate numbers above
- `qwen-responses.jsonl`, `deepseek-ratings.jsonl`: raw model outputs including usage
