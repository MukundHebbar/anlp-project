# Plan: Qwen3.5 baselines, GRPO vs on-policy distillation, and cross-task transfer (rev 2)

Date: 2026-10-06. Rev 2 folds in an external review (pasted 2026-10-06), checked against this repository's own
trial evidence (`docs/research/transfer-study/reconstruct-opd-trials.md`), and the v2-prompt probes.

**Question.** Train the Qwen3.5-2B student on one task (SOLVE, JUDGE or RECONSTRUCT) by GRPO, or by on-policy
distillation (OPD) from Qwen3.5-9B. How much does it improve on its own task, and how much does that transfer
to the other two?

**Output.** Two 3×3 transfer matrices, one per method. Each cell is Δ(i→j) = score_j(M_i) − score_j(M_init) on
the FINAL-v3 test sets. The plan also gives GRPO − OPD per cell, and splits off the warm-up's own share.

## 1. Locked configuration

### Shared by every training run

| Setting | Value | Source |
|---|---|---|
| Student | `Qwen/Qwen3.5-2B` post-trained, non-thinking | decided 2026-10-06 |
| LoRA | r 64, α 64, dropout 0, attention + MLP projections | matrix recipe |
| Optimizer | AdamW, **lr 5e-5 for both methods**, betas 0.9/0.999, wd 0, grad clip 1.0, no LR warm-up | review agrees |
| Rollouts | T 1.0, top-p 1.0, **64 trajectories per update**, 1 update per step (strictly on-policy) | |
| Importance-sampling cap | 2.0 (truncated IS for the vLLM-vs-trainer mismatch) | matrix recipe |
| Training cap | **pending decision, see §3** | probe: 32–38% of v2 answers exceed 8k, almost none looping |
| Steps | **52 for every arm, fixed before training.** Adapters kept at 26 and 52. Extending 52 → 104 later stays clean | review (b); budget |
| Seed | 1. Seeds 2–3 later, for the central comparisons only | |
| Prompts | FINAL-v3 train minus the 200-question dev slice, seeded order; student prompts v2 with the brevity line | |

### Starting point: the same for both methods, per task

| Task | Initial model M_init for **both** GRPO and OPD | Why |
|---|---|---|
| SOLVE | the untrained 2B (no warm-up) | In the matrix, SFT lowered SOLVE dev accuracy (57.5 → 49.0) |
| JUDGE | the 2B after a short SFT warm-up on 9B answers | as in the matrix |
| RECONSTRUCT | the 2B after a short SFT warm-up on 9B answers | Our trials: plain OPD from the untrained student collapses in 3–5 steps; penalties only slow it; the warm-up stops it |

