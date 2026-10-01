# Baselines and proposed OPD method

Status, 2026-09-30:
- **Baselines:** complete under evaluation protocol v2 (student Qwen3.5-2B, teacher Qwen3.8-27B, T 1.0, 32k cap).
- **OPD trials** (512 train prompts per task, dev slices of 200 train questions, section 5):
  - SOLVE: dev accuracy 52.0% → 61.5% after 16 steps.
  - JUDGE: V/L/E/M score 45.6 → 57.3 after 14 steps.
  - RECONSTRUCT: collapses into repetition loops within 3–5 steps. Two fixes were tried and neither worked (dropping truncated rollouts; a KL anchor with β 0.1). This is still open.

This document gathers the baseline results and the agreed training method in one place. For the full baseline configuration with time and cost of every run, see [baseline-results.md](baseline-results.md).
The fixed design decisions (dataset, splits, OPD only) are in the
[study design](../../design/reasoning-transfer-study.md#fixed-design-decisions). Every
baseline number here comes from the generated
[baseline report](../../../artifacts/baselines/final-v3/REPORT.md); the method and the run
history are in its [README](../../../artifacts/baselines/final-v3/README.md) and
[RUN_LOG](../../../artifacts/baselines/final-v3/RUN_LOG.md).

## 1. Setup

### Tasks and data

[FINAL-v3](../../../data/manifests/final-v3/README.md) provides 4,000 DeepMath-103K
questions per task, split 3,600 train / 400 test.

- Each task uses **different questions**, with no overlap between tasks, counting duplicate copies.
- The tasks are matched by distribution: the same four topic buckets, difficulty 5.0–8.0, and difficulty shares within about one percentage point (about 30% of each task at 7.0–8.0).

| Task | Model sees | Model produces |
|---|---|---|
| SOLVE | a question | a solution ending in `<final_answer>…</final_answer>` |
| JUDGE | a question and a step-by-step proposed solution (S1…Sn) | `Decision:` correct/incorrect, `First wrong step:`, `Explanation:` |
| RECONSTRUCT | the final answer and 4 clues; the question is hidden | JSON with `assumptions`, `question`, `justification` |

JUDGE test is balanced: 200 correct and 200 incorrect proposed solutions.

### Models

| Role | Model | Notes |
|---|---|---|
| Student | `Qwen/Qwen3.5-2B` | bf16, text-only, non-thinking chat template |
| Teacher | `Qwen/Qwen3.8-27B` | bf16, text-only, non-thinking chat template |
| Judge (evaluation only) | `deepseek-ai/DeepSeek-V4.1-Flash` via DeepInfra | temperature 0, reasoning low; never used for training |

**Tokenizer compatibility.** Token-level OPD needs the student and teacher to give each
token ID the same meaning. The check was run on Qwen3.5-4B, but the 2B uses the same
Qwen3.5 tokenizer and the same 248,320-entry vocabulary:
- All 248,070 student tokens have the same IDs in the teacher.
- The teacher adds 7 audio/TTS special tokens, which the student never produces.
- 41/41 sample texts, including final-v3 prompts and long solutions, encode identically.
- The rendered non-thinking chat prompt is identical token for token.

A one-line check on the 2B tokenizer itself should precede training.

### Why a 2B student and a 32k cap

The first baselines used Qwen3.5-4B at an 8,192-token cap (section 5). Two problems came up:
- **The cap was binding.** On answers that finished, the 4B's SOLVE accuracy was 95.1% vs the teacher's 97.9%, so most of its SOLVE gap came from answers cut off at 8k. At 16k it reached 79% on 200 test questions, close to the teacher, leaving SOLVE almost no room to improve.
- **The 2B has a genuine gap on all three tasks.** It gives many more outright wrong SOLVE answers.

Standard practice evaluates at 32k tokens or more, including non-thinking mode (Qwen3,
Qwen3.5, DeepSeek-R1). OPD commonly trains on shorter rollouts than it evaluates on.
Hence: **16k-token training rollouts, 32k-token evaluation.** The student choice was
informed partly by test questions (200 SOLVE test questions); this is recorded as a
limitation.

## 2. Evaluation protocol (v2, frozen)

Each model answers every test question once. The same settings are used for every trained checkpoint.

- **Sampling:** temperature **1.0**, top_p **1.0** (off), top_k off, no penalties, seed 0, one sample per question, at most **32,768** new tokens. A cut-off answer counts as a failure.
- **Why:** these settings match the OPD training rollouts. They follow the train-matched evaluation of Thinking Machines/Tinker, AsyncOPD and Prefix OPD; no OPD maths paper checked uses the model card's settings or a presence penalty.
- **Replaced protocol v1:** T 0.7 / top_p 0.8 / top_k 20, Qwen's *general* non-thinking defaults. On the SOLVE dev slice, the OPD-trained student looped on 89 of 200 questions under v1. At the training temperature its accuracy rose from 52.0% to 61.5% (+9.5 points, p = 0.009).
- **Prompts, scoring, judges and retry rules** are unchanged. See [baseline-results.md](baseline-results.md#2-configuration-protocol-v2-frozen).

## 3. Baseline results (protocol v2, test set, 400 per task)

| Metric | Student Qwen3.5-2B | Teacher Qwen3.8-27B |
|---|---:|---:|
| SOLVE accuracy | 55.8% | 79.5% |
| JUDGE verdict accuracy | 57.5% | 73.5% |
| JUDGE first wrong step (incorrect solutions) | 18.0% | 55.5% |
| JUDGE V/L/E/M score /100 | 47.0 | 78.1 |
| RECONSTRUCT PC-v4 /100 (scored items) | 36.0 | 70.1 |
| RECONSTRUCT same original question | 5.0% | 28.2% |

Full tables, intervals, time and cost are in [baseline-results.md](baseline-results.md). The protocol v1 results are kept there for reference.

## 4. Proposed method: reverse-KL on-policy distillation

### Training arms

The core experiment trains three independent students from the same starting checkpoint
(Qwen3.5-2B), one per task:

| Arm | Training prompts |
|---|---|
| M_S | SOLVE train (3,600) |
| M_J | JUDGE train (3,600) |
| M_R | RECONSTRUCT train (3,600) |

Each trained student is evaluated on all three test sets with the frozen protocol of
section 2. Transfer is reported as

    Δ(i → j) = score_j(M_i) − score_j(M_0)

where M_0 is the untrained student (section 3). Comparisons are made within a test task's
column.

- **All 3,600 training questions per task are used.** Only train/test separation is enforced.
- **The final checkpoint is the one evaluated,** declared in advance; there is no checkpoint selection.
- **The training inputs are the FINAL-v3 `training.input` prompts,** rendered with the same prompts as evaluation. The stored chain-of-thought and target fields are not used.

### Objective

For a prompt x, the student samples a response y ~ π_θ(· | x) at **temperature 1.0**, so
that the rollouts come from the distribution the loss is defined on. The teacher then
scores the same tokens under the same prompt. For each generated token t:

    A_t = log π_teacher(y_t | x, y_<t) − log π_θ(y_t | x, y_<t)      (treated as a constant)
    loss = − (1 / B) Σ_rollouts (1 / |y|) Σ_t min(r_t, 2) · A_t · log π_θ(y_t | x, y_<t)

The loss is the token mean within each rollout, then the mean over the B rollouts of the
step. The discount is 0, so each token is credited only with its own log-ratio.
r_t = π_θ(y_t) / π_vLLM(y_t) is a token-level importance weight, capped at 2. It corrects
for small numerical differences between the vLLM sampler and the trainer.

This is the sampled-token estimate of the per-token reverse KL, KL(π_θ ‖ π_teacher):
- It lowers the probability of tokens the student likes but the teacher does not.
- It needs only the teacher's log-probability of the tokens actually generated. Full-vocabulary KL would need gigabytes of teacher scores per long answer.
- The student's log-probabilities are taken from the trainer, which is where the gradient flows. The gap between the trainer's and vLLM's log-probabilities is logged as a health check.
- The teacher never sees the reference answer or any hidden information: it gets exactly the student's prompt.

**Truncated rollouts** (those reaching 16k tokens) stay in the loss, following common OPD
practice. The recent OPD literature reports that reverse KL can inflate length and
repetition, so the truncation rate, mean length and repetition are monitored every step.

**Repetition** is measured per rollout on its last 4,096 generated tokens:
1 − (distinct 8-token n-grams ÷ all 8-token n-grams). A value of 0 means no 8-token run
repeats; a verbatim loop scores close to 1. The step value is the mean over its 32 rollouts.

**Automatic stop.** The run stops after any step where one of these holds:
- the loss or the vLLM/trainer log-prob gap is NaN;
- the mean absolute log-prob gap exceeds 0.5;
- repetition is above 0.5 for 2 consecutive steps;
- truncation is more than 15 points above step 1's for 3 consecutive steps.

### System: two H100 80 GB GPUs

| GPU | Component | Memory, approx. |
|---|---|---:|
| 0 | Student rollouts: vLLM, Qwen3.5-2B + current LoRA adapter, KV cache | ≈ 15–25 GB |
| 0 | Student trainer: HF + PEFT LoRA, gradient checkpointing, log-probs computed in chunks (the 248k vocabulary makes full logits large) | ≈ 20–35 GB |
| 1 | Teacher scoring: vLLM, Qwen3.8-27B bf16, stays loaded; token log-probs only, with batch size bounded in tokens | ≈ 54 GB weights + working memory |

One step:
1. The student's vLLM generates responses for a batch of prompts.
2. The teacher's vLLM returns the log-probability of every generated token.
3. The trainer computes the loss and takes **one** optimiser step.
4. The new LoRA adapter (tens of MB) is loaded into the student's vLLM before the next batch.

The teacher never has to leave the GPU, and every batch is generated by the current policy.

### Configuration (as run in the trials)

This is `TRIAL_CONFIG` in [opd.py](../../../src/anlp_project/opd.py). Every run saves its
exact configuration as `config.json` next to its metrics.

| Setting | Value |
|---|---|
| Rollout batch | 32 prompts per step, 1 sample per prompt |
| Updates per rollout batch | 1, then the new adapter is loaded into the student's vLLM (fully on-policy) |
| Rollout sampling | temperature 1.0, top_p 1.0, at most **16,384** new tokens (all three tasks) |
| Objective | per-token reverse KL, sampled-token estimator, discount 0; token-level importance weight capped at 2.0 |
| Loss normalisation | token mean within each rollout, then mean over rollouts |
| Student adapter | LoRA rank 64, alpha 64, dropout 0; `q/k/v/o_proj`, `in_proj_qkv`, `in_proj_z`, `out_proj`, `gate/up/down_proj` (attention, Gated-DeltaNet linear attention and MLP); vision tower excluded; 62.5M trainable parameters |
| Optimiser | AdamW, learning rate 5e-5 constant, no warm-up, betas (0.9, 0.999), no weight decay, gradient clipping 1.0, bf16 |
| Automatic stop | see above |
| Seeds | 1 |
| Checkpoints | adapter saved after every step; the final one is evaluated |
| Evaluation | protocol v2 (section 2): temperature 1.0, top_p 1.0, no top-k, no presence penalty, 32,768-token cap, one sample, the same prompts and judges |
| Software | vLLM 0.30.0, transformers 5.17.0, PEFT 0.21.1, flash-linear-attention 0.5.2 (pinned in the Modal image) |

Two options exist for the RECONSTRUCT problem and are **off by default**:
- `drop_truncated`: leave rollouts that hit the cap out of the loss; skip the update if all are dropped.
- `kl_anchor_beta`: subtract β · (log π_θ − log π_init) from each token's advantage, where π_init is the untrained student (LoRA adapter disabled).

For the full arms, the budget per arm (steps or prompts) is still to be fixed. One pass
over 3,600 prompts at 32 per step is 113 steps.

### What the transfer matrix will report

For each checkpoint and test task:
- the headline metric of section 3;
- budget-limited accuracy within 8k and 16k tokens;
- checkable-only accuracy;
- the cap-hit rate and mean answer length.

The teacher writes much shorter answers than the student. Any OPD run is likely to make
the student more concise, which by itself reduces runaway answers and raises accuracy
whichever task was trained. Reporting length, cap hits and checkable-only accuracy keeps
"the student learned to stop" apart from "the student learned the mathematics".

### Deferred (not in the current run)

- **Placebo control:** OPD on non-maths prompts with the same budget. It would separate generic effects of distillation, such as conciseness, from task-specific transfer. Its absence is a limitation of the current study. The length and checkable-only columns above partly compensate.
- Additional seeds, the mixture arms (S+J, S+R, J+R, S+J+R), and a second student size.

### Next steps and risks

- **Resolved by the probe and trials:**
  - vLLM hot-swaps LoRA adapters on the Qwen3.5 hybrid architecture.
  - Memory: the trainer peaks at about 9 GiB. GPU 0 uses about 37 GB and GPU 1 about 71 GB.
  - The vLLM/trainer log-prob gap stays at 0.01–0.02.
- **Open:** the RECONSTRUCT recipe (sections 5.4–5.5). The full three arms and test evaluation follow once it is fixed, on the October credits.

Rough cost, from measured Modal rates (2 × H100 with CPU and memory ≈ $9/h):
- A step takes 2–4 minutes at 16k.
- Start-up and compilation add about 8 minutes per run.
- Evaluating a checkpoint (1,200 answers at 32k) costs about $1.30 of Modal plus about $1.40 of DeepSeek judging.

## 5. OPD trials (dev slices, September 2026)

### 5.1 Setup

- **Slices:** for each task, 512 training prompts and a disjoint 200-question dev slice, both drawn from the FINAL-v3 **train** split (seed 20260930, [opd.py](../../../src/anlp_project/opd.py)). The test split was not used. The slices are in `data/manifests/final-v3/opd-trial-{solve,judge,reconstruct}.json`.
- **Training:** the configuration of section 4, planned as 16 steps (16 × 32 = 512 prompts, one pass).
- **Evaluation:** protocol v2 on the dev slice, with the same scoring and DeepSeek judges as the baselines.
- **Hardware:** Modal, 2 × H100 for training and 1 × H100 for evaluation.
- **Records:** `artifacts/opd/<run>/` holds the configuration, per-step metrics and logs; `artifacts/opd/evals/<run>/` holds every dev answer, score and judge call. The LoRA adapters (about 250 MB each) are kept in the Modal Volumes, not in git: `anlp-opd-cache` (ARYAMA) and `anlp-final-v3-hf-cache` (SANGHA), under `opd/<run>/adapters/step<N>`.

### 5.2 Results

The comparisons are paired over the same dev questions.

| Task | Run | Steps | Dev result, untrained → after OPD |
|---|---|---:|---|
| SOLVE | `trial-solve-20260930T032839Z` | 16 | Accuracy **52.0% → 61.5%**, +9.5 points [+2.5, +16.0], McNemar p = 0.009 |
| JUDGE | `trial-judge-20260930T100917Z` (+ `-resume12`) | 14 | V/L/E/M score **45.6 → 57.3** (+11.8 [+6.8, +16.8], 194 questions judged in both) |
| | | | First wrong step (86 incorrect solutions) 14.0% → 25.6%, p = 0.002 |
| | | | Verdict accuracy 55.0% → 60.0%, p = 0.076 |
| RECONSTRUCT | `trial-reconstruct-20260930T100915Z` | 5 (automatic stop) | PC-v4, unusable = 0: **36.0 → 17.3** (−18.6 [−23.1, −14.4], 167 resolved in both) |
| | | | Unusable answers 15 → 77; answers at the 32k cap 1 → 85 (0.5% → 42.5%) |

Other observations:
- **Mean answer length on SOLVE and JUDGE fell:** SOLVE 7,605 → 6,646 tokens, JUDGE 3,046 → 2,262.
- **The JUDGE run had 14 steps, not 16.** A client cancellation stopped it after step 12. It was resumed from the step-12 adapter with a fresh AdamW state (the optimiser state is not saved), then stopped again after step 14. Reverse KL was flat over steps 9–14, so the step-14 adapter was evaluated.
- **Per-step training metrics** (mean length, truncation, repetition, reverse KL) are in each run's `metrics.jsonl`.

### 5.3 The RECONSTRUCT collapse

| Step | 1 | 2 | 3 | 4 | 5 |
|---|---:|---:|---:|---:|---:|
| Truncated at 16k | 0% | 0% | 16% | 44% | 50% |
| Repetition | 0.05 | 0.08 | 0.27 | 0.53 | 0.58 |

- **The capped dev answers are loops.** Of the 85 answers that hit the 32k cap after training:
  - 77 repeat a block verbatim;
  - 5 are counting loops ("for a = 869 … for a = 870 …");
  - 1 is a near-verbatim repetition;
  - the other 2 are not loops.
- **Why:** once a loop has started, the teacher predicts its continuation with high probability too, because it copies from its context. The sampled-token advantage log π_teacher − log π_student is therefore positive on loop tokens, and training reinforces them. With discount 0, nothing in the loss rewards stopping. Several 2026 OPD papers describe the same failure; see section 5.5.
- **SOLVE and JUDGE did not collapse.** SOLVE had one high step (repetition 0.48, truncation 31% at step 3), then recovered to about 0.2. JUDGE peaked at 0.29.

### 5.4 Fix trials

Both trials used the same prompts and seed as the original RECONSTRUCT trial and a 6-step budget, with the repetition stop added.

| Step | A: drop truncated (trunc / rep / rollouts used) | B: KL anchor β 0.1 (trunc / rep / anchor KL) |
|---|---|---|
| 1 | 0% / 0.05 / 32 | 0% / 0.07 / 0.000 |
| 2 | 9% / 0.17 / 29 | 3% / 0.10 / 0.006 |
| 3 | 31% / 0.40 / 22 | 22% / 0.34 / 0.040 |
| 4 | 53% / 0.61 / 15 | 47% / 0.50 / 0.062 |
| 5 | 75% / 0.76 / 8 | 56% / 0.72 / 0.040 |
| Stopped by | repetition rule | truncation rule |

Runs: `fix-reconstruct-drop-20260930T135756Z` (ARYAMA) and `fix-reconstruct-kl0.1-20260930T135809Z` (SANGHA).

- **Neither fix works.** Both collapse at least as fast as the original run, so the adapters were not evaluated.
- **Dropping truncated rollouts is the worst of the three.** Loops that end just under the cap are still trained on. By step 5 only the 8 shortest rollouts remained, and they were loops too. The update was never skipped, because at least one rollout always finished under the cap.
- **The anchor at β 0.1 is too weak.** Its per-token penalty (about 0.1 × 0.05) is roughly 50× smaller than the teacher term (about 0.2–0.3). The reference model also continues a loop once it is in context, so a per-token anchor can only resist where the loop starts.

### 5.5 Literature on loops in OPD, and candidate next fixes

- **Teacher agreement on degenerate prefixes** is reported as a main failure mode:
  - [Revisiting OPD](https://arxiv.org/abs/2603.25562): "tokens with high teacher probability can remain rewarded even after the trajectory has drifted into repetition".
  - [KL agreement trap / KAT](https://arxiv.org/abs/2606.09471): stops the rollout once a sliding-window KL stays low; 60% shorter rollouts and +2.7 points avg@8.
- **Length exploitation of token-mean losses:** [Demystifying OPD](https://arxiv.org/abs/2607.13399). Clipping the advantage reduced length only moderately.
- **Stable-OPD** ([2604.08527](https://arxiv.org/abs/2604.08527)): a reference-KL term alone raised accuracy only from 28.0 to 29.7; most of its gain came from an SFT loss on reference solutions, which this study excludes.
- **End-of-sequence mismatch** ([2609.20511](https://arxiv.org/abs/2609.20511)) arises between base students and post-trained teachers. Both of our models are post-trained instruct models.
- **Changing the divergence (e.g. JSD)** does not remove teacher agreement inside a loop. The loss change with evidence is teacher top-K local support matching (Revisiting OPD, K = 32). It needs top-K teacher log-probs and would have to be applied to all three arms.

**Candidate next fix (not yet run):** a loop-aware advantage. Flag a token when the 32-token span ending at it has already appeared earlier in the same rollout. Replace the teacher advantage on flagged tokens with a small fixed penalty, in the manner of unlikelihood training and n-gram repetition penalties in RL. SOLVE and JUDGE rarely repeat 32-token spans, so the same recipe could be applied to all three arms.

### 5.6 Time and cost

Modal costs are from the workspace billing meter and include start-up, compilation and Volume storage.

| Part | Workspace | Wall-clock | Modal |
|---|---|---:|---:|
| Probe (2 SOLVE steps), SOLVE trial (16 steps, 44 min) and its 3 dev evaluations | ARYAMA | | ≈ $11.1 |
| JUDGE trial (12 steps, 28 min) + resume (2 steps), RECONSTRUCT trial (5 steps, 19 min), dev evaluations, one cancelled evaluation | ARYAMA | | ≈ $12.6 |
| Fix trial A (5 steps) | ARYAMA | 17 min | $4.43 |
| Fix trial B (5 steps) | SANGHA | 17 min | $4.44 |

DeepSeek judging for the JUDGE and RECONSTRUCT dev evaluations cost $1.33.

### 5.7 RECONSTRUCT follow-up trials on Turing (1 October 2026)

**Setup.**
- **Hardware:** IIIT Turing, node07, L40S GPUs. The teacher runs on 2 GPUs (tensor parallel); the student's vLLM and the trainer share 1.
- **Code:** the same loop as Modal, moved into [opd_train.py](../../../src/anlp_project/opd_train.py). Turing scripts are in [scripts/turing/](../../../scripts/turing/).
- **Trials:** same questions and seeds as the Modal RECONSTRUCT trial, 8 steps each unless noted.
- **Evaluation:** protocol v2 on the 200 RECONSTRUCT dev questions, run on Turing. The untrained student gives the same result there as on Modal: 1 capped answer, 2,930 tokens on average.
- **Judging:** PC-v4 is paired against the untrained student's dev answers, with unusable answers counted as 0. Questions with an unresolved judgment in either run are dropped, so n is about 140–165.
- **Records:** in `artifacts/opd/turing/` (configs, per-step metrics, every rollout's text, logs, job scripts, GPU-hour ledger) and `artifacts/opd/evals/dev-reconstruct-*`.

**Results.**

| Trial | Changes from plain OPD | Training: truncated / repetition by step 5 | Dev capped | Dev mean length (tokens) | PC-v4 paired diff [95% CI] | Unusable / shortcuts |
|---|---|---|---:|---:|---|---|
| Untrained | — | — | 1 | 2,930 | — | 15 / 11 |
| Modal plain OPD | none | 50% / 0.58, stopped at step 5 | 85 | 15,025 | −18.6 [−23.0, −14.3] | 77 / 19 |
| SFT-256 only | SFT on 256 filtered teacher answers | — | 4 | 4,423 | not judged | — |
| SFT-256 + OPD | warm-up | 28% / 0.36, stopped at step 5 | — | — | — | — |
| T1 | overlong penalty 0.5 | 28% / 0.38 (41–44% at steps 4 and 6), stopped at step 7 | — | — | — | — |
| T2 | anchor β 0.5 + overlong 1.0 + teacher instruction | 28% / 0.35, then 6–34% | 11 | 6,361 | −2.3 [−7.0, +2.4] | 24 / 16 |
| T3 | T2 with LR 1e-5 | 0% / 0.07 | 16 | 5,934 | −8.6 [−13.3, −3.9] | 26 / 18 |
| T4 | T2 + soft length penalty from 4k | 31% / 0.45, cancelled at step 5 | — | — | — | — |
| T5 | **top-K loss** (K 20), 16 steps | 3% / 0.17 | 0 (step 16) | 829 | −5.0 [−9.4, −0.7] | 6 / 26 |
| T6 | **top-K + top-K anchor to the base model, β 1**, 16 steps | 0% / 0.09 | 1 (step 8), 1 (step 16) | 1,752 / 2,187 | **−1.7 [−6.0, +2.3]** (step 8), −4.1 [−9.2, +0.8] (step 16) | 7 / 14, 12 / 14 |
| T7 | T6 with JSD instead of reverse KL | 0% / 0.04, stopped at step 8 (barely moved from the base) | not evaluated | | | |
| T8 | T2 + teacher signal only for rollouts ≤ 8k tokens | 28% / 0.41 at step 4, cancelled | — | — | — | — |
| T9 | top-K + teacher instruction + top-K anchor β 0.5, 16 steps | 6% / 0.15 | 0 (step 8), 1 (step 16) | 1,215 / 1,739 | **+2.1 [−2.1, +6.5]** (step 8), −5.9 [−10.5, −1.6] (step 16) | 8 / 18, 19 / 13 |
| T10 | T6 recipe on 1,024 prompts | 6% / 0.11; 0% truncated from step 6; stopped at step 12 | not evaluated | | | |
| SFT-470 only | SFT on all 470 filtered teacher answers | — | 2 | 3,575 | +2.3 [−3.0, +7.4] | 20 / 17 |
| **SFT-470 + plain OPD** | warm-up, then the standard sampled-token OPD, 16 steps | 9% / 0.20; plateau 6–25%, never ran away | 33 (step 8), **17 (step 16)** | 6,893 / 4,391 | **+5.9 [+1.3, +10.5]** (step 16) | 14 / 12 |
| SFT-470 + top-K + anchor to SFT | see below | | | | | |

**Diagnosis.**
1. **The loops are not an end-of-turn problem.** At the stop token the teacher's advantage is positive (+0.08 to +0.5). In 13 of the 14 capped rollouts inspected, the JSON never closed. Loops start mid-reasoning, after bland, low-content statements.
2. **Likelihood hacking under the sampled-token reverse KL.**
   - Generic, predictable text has high teacher probability, so loop tokens get a positive advantage.
   - Penalties on length, a KL anchor and a teacher instruction only slow this down.
   - The teacher instruction ("Be concise. Never repeat …") lowers the teacher's log-prob on loop tokens by 0.13 nats and on other tokens by under 0.02. The shorter version lowers it by only 0.04.
3. **The estimator is the cause.** Replacing it with the teacher top-K local-support KL ([Revisiting OPD](https://arxiv.org/abs/2603.25562)) removes the loops on dev: 0–1 capped answers out of 200. No penalty is needed.
4. **Imitation transfers form, not content.**
   - Every method that pulls the 2B towards the teacher makes it adopt the teacher's style: SFT made answers 40% longer and more exploratory, and top-K made them short and committal.
   - The content doesn't come with it. Plain top-K doubled shortcuts (26 vs 11) and lowered mathematical validity from 0.84 to 0.46. The teacher takes 5 shortcuts on 400 test questions and has mathematical validity 2.5.
   - A top-K anchor to the base model keeps shortcuts at the base level, but quality is still not above the base.
   - Across trials, more pull towards the teacher scores worse: β 0 below β 1, and step 16 below step 8.
5. **Per-step training truncation is too noisy to judge a run.** With 32 rollouts, a true rate of about 8% often shows as 0 or 1 of 32. Dev generation at 32k is the reliable check.

**Cost.**
- GPU-hours by stage are in the ledger `artifacts/opd/turing/turing_budget.json`; all jobs are listed with sacct-charged time.
- Teacher answers: 1.5 GPU-h. SFT: 0.13 GPU-h. Each OPD trial: 1.3–2.6 GPU-h. Each dev check: 0.1–0.2 GPU-h.
- DeepSeek judging: about $0.5 per judged adapter.

## 6. Earlier protocol (for reference)

The first baselines used **Qwen3.5-4B at an 8,192-token cap.** Test set, 400 per task:

| | 4B student | Teacher |
|---|---:|---:|
| SOLVE accuracy | 73.0% | 80.8% |
| JUDGE verdict accuracy | 64.0% | 76.2% |
| RECONSTRUCT PC-v4 /100, unusable = 0 | 58.3 | 71.5 |

These are superseded by section 3. They remain in the
[report](../../../artifacts/baselines/final-v3/REPORT.md) and are useful as a second student
size.
