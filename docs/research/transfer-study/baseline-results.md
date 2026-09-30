# Zero-training baselines: results, configuration, time and cost

Recorded 2026-09-30. These are the **E0** (untrained) numbers for the transfer study: the
student and the teacher answer every FINAL-v3 test question once, with no training, under
the **final evaluation protocol (v2)**. Every trained checkpoint is evaluated the same way.
Everything below is taken from the stored run files. The full generated tables are in
[REPORT.md](../../../artifacts/baselines/final-v3/REPORT.md), the per-run history in
[RUN_LOG.md](../../../artifacts/baselines/final-v3/RUN_LOG.md), and the training plan in
[baselines-and-opd-method.md](baselines-and-opd-method.md).

## 1. Summary (protocol v2; test set, 400 questions per task)

| Metric | Student Qwen3.5-2B | Teacher Qwen3.8-27B |
|---|---:|---:|
| SOLVE accuracy | 55.8% | 79.5% |
| JUDGE verdict accuracy | 57.5% | 73.5% |
| JUDGE first wrong step (incorrect solutions) | 18.0% | 55.5% |
| JUDGE V/L/E/M score /100 | 47.0 | 78.1 |
| RECONSTRUCT PC-v4 score /100 (scored items) | 36.0 | 70.1 |
| RECONSTRUCT same original question | 5.0% | 28.2% |

The teacher is far ahead on every task. On SOLVE questions checkable for both models,
accuracy is 69.1% vs 94.7%.

**Time:** 1 h 34 min wall-clock (34 min generation, 60 min judging, run in parallel).

**Cost:** $3.47 Modal (teacher $2.71, student $0.76) and $2.99 DeepSeek judging.

## 2. Configuration (protocol v2, frozen)

### Data

- [FINAL-v3](../../../data/manifests/final-v3/README.md) test split: 400 questions per task, 1,200 in total. JUDGE test has 200 correct and 200 incorrect proposed solutions.
- The tasks use different DeepMath-103K questions, matched on topic buckets and difficulty (5.0–8.0).

### Models and serving

| | Student | Teacher |
|---|---|---|
| Model | `Qwen/Qwen3.5-2B` (snapshot `15852e8`) | `Qwen/Qwen3.8-27B` (snapshot `1d4bf0f`) |
| Mode | bf16, text-only (`language_model_only`), non-thinking chat template (`enable_thinking: False`) | same |
| Engine | vLLM 0.30.0 + transformers 5.17.0 (pinned), offline `LLM.chat`, one H100 80 GB on Modal, `gpu_memory_utilization` 0.90, `max_num_seqs` 256, `max_model_len` 40,960, prefix caching | same |

- The student and teacher share a tokenizer. This was checked on the Qwen3.5 tokenizer: 248,070 shared token IDs identical, 41/41 texts encoded identically, and the rendered prompt identical token for token.
- The teacher ran in the SANGHA Modal workspace and the student in the ARYAMA workspace. Both used the same pinned image and the same weight snapshots.

### Sampling (identical for every model and checkpoint)

| Setting | Value |
|---|---|
| Temperature | **1.0** |
| top_p | **1.0** (off) |
| top_k | **0** (off) |
| min_p / presence penalty / repetition penalty | 0 / 0 / 1.0 (all off) |
| Max new tokens | **32,768**; an answer that hits the cap counts as a failure |
| Samples | **1 per question**, seed 0 |

**Why these settings:**
- **They match the OPD training rollouts exactly,** so evaluation samples from the same distribution the student is trained on.
- **They follow the train-matched evaluation used by** Thinking Machines/Tinker (T 1.0, top_p 1.0, top_k −1), AsyncOPD, Prefix OPD and Entropy-aware OPD.
- **None of the OPD maths papers checked uses the model card's settings.** Essentially none uses a presence penalty for maths evaluation.
- **Protocol v1 was dropped for a measured reason.** It used Qwen's general non-thinking defaults (T 0.7, top_p 0.8, top_k 20). Under it, the OPD-trained student looped on 89 of 200 dev questions, a decoding artefact of the sharper trained distribution (section 4).

### Prompts

| Task | Prompt file | Notes |
|---|---|---|
| SOLVE | `data/prompts/solve/solve_no_reference.md` | Asks for one `<final_answer>` tag |
| JUDGE | `data/prompts/judge/judge_student_p1.md` | The FINAL-v3 `training.input` plus the `Decision:` / `First wrong step:` / `Explanation:` format lines |
| RECONSTRUCT | `data/prompts/reconstruct/final_v1/student.md` | Byte-identical to the prompt in the earlier DeepSeek-scored RECONSTRUCT runs |

