# Final plan: cross-task transfer with GRPO and on-policy distillation (Qwen3.5-2B)

Date: 2026-10-06. This file is the single current plan. It replaces the earlier revisions:
`2026-10-06-grpo-opd-transfer.md` (decisions and evidence) and `2026-10-06-jev-eval-judge.md` (judge work).

## 1. Goal

Train Qwen3.5-2B on one task at a time (SOLVE, JUDGE or RECONSTRUCT), by **GRPO** or by **on-policy
distillation (OPD)** from Qwen3.5-9B. Measure each trained model on all three tasks.

- **Main result:** two 3×3 transfer matrices, one per method. Each cell is
  Δ(i→j) = score_j(trained on i) − score_j(starting model), on the FINAL-v3 test sets.
- **Secondary results:**
  - GRPO − OPD per cell;
  - the warm-up's own contribution;
  - which sub-skills move (JUDGE V/L/E/M; RECONSTRUCT P/T/E/M);
  - cost per arm.

## 2. Fixed decisions

| Item | Decision |
|---|---|
| Data | FINAL-v3. Per task, different DeepMath questions matched on topic and difficulty. 3,600 train / 400 test; the 200-question dev slice is held out of training. Datasets stay as they are |
| Student | `Qwen/Qwen3.5-2B` post-trained, non-thinking chat template |
| OPD teacher | `Qwen/Qwen3.5-9B`, also the reference upper model. Tokenizer identical to the 2B (checked) |
| Student prompts | v2 (`baseline.PROMPT_FILES`): JUDGE ends with one final block written once; RECONSTRUCT reasons, then gives one final JSON whose question field holds only the question; both carry a brevity line and state the strict-gate rules. v1 is kept only to reproduce old runs |
| Strict gates | `strict_gates.py`, applied before any score or reward; a failed gate scores 0. JUDGE: several or contradictory decisions or steps. SOLVE: disagreeing final answers. RECONSTRUCT: answer in the question, monologue or drafting, no question. RECONSTRUCT is parsed from its **last** JSON object |
| Training reward and dev judge | **Jev API** (`jev_judging.py`, calibrated, staged shortcut check). Used **only where required** (§6) |
| Final test judge | `Qwen/Qwen3.8-27B`, logit-reading (`qwen_judging.py`), calibrated against DeepSeek. Used for nothing else |
| Evaluation sampling | **4 samples per question** (pass@4). T 1.0, top-p 1.0, 16k first pass continued to 32k |
| Compute | At most **6 GPUs at once** on Turing. Internal ledger raised to 500 GPU-h. No Turing run without the user's go-ahead |
| Seeds | 1 for now. Extra seeds later for the central comparisons only |

## 3. Training configuration

**Shared:**
- LoRA r 64, α 64, dropout 0, attention + MLP projections.
- AdamW, lr 5e-5 constant, grad clip 1.0.
- 64 trajectories per update, 1 update per step, T 1.0.
- **16k rollout cap** (a third of v2 answers exceed 8k, and they are real reasoning, not loops).
- **52 steps for every arm, final checkpoint fixed at 52.** Adapters kept at 26 and 52.
- Prompts in seeded order from the train split, minus the dev slice.

**Starting point, the same for both methods:**

| Task | Starting point | Reason |
|---|---|---|
| SOLVE | the plain 2B | warm-up lowered SOLVE before (57.5 → 49.0 dev) |
| JUDGE | 2B + short SFT warm-up | the matrix recipe |
| RECONSTRUCT | 2B + short SFT warm-up | without it, OPD collapsed into loops within 3–5 steps |

- **Warm-up:** 256 examples, 1 epoch, batch 16, lr 1e-4 cosine to 1e-5.
- **Warm-up data:** 9B answers to the warm-up questions, 2 samples each.
  - Kept only if they pass the gates and are correct: verdict and step for JUDGE, Jev ≥ 70 for RECONSTRUCT.
  - Best answer per question.

**OPD** (`--config opd9b`):

| Setting | Value |
|---|---|
| Teacher | 9B on 1 GPU, shared by the 3 students |
| Loss | per-token reverse KL, sampled token |
| Prompts per step | 64 × 1 |
| Regularisers | KL anchor β 0.5, overlong penalty 1.0, anti-repetition instruction for the teacher. This is the only loop-free recipe in our trials |

**GRPO** (`--config grpo`):

