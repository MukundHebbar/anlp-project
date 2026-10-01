# RECONSTRUCT OPD trials: what we tried and what worked

As of 2026-10-01. Full per-step records and judged outputs are in `artifacts/opd/turing/` and `artifacts/opd/evals/dev-reconstruct-*`. The detailed write-up is in section 5 of [baselines-and-opd-method.md](baselines-and-opd-method.md).

## Summary

An SFT warm-up on 470 teacher answers followed by OPD improves RECONSTRUCT significantly. Looping can be held close to the untrained student's level. Two variants work, scored on 400 questions: the 200 dev questions plus 200 held-out questions that no run used.

| Recipe (from SFT-470, 16 OPD steps) | Capped at 32k / 400 | PC-v4 vs untrained, pooled (n ≈ 300 paired) |
|---|---:|---|
| Untrained student | 1 (0.25%) | — |
| **OPD + KL anchor + overlong penalty + teacher instruction** | **7 (1.75%)** | **+3.7 [+0.3, +7.1]** |
| Plain OPD | 31 (7.75%) | **+7.6 [+4.2, +10.9]** |

- **The problem we started from:** plain OPD on RECONSTRUCT collapses within 3–5 steps. In the original trial, 85 of 200 dev answers looped to the 32k cap and PC-v4 fell by 18.6 points.
- **The trade-off:** plain OPD has the larger gain but loops 4–5× more often; the regularised version is almost loop-free with a smaller gain. Use the first when effect size matters most and the second when clean outputs do.
- **What doesn't work:** the teacher top-K loss removes the loops but also removes OPD's gain. Penalties without the warm-up only slow the collapse.

## Setup

Every trial used the same student, teacher, data and scoring.

| Item | Setting |
|---|---|
| Student / teacher | Qwen3.5-2B (LoRA r 64) / Qwen3.8-27B |
| OPD defaults | 32 prompts × 1 rollout per step, LR 5e-5, 16k-token rollouts at T 1.0, sampled-token reverse KL |
| Training data | 512 RECONSTRUCT train questions (16 steps); same questions and seeds in every trial |
| SFT warm-up | 512 other train questions × 2 teacher answers, filtered for format and repetition (470 kept); 1 epoch, LR 1e-4 |
| Dev evaluation | 200 RECONSTRUCT questions from the train split, disjoint from training; T 1.0, 32k cap, 1 sample |
| Quality score | PC-v4 judges (DeepSeek V4.1 Flash), paired against the untrained student; unusable answers count as 0 |
| Hardware | IIIT Turing node07, 3 × L40S (teacher on 2, student and trainer on 1) |

A "capped" answer ran to 32k tokens without finishing. Almost all of these are repetition loops.

## What we tried

PC-v4 change is paired against the untrained student, with 95% bootstrap CIs; n is about 140–165 questions judged in both runs. The untrained student scores about 35; the teacher scores about 70 on test.

| Run | What changed | Dev capped / 200 | PC-v4 change | Unusable / shortcuts |
|---|---|---:|---|---|
| Untrained student | — | 1 | — | 15 / 11 |
| Plain OPD (original, Modal) | nothing | 85 | −18.6 [−23.0, −14.3] | 77 / 19 |
| SFT-256 → plain OPD | small warm-up | collapsed at step 5 | not judged | — |
| T1 | overlong penalty 0.5 | collapsed at step 7 | not judged | — |
| T2 | KL anchor β 0.5 + overlong penalty 1.0 + anti-repetition teacher instruction | 11 | −2.3 [−7.0, +2.4] | 24 / 16 |
| T3 | T2 with LR 1e-5 | 16 | −8.6 [−13.3, −3.9] | 26 / 18 |
| T4 | T2 + soft length penalty from 4k tokens | collapsing, cancelled at step 5 | not judged | — |
| T5 | top-K loss (K 20) | 0 | −5.0 [−9.4, −0.7] | 6 / 26 |
| T6 | top-K + KL anchor to base, β 1 | 1 | −1.7 [−6.0, +2.3] at step 8; −4.1 at step 16 | 7 / 14 |
| T7 | T6 with JSD instead of reverse KL | barely moved from base; stopped | not judged | — |
| T8 | T2 + no teacher signal on rollouts over 8k tokens | collapsing, cancelled at step 4 | not judged | — |
| T9 | top-K + teacher instruction + anchor β 0.5 | 0 | +2.1 [−2.1, +6.5] at step 8; −5.9 at step 16 | 8 / 18 |
| T10 | T6 on 1,024 prompts | 0% truncated in training to step 12; stopped | not judged | — |
| SFT-470 only | full warm-up, no OPD | 2 | +2.3 [−3.0, +7.4] | 20 / 17 |
| **SFT-470 → plain OPD** | **full warm-up, then standard OPD** | **17** | **+5.9 [+1.3, +10.5]** (dev); +9.4 [+4.7, +14.3] held-out; +7.6 [+4.2, +10.9] pooled | **14 / 12** |
| SFT-470 → top-K + anchor to SFT | warm-up, then top-K | 4 | −1.0 [−5.8, +3.8] | 19 / 19 |
| **SFT-470 → OPD + anchor + overlong + instruction** | **best recipe with light regularisers** | **3** | +2.1 [−2.6, +6.9] at step 16 (dev); **+5.4 [+0.4, +10.4] held-out; +3.7 [+0.3, +7.1] pooled** | 10 / 24 |
| SFT-470 → plain OPD + unpaired SFT term (A) | 16 teacher answers per step, for other questions, weight 1 | 18 (+17 held-out) | +5.8 [+2.2, +9.5] pooled; −1.8 vs plain OPD | 21 / 19 |
| SFT-470 → top-K forward KL (F), 12 steps with 3 warm-up | forward instead of reverse KL | not evaluated: rollouts degenerated to gibberish by step 12 | — | — |
| Stable-OPD from the untrained student | paired golden demonstrations (266 of 512 questions, PC-v4 ≥ 50, no shortcut) + KL anchor β 0.5, 3 warm-up steps | collapsed: 41% truncated, repetition 0.55 at step 5; stopped | not judged | — |