### Scoring

- **SOLVE:**
  - The deterministic verifier (v2) compares the answer with the DeepMath answer.
  - The answer is the `<final_answer>` tag; if there are several, the last non-empty one is used.
  - Statuses are `correct`, `incorrect`, `unverified` (no safe equivalence rule) and `missing`. Only `correct` counts.
- **JUDGE:**
  - Deterministic: the verdict and first wrong step are parsed from the answer and compared with the key.
  - Model-judged: DeepSeek scores V, L, E and M (each 0–4) against the answer key using `data/prompts/judge/judge_eval_p1.md`.
  - Score = 6.25 × sum; a wrong verdict forces L = E = 0.
- **RECONSTRUCT:**
  - DeepSeek PC-v4 judges (`data/prompts/reconstruct/partial_credit_v4/`). The fidelity judge sees the original question and scores P and T; the source-blind validity judge scores E and M.
  - Certificate validation: `reconstruct_judge_validation.py`.
  - Score = 6.25 × sum; a shortcut scores 0.
  - Broken JSON is used if the `question`/`justification` strings can be extracted without rewriting them.
  - An answer with no extractable question is *unusable* and counts as 0. A judgment that fails validation is *unresolved* and is excluded.
- **Judge model:** `deepseek-ai/DeepSeek-V4.1-Flash` via DeepInfra, temperature 0, reasoning effort low, at most 8,192 output tokens.
  - Each call gets at most **two attempts**. The second is made only after a transport failure; rate limits and dropped connections are waited out within an attempt.
  - Judgments that fail validation are not retried.
- **Also reported:** accuracy within 8k and 16k tokens (from the same run), the cap-hit rate, and mean length.
- **Intervals:** 95% bootstrap over questions (2,000 resamples). They cover question sampling only; there is one sample per question.

## 3. Results (protocol v2)

### Headline (failures count as wrong; 95% intervals)

| Metric | Student Qwen3.5-2B | Teacher Qwen3.8-27B |
|---|---:|---:|
| SOLVE accuracy | 55.8% [51.0, 60.8] | 79.5% [75.5, 83.2] |
| JUDGE verdict accuracy | 57.5% [52.8, 62.3] | 73.5% [69.0, 77.5] |
| … on correct solutions (n = 200) | 57.0% [50.5, 64.0] | 70.0% [63.5, 76.5] |
| … on incorrect solutions (n = 200) | 58.0% [51.0, 65.0] | 77.0% [71.5, 83.0] |
| JUDGE first wrong step (n = 200 incorrect) | 18.0% [13.0, 23.5] | 55.5% [49.0, 62.5] |
| JUDGE V/L/E/M score /100 | 47.0 [43.2, 50.8] (n = 394) | 78.1 [74.6, 81.6] (n = 396) |
| RECONSTRUCT PC-v4 /100, scored items | 36.0 [33.6, 38.3] (n = 312) | 70.1 [67.9, 72.4] (n = 333) |
| RECONSTRUCT PC-v4 /100, unusable = 0 | 33.5 [31.1, 35.9] (n = 335) | 69.1 [66.7, 71.5] (n = 338) |
| RECONSTRUCT same original question | 5.0% [3.0, 7.2] | 28.2% [24.2, 32.8] |
| RECONSTRUCT grounded recovery (provisional) | 0.8% [0.0, 1.8] | 15.5% [12.2, 19.0] |

### Budget-limited (same run; counts only answers that finished within the budget)

| Metric | Student | Teacher |
|---|---:|---:|
| SOLVE accuracy within 8k / 16k | 34.5% / 54.8% | 76.0% / 79.5% |
| JUDGE verdict accuracy within 8k / 16k | 51.5% / 57.0% | 73.5% / 73.5% |
| RECONSTRUCT PC-v4 /100 within 8k / 16k (unusable = 0) | 29.6 / 33.4 | 68.9 / 69.1 |

### Questions checkable for both models

| Task | Questions | Metric | Student | Teacher |
|---|---:|---|---:|---:|
| SOLVE | 301 | Accuracy | 69.1% | 94.7% |
| JUDGE | 400 | Verdict accuracy | 57.5% | 73.5% |
| JUDGE | 200 incorrect | First wrong step | 18.0% | 55.5% |
| JUDGE | 390 | V/L/E/M score /100 | 47.1 | 78.0 |
| RECONSTRUCT | 264 | PC-v4 score /100 | 36.3 | 70.4 |
| RECONSTRUCT | 264 | Same original question | 5.3% | 29.5% |