| Setting | Value |
|---|---|
| Group | 8 prompts × 8 samples |
| Advantage | reward − group mean, no std scaling |
| KL anchor | β 0 |
| Truncated rollouts | filtered out of the loss and the group mean |
| Equal-reward groups | skipped |
| Clipping | no PPO clipping: exactly one update per batch, so the policy ratio is 1 |
| SOLVE reward | exact answer → 1/0 |
| JUDGE reward | 0 for a wrong verdict; else 0.5 + 0.25·[right step] + 0.25·Jev (E+M)/8 |
| RECONSTRUCT reward | Jev staged score / 100, −0.1 for several drafts |

Gated, shortcut and truncated answers get 0. GRPO is compute-matched to OPD (64 trajectories per step), not
data-matched: 416 vs 3,328 distinct prompts over 52 steps.

## 4. Phases

### Phase 1: baselines (running now)
| Step | What | GPUs | Status |
|---|---|---|---|
| 1a | 2B: 3 test sets × 4 samples, then 3 dev slices × 4 samples | 3 | running (job 42313) |
| 1b | 9B: 3 test sets × 4 samples | 3 | running (job 42314) |
| 1c | Deterministic scores with strict gates: SOLVE accuracy, JUDGE verdict and step; pass@1 and pass@4 | 0 | automatic at merge |
| 1d | Calibrate the 27B judge: saved 500-answer samples against DeepSeek, fit on 4 checkpoints, test on 4, plus a 30-answer manual spot check | 2 | after 1a/1b |
| 1e | 27B judges the baseline test answers (JUDGE V/L/E/M, RECONSTRUCT P/T/E/M) | 2 | after 1d |
| 1f | Jev on the 2B dev RECONSTRUCT, sample 1 only (the monitoring reference) | 0 | ~$0.20 |
| 1g | **Baseline report** (`scripts/report_passk.py`): pass@1, pass@4, 16k-budget score, gate rates, length, 9B − 2B headroom per task | 0 | — |

**Gate:** if the 9B is not clearly better than the 2B on a task, OPD on that task is reported as a negative control.

### Phase 2: warm-up and checks (after the baseline report)
| Step | What | GPUs |
|---|---|---|
| 2a | 9B warm-up answers, JUDGE and RECONSTRUCT (512 questions × 2) | 2 |
| 2b | Filter: gates and correctness; Jev ≥ 70 for RECONSTRUCT | 0 |
| 2c | SFT warm-ups for JUDGE and RECONSTRUCT | 2 |
| 2d | 2-step checks of one GRPO and one OPD run: loss finite, rewards computed, Jev reachable from the node, adapter sync | 2 |
| 2e | Unit tests for the GRPO path (group advantages, reward ranges, gates, Jev failures, truncation filter) | 0 |

### Phase 3: main runs (52 steps, 6 GPUs maximum)
| Wave | Runs | GPUs |
|---|---|---|
| 1 | OPD-SOLVE, OPD-JUDGE, OPD-RECONSTRUCT + shared 9B teacher; GRPO-SOLVE, GRPO-JUDGE | 4 + 2 = 6 |
| 2 | GRPO-RECONSTRUCT, on the first GPU wave 1 frees | 1 |

**Monitoring at steps 26 and 52** (free metrics, plus Jev on RECONSTRUCT):
- reward or teacher gap, truncation, gate rate, repetition;
- a reward-hacking audit: read high-reward RECONSTRUCT rollouts.

**Stop if** truncation exceeds 15%, the gate rate keeps rising, or repetition exceeds 0.5. A stop is reported as such.

### Phase 4: evaluation and analysis
| Step | What | GPUs |
|---|---|---|
| 4a | 6 trained + 2 warm-up-only checkpoints × 3 test sets × 4 samples | 6 |
| 4b | 27B judges them; deterministic scores with gates | 2 |
| 4c | Report: two transfer matrices with paired bootstrap Δ against the starting model; GRPO − OPD per cell; warm-up rows; 16k-budget score; gate and format rates; length; GPU-h and API cost | 0 |
| 4d | Write-up: asymmetries, sub-skill decomposition, method comparison, limitations (1 seed, 52 steps, one student family, a training reward judge different from the final judge by design) | 0 |

### Housekeeping (no GPU)
- Freeze the protocol in `docs/research/transfer-study/protocol-v3.md`: prompt hashes, caps, judge versions,
  calibration files.