Splitting the best result: the warm-up gives +2.3 [−3.0, +7.4], and OPD adds +3.1 [−1.5, +7.8] on top. On the same dev questions, plain OPD beats top-K OPD from the same warm-up by 6.3 points [+1.6, +11.6]. It also beats the regularised version by 2.5 points [−2.3, +7.4], which is not significant.

## What we learned

1. **The loops are likelihood hacking, not an end-of-turn problem.** The teacher agrees with where the student stops: the stop token's advantage is positive. The loops start mid-answer, after bland, low-content sentences. The teacher finds such text likely, so the sampled-token loss rewards it, and repeating it is the most likely text of all.
2. **Penalties only slow the collapse.** Overlong and soft length penalties, a KL anchor, a lower learning rate and length gating all delayed it. None stopped it, because the push towards longer answers comes from the teacher signal on normal-length answers.
3. **The top-K loss stops the loops but transfers form, not content.** Answers get short and committal, shortcuts double without an anchor, and mathematical validity falls. Content gains come only from the sampled-token loss and the SFT warm-up.
4. **The SFT warm-up carries content.** All four PC-v4 dimensions improve, and reconstructions matching the original question rise from 9 to 17. A warm-up on 470 answers also stops plain OPD from running away: training truncation held at 6–25% instead of climbing to 50%.
5. **Some fixes from the literature didn't help in our setup.** An SFT term during OPD on unpaired teacher answers added nothing over plain OPD. Forward KL on the top-K support broke the model, which is the mode-covering failure MiniLLM warns about for small students. Stable-OPD's components (paired golden SFT plus a KL anchor) from the untrained student only delayed the collapse by one step. That run used LoRA at LR 5e-5; Stable-OPD itself uses full fine-tuning at 1e-6.
6. **Training truncation is too noisy to judge a run.** With 32 rollouts per step, an 8% true rate often shows as 0 or 1. Dev generation at 32k is the reliable check.

## Recommendation and open decisions

- **Recipe for RECONSTRUCT:** an SFT warm-up on filtered teacher answers, then OPD.
    - **Regularised** (KL anchor β 0.5 to the SFT model, overlong penalty 1.0, anti-repetition teacher instruction): +3.7 pooled, 1.75% looping. This is the recommended default.
    - **Plain:** +7.6 pooled, 7.75% looping. Use it if the study weighs effect size above output quality, and report the loop rate.
- **Held-out check:** the 200 extra questions (`opd-extra-reconstruct.json`, first 200) were never used for training, warm-up or dev. The gains replicate there, which rules out dev-slice noise as the explanation.
- **Same recipe for all arms:** if RECONSTRUCT gets a warm-up, SOLVE and JUDGE should too. Each needs about 1.5 GPU-hours of teacher answers and 0.1 for SFT on Turing. This changes the "OPD only" decision and needs sign-off.
- **Limits:** one seed, 400 evaluation questions from the train split, and at most 16 OPD steps. A full pass over 3,600 questions is about 110 steps, so keep the stop rules and run a dev check every 16 steps.
- **Cost:** 36.9 of 42.5 approved Turing GPU-hours, and about $14 of DeepSeek judging.