"Checkable" means:
- SOLVE: the verifier decided `correct` or `incorrect`.
- JUDGE: parsed and not cut off.
- RECONSTRUCT: usable, with both judgments resolved.

### Missing and malformed responses

| | Student | Teacher |
|---|---:|---:|
| SOLVE correct / incorrect / unverified / missing | 223 / 97 / 69 / 11 | 318 / 19 / 60 / 3 |
| Hit the 32k cap: SOLVE / JUDGE / RECONSTRUCT | 0 / 0 / 1 | 0 / 0 / 0 |
| Mean answer tokens: SOLVE / JUDGE / RECONSTRUCT | 8,309 / 2,900 / 2,995 | 3,552 / 1,082 / 1,575 |
| RECONSTRUCT valid JSON as returned | 76 / 400 | 350 / 400 |
| RECONSTRUCT usable / unusable | 377 / 23 | 395 / 5 |
| RECONSTRUCT scored / unresolved judgment | 312 / 65 | 333 / 62 |
| RECONSTRUCT shortcuts (score 0) | 35 | 5 |
| JUDGE items without a judge score | 6 | 4 |

### Rubric dimensions (means, 0–4, scored items)

| | Student | Teacher |
|---|---:|---:|
| JUDGE V / L / E / M | 2.38 / 1.78 / 1.49 / 1.88 | 3.20 / 3.05 / 3.02 / 3.23 |
| RECONSTRUCT P / T / E / M | 1.79 / 2.04 / 1.74 / 0.67 | 2.76 / 3.10 / 2.97 / 2.50 |

### By topic and difficulty (all questions)

| Group | SOLVE, student | SOLVE, teacher | JUDGE verdict, student | JUDGE verdict, teacher |
|---|---:|---:|---:|---:|
| Algebra | 51.5% | 77.8% | 59.8% | 73.2% |
| Calculus | 71.3% | 85.1% | 62.6% | 73.7% |
| Discrete Mathematics | 44.7% | 75.5% | 57.1% | 75.8% |
| Number Theory | 54.7% | 79.2% | 51.3% | 71.7% |
| Difficulty 5.0–6.5 | 56.5% | 80.2% | 59.3% | 75.4% |
| Difficulty 7.0–8.0 | 54.1% | 77.9% | 53.3% | 69.2% |

### Findings

1. **A large gap on every task, driven by correctness:**
   - SOLVE: 97 wrong answers vs 19.
   - JUDGE first-wrong-step accuracy: 18.0% vs 55.5%.
   - RECONSTRUCT: 36.0 vs 70.1 on scored items.
2. **The student no longer runs away at temperature 1.0.** It hit the 32k cap on 1 of 1,200 answers (under protocol v1: 156). It is still verbose, writing 2–3× longer answers than the teacher.
3. **The student's JUDGE verdicts are close to chance.** It finds the first wrong step rarely (18%), so JUDGE has little room below the baseline to show negative transfer.
4. **RECONSTRUCT is the student's weakest task.** It has low mathematical validity (M = 0.67 vs 2.50) and many shortcut answers (35 vs 5).

### Caveats

- One sample per question and one run per model. Most OPD papers average over several samples per question, so these numbers are noisier.
- RECONSTRUCT judges leave some items unresolved (65 for the student, 62 for the teacher).
- 15–17% of SOLVE answers are `unverified`, which counts as wrong.
- DeepSeek scores have not been validated against human grades on this data.
- Grounded recoveries are provisional until reviewed by hand.
- The student model, the cap and the evaluation temperature were chosen partly using test data (200 SOLVE test questions) and a dev-slice OPD trial (section 4).

## 4. Earlier protocol and checks (how protocol v2 was chosen)