- Commit all code and plans; nothing from 2026-10-06 is committed yet.

## 5. Time and compute

| Phase | Wall time | GPU-h |
|---|---|---:|
| 1 baselines (pass@4) + 27B calibration and judging | ~6–8 h | ~35 |
| 2 warm-up, SFT, checks | ~3 h | ~5 |
| 3 main runs (two waves) | ~20–24 h | ~70 |
| 4 evaluation (pass@4) + judging + report | ~8–10 h | ~45 |
| **Total** | **~2–2.5 days** | **~155** (ledger: 368 GPU-h left) |

## 6. Jev credits: only where required

| Use | Cost |
|---|---:|
| GRPO reward: RECONSTRUCT, and JUDGE's E+M term when the verdict is right | ~$4 |
| RECONSTRUCT warm-up filter | ~$0.30 |
| Dev RECONSTRUCT at steps 26 and 52, 1 sample, plus the 2B dev baseline | ~$1 |
| **Total** | **~$5–6** |

No Jev on test sets, on extra pass@k samples, or for ad-hoc checks unless asked. The test sets use the 27B.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Reward hacking against Jev | gates, shortcut stage, independent 27B final judge, high-reward audits |
| Long v2 answers | 16k cap; truncation monitored; 16k-budget score reported |
| No 9B headroom on a task | Phase 1 gate; that OPD arm becomes a negative control |
| Jev rate limits or outages | backoff; a failed reward drops the rollout from the step and is logged |
| The 27B judge fails calibration | fall back to DeepSeek for the test sets only (~$1.55 per test evaluation × samples) |
| GPU contention on a shared account | ≤ 6 GPUs; node07 and node11 hold the environment and weights |

## 8. Phase 1 result: baselines complete (2026-10-06)

Full report: `artifacts/baselines/final-v3/v3-report/baseline-pass4.md`. Test sets, 400 questions per task, 4 samples
each, strict gates. JUDGE and RECONSTRUCT scores are judged by Qwen3.8-27B (calibration-qwen27b-v1).

| Metric (pass@1 / pass@4) | Qwen3.5-2B | Qwen3.5-9B | Headroom (pass@1) |
|---|---|---|---:|
| SOLVE accuracy % | 51.0 / 77.8 | 79.8 / 89.2 | +28.8 |
| JUDGE verdict % (pass@4 saturates by chance) | 64.3 / 94.8 | 87.6 / 97.8 | +23.3 |
| JUDGE first wrong step % | 34.8 / 74.0 | 87.9 / 98.5 | +53.1 |
| JUDGE V/L/E/M /100 (mean / best of 4) | 53.9 / 85.0 | 85.7 / 97.4 | +31.8 |
| RECONSTRUCT PC-v4 /100 (mean / best of 4) | 40.1 / 61.6 | 72.7 / 84.7 | +32.6 |
| RECONSTRUCT same question % | 2.9 / 8.0 | 19.6 / 32.5 | +16.7 |
| Gate failures (SOLVE / JUDGE / RECONSTRUCT) | 6.9 / 13.8 / 12.6 % | 3.2 / 5.4 / 3.8 % | |

- **The 9B gate passes on every task**, so all three OPD arms go ahead.
- 2B dev reference (Jev, RECONSTRUCT, sample 0): 40.1.
- The 27B judge agrees with DeepSeek as well as Jev does on total scores (JUDGE r 0.940, RECONSTRUCT 0.840).
  The 30-answer spot check found 28 of 30 sound. Details: `artifacts/qwen-judge-calibration/report.md`.

## 9. Updates (2026-10-06, after the baselines)

**GRPO runs first; OPD is postponed** (user decision).

**GRPO variant: Dr. GRPO** (Liu et al. 2025), not standard GRPO.
- Advantage = reward − group mean, no std division.
- Loss = token sum / 16,384 (the generation cap), with no per-answer 1/|o| normalization. This removes GRPO's
  length bias, which lets wrong answers grow long.
- Config: `GRPO_CONFIG` (`variant: dr_grpo`, `norm_tokens: 16384`).
- At typical 2B answer lengths (5–8k tokens) the effective step is about 0.3–0.5× the per-answer mean
  normalization at the same lr 5e-5.

No extra length reward and no soft overlong penalty, at the user's choice.