The warm-up is **shared by both methods**, so it does not confound GRPO vs OPD (the review's option). The
warm-up-only checkpoints are evaluated as their own rows, so the warm-up's gain is reported separately.

- **Warm-up settings:** 256 examples, 1 epoch, batch 16, lr 1e-4 cosine to 1e-5, 3 warm-up steps.
- **Warm-up data:** 9B answers to the warm-up questions, 2 samples each.
  - Kept only if they pass the strict gates and are correct: verdict and step for JUDGE, Jev ≥ 70 for
    RECONSTRUCT (review: 70, not 50).
  - Keep the best answer per question.

### OPD

| Setting | Value | Note |
|---|---|---|
| Teacher | Qwen3.5-9B, 1 GPU, shared by the 3 students | tokenizer identical: 0 IDs differ, 30/30 prompts identical |
| Loss | per-token reverse KL, sampled token | |
| KL anchor to M_init | β 0.5 | our tested recipe; the review agrees |
| Overlong penalty | 1.0 | **Kept**, against the review. In OPD there is no group mean, so the review's GRPO argument does not apply. Our trials found it part of the only loop-free recipe |
| Teacher-only anti-repetition instruction | **kept** | Against the review: it is part of our tested regularised recipe (1.75% looping vs 7.75%). Reported as a method detail |
| Stop-token masking (review) | **not adopted** | Our trials found the loops start mid-answer, and the teacher agrees with where the student stops |

### GRPO

| Setting | Value | Note |
|---|---|---|
| Group | 8 prompts × 8 samples = 64 trajectories | compute-matched to OPD. **Not** data-matched: 416 vs 3,328 distinct prompts over 52 steps; stated as such |
| Advantage | reward − group mean, no std scaling, the same for every token | review agrees |
| KL anchor | **β 0** | review; standard for GRPO (DAPO, Dr. GRPO). A reward in [0, 1] cannot outweigh a 0.5 anchor |
| Truncated rollouts | **filtered**: left out of the loss and of the group mean, no penalty | review; DAPO overlong filtering |
| Groups with equal rewards | skipped (zero advantage) | |
| PPO clip 0.2 / 0.28 (review) | **not adopted** | Each batch gets exactly one update, so π/π_old = 1 apart from vLLM-vs-trainer numerical noise, which the IS cap handles. Clipping only matters with several updates per batch |
| SOLVE reward | 1 for a correct single final answer, else 0 | |
| JUDGE reward | 0 if the verdict is wrong; else 0.5 + 0.25·[right step] + 0.25·Jev (E+M)/8 | review agrees |
| RECONSTRUCT reward | Jev staged score / 100 (gate → shortcut stage → P/T/E/M); −0.1 for several drafts; gated or shortcut answers get 0 | |

### Evaluation

| Setting | Value |
|---|---|
| Protocol | protocol v2, T 1.0, one sample, 16k pass continued to 32k, v2 prompts, strict gates |
| Primary score | the 32k score, as in every earlier result |
| Secondary score | the **fixed 16k budget** score from the same generations (answers cut at 16k count as wrong), plus % truncated at 16k. This answers the review's test-time-compute point at no cost |
| JUDGE and RECONSTRUCT judge | Qwen3.8-27B, logit-reading. Deterministic and blind by construction: it sees only question, key and answer |
| Judge calibration | calibrated on DeepSeek-labelled samples, plus a 30-answer manual spot check |
| Exact and parser metrics | primary wherever they exist: SOLVE accuracy, JUDGE verdict and step |
| Dev | 200 questions per task, Jev, diagnostics only. They never choose the checkpoint, which is fixed at 52 |

## 2. Order of runs

**At most 6 GPUs at once** (user, 2026-10-06), although the account allows 8.

| # | Run | GPUs | GPU-h (8k / 16k cap) |
|---|---|---|---:|
| 1 | **Baselines:** 2B and 9B on the 3 test sets; 2B on the 3 dev slices | 6 | ~10 |
| 2 | 9B warm-up answers, JUDGE and RECONSTRUCT (in parallel with 1) | 2 | ~3 |
| 3 | SFT warm-ups (JUDGE, RECONSTRUCT) | 2 | ~0.5 |
| 4 | Basic checks: 2 steps of GRPO and 2 of OPD | 2 | ~0.5 |
| 5a | **Main runs, wave 1:** OPD ×3 + the shared 9B teacher (4 GPUs) and GRPO-SOLVE + GRPO-JUDGE (2 GPUs) | 6 | |
| 5b | **Main runs, wave 2:** GRPO-RECONSTRUCT, started on the first GPU wave 1 frees | 1 | ~55 in total at 16k |
| 6 | Evaluate the 6 trained checkpoints + 2 warm-up-only checkpoints on the 3 test sets | 8 | ~12 / ~14 |
| 7 | 27B judge: build and calibrate on saved answers, then score everything | 2 | ~4 |
| | **Total** | | **~60 / ~87** |

The ledger has 58 GPU-h left. API: about $10–12 of Jev in total.

## 3. Decision needed: the training cap

With v2 prompts, the 2B's answers average 5.7k (JUDGE) and 6.4k (RECONSTRUCT) tokens. 32.5% and 37.5% exceed
8k, and almost none of those are loops (2 of 56).

- **(A) 16k cap.** Follows the rule; about 87 GPU-h in total, so ~30 more GPU-h need approval.
- **(B) Shorter answers first.** Put an explicit budget in the prompts (e.g. "keep your reasoning under about
  1,000 words") and re-run the 5-minute probe.
  - Use 8k if no more than 5% of answers exceed 8k **and** JUDGE strict accuracy and RECONSTRUCT gate rate
    stay at the v2 levels.
  - Otherwise fall back to (A). This fits the current budget if it works.

## 4. Analysis (unchanged)

- Transfer matrices and asymmetry.
- Which sub-skills move: JUDGE V/L/E/M; RECONSTRUCT P/T/E/M; SOLVE by topic.
- GRPO vs OPD: per cell, plus cost.
- Controls: warm-up-only rows, format and gate rates, the reward-hacking audit (Jev vs 27B on dev, reading
  high-reward samples), and judge agreement.
- Limitations: one seed, 52 steps, and the training reward judge differs from the final judge by design.

## 5. Local judge option (considered 2026-10-06, NOT adopted)

**Decision: keep the Jev API** for GRPO rewards and dev judging (user, 2026-10-06). The analysis below is kept for
later. If adopted, the estimate is ~1–1.5 min of JEV-9B time per GRPO step on one L40S (mostly overlapped with
rollouts) and ~30–60 min per pass@4 test set. Main-run layout with Jev: unchanged (wave 1: OPD ×3 + teacher +
GRPO-SOLVE + GRPO-JUDGE; wave 2: GRPO-RECONSTRUCT).

### Option considered: a local judge instead of Jev

**Choice: `autotrust/JEV-9B`**, an open distillation of Jev 1.13 (Qwen3.5-9B + LoRA + decision head), served
locally on one L40S.
- It is the closest local equivalent of the Jev questions and calibration we already validated (card: KL ≈ 0.019
  to Jev, ECE 0.0007).
- It fits one GPU (18 GB).
- Its base differs from the final judge (Qwen3.8-27B), so the training reward stays independent of the final
  scorer. This rules out JEV-27B, which is built on the same 27B.

**Fallbacks**, in order:
- `EldanRing/Winnow-12B` (Gemma-4 base, so more independent; but GGUF only, on a llama.cpp fork);
- `jaredpalmer/kev-9b` (native 0–4 levels; validated only to 8k tokens).

**Rejected:**
- Quyet-1.0-Large: no evaluations, a 6k-token state cap, and it needs 2 GPUs.
- TIPS-Qwen3-4B-Thinking-Math: a long-reasoning PRM that gives binary step labels only, too slow for rewards.
  Possible later as an extra offline check of JUDGE's first-wrong-step and M.

**Before use**, the same validation Jev passed:
- on the 500-answer samples against DeepSeek, fit cutoffs on 4 checkpoints and test on the other 4;
- adopt only if agreement is at least Jev's (JUDGE total r ≥ 0.94; RECONSTRUCT P/T/E/M κ ≥ 0.68/0.74/0.63/0.72;
  shortcut stage ≥ 19 of 32 caught);
- then a throughput test at GRPO load.

**Main-run layout with the judge GPU** (max 6):
- wave 1: OPD ×3 + 9B teacher (4) + GRPO-SOLVE (1, no judge needed);
- wave 2: GRPO-JUDGE + GRPO-RECONSTRUCT (2) + JEV-9B judge server (1).