**Protocol v1** (T 0.7, top_p 0.8, top_k 20; Qwen's general non-thinking defaults), full test set, 32k cap:

| | Student 2B | Teacher 27B |
|---|---:|---:|
| SOLVE accuracy | 49.5% | 83.8% |
| JUDGE verdict accuracy | 61.5% | 76.8% |
| RECONSTRUCT PC-v4 /100, scored items | 46.5 | 72.5 |
| Hit the 32k cap: SOLVE / JUDGE / RECONSTRUCT | 37 / 16 / 103 | 0 / 0 / 4 |

Under v1 the student scored higher on JUDGE and RECONSTRUCT but lower on SOLVE, and it often generated without stopping. The two protocols give different baselines, so **only v2 numbers may be compared with v2 checkpoints.**

**The OPD trial that exposed the problem.** The trial ran 16 steps on 512 SOLVE train prompts. It was evaluated on 200 dev SOLVE questions, a separate part of the train split:

| Dev SOLVE | Untrained | After OPD |
|---|---:|---:|
| Protocol v1 (T 0.7) | 57.0% (cap hits 19) | 43.0% (cap hits 89, repetition loops) |
| Train-matched (T 1.0, top_p 1.0, no top-k) | 52.0% (cap hits 1) | **61.5%** (cap hits 1) |

At matched temperature, OPD gained **+9.5 points** (95% interval +2.5 to +16.0, McNemar p = 0.009).

**Even earlier runs:**
- **Qwen3.5-4B at 8k (full test):** SOLVE 73.0% vs 80.8%. With the cap no longer binding it reached 79.0% on 200 questions, leaving too little room, which led to the switch to the 2B.
- **The 2B at 8k/16k/32k** on 200 SOLVE test questions was also run and recorded in REPORT.md and RUN_LOG.md.

## 5. Time and cost

- **Modal costs** are from Modal's itemised billing, matched to each run's app ID. They include H100, CPU and memory.
- **DeepSeek costs** are the provider's per-call estimates recorded with each judgment.
- **Judging wall-clock** is from the first to the last recorded judgment.

### Protocol v2 baseline (the reported E0)

| Part | Workspace | Wall-clock | Load / generate | Modal | DeepSeek |
|---|---|---:|---|---:|---:|
| Student generation, 1,200 answers | ARYAMA | 9.6 min | 148 s / 380 s | $0.76 | – |
| Teacher generation, 1,200 answers (in parallel) | SANGHA | 33.6 min | 230 s / 1,750 s | $2.71 | – |
| Student judging, 1,154 calls | DeepInfra | 57.5 min | – | – | $1.57 |
| Teacher judging, 1,190 calls | DeepInfra | 60.3 min | – | – | $1.42 |
| **Total** | | **1 h 34 min** (07:20–08:55 UTC) | | **$3.47** | **$2.99** |

- The student's judging started as soon as its generation finished, 24 minutes before the teacher's.
- Modal breakdown: H100 $2.83, CPU $0.27, memory $0.37.
- Judge outcomes:
  - Student: 1,083 valid, 61 validation failures, 10 transport failures after two attempts.
  - Teacher: 1,124 valid, 52 validation failures, 14 transport failures after two attempts.

### Everything before protocol v2

| Part | Modal | DeepSeek |
|---|---:|---:|
| Protocol v1 at 32k: 2B and 27B on the full test set | $4.45 | $2.70 |
| Earlier 4B / 8k protocol, pilots, cap and student-size checks | $6.97 | $3.68 |
| Setup and failed attempts (SANGHA) | $2.11 | – |
| OPD probe, SOLVE trial and its 3 dev evaluations (ARYAMA) | ≈ $11.1 | – |
| Later OPD trials: JUDGE, RECONSTRUCT and the two RECONSTRUCT fix trials | see [method doc, section 5.6](baselines-and-opd-method.md#56-time-and-cost) | |

The v1 and earlier runs are itemised in [RUN_LOG.md](../../../artifacts/baselines/final-v3/RUN_LOG.md).

### Per-checkpoint estimate for later evaluations

Evaluating a trained student on the full test set is one student run plus its judging:
about 10 minutes and $0.80 of Modal, plus about 60 minutes and $1.60 of DeepSeek.

## 6. Reproduce

```bash
modal run scripts/modal_baseline.py::download                                  # CPU: cache weights
modal run --detach scripts/modal_baseline.py::main --model qwen3.5-2b  --split test --protocol v2
modal run --detach scripts/modal_baseline.py::main --model qwen3.8-27b --split test --protocol v2
python3 scripts/judge_baseline.py --model qwen3.5-2b-final  --split test --workers 12  # then again at --workers 6
python3 scripts/judge_baseline.py --model qwen3.8-27b-final --split test --workers 12  # for transport retries
python3 scripts/report_baseline.py
```

- Outputs are in `artifacts/baselines/final-v3/test/{qwen3.5-2b-final,qwen3.8-27b-final}/`: responses with their exact prompts, metadata, deterministic scores, every judge call, and judged scores. Each run also has a copy in its Modal Volume.
- **Scoring can be re-run from the stored responses at any time without regenerating.**
- To use a workspace's own weight cache, set `BASELINE_VOLUME=<volume>`.
