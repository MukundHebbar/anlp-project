# What RL on a checking task changes inside a small reasoning model

Qwen3.5-2B, LoRA (rank 64, all attention and MLP projections, 24 layers), Dr. GRPO. Phase 1 trained one adapter per
task on matched DeepMath data: **SOLVE** (write a solution), **JUDGE** (find the first wrong step of a step-numbered
solution), **RECONSTRUCT** (recover a question from its answer and clues), plus a **mixed** adapter on all three. This
note collects what the Phase-2b analyses found about the checking skill. Error-finding is scored on ProcessBench
(3,400 step-split solutions by 12 other models, first error labelled by humans) and on the synthetic JUDGE test set
(DeepMath problems, one injected error), with the same JUDGE prompt and sampling for every model.

## 1. The checking skill learned by JUDGE RL lives in the first layers, and is transplantable

Hybrid adapters: the SOLVE adapter with the LoRA weights of some layers replaced by another adapter's. F1 = harmonic
mean of exact-first-error accuracy on wrong solutions and accuracy on correct ones. Paired bootstrap (2,000) vs the
plain SOLVE adapter; ProcessBench = GSM8K + MATH (1,400 solutions).

| SOLVE adapter with layers ... from ... | ProcessBench F1 change | Synthetic F1 change | SOLVE dev accuracy change (4 samples) |
|---|---|---|---|
| 0–5 from JUDGE | **+15.3** [+11.5, +19.2] | **+16.1** [+10.2, +22.4] | −1.8 [−5.1, +1.6] |
| 0–3 from JUDGE | +11.5 [+7.5, +15.5] | +8.9 [+2.1, +15.8] | |
| 6–11 / 12–17 / 18–23 from JUDGE | +6.8 / +2.2 / +4.5 | +3.3 / +3.5 / −1.8 | |
| single layers 0, 1, 2, 3, 4, 5 from JUDGE | +4.7, +5.4, +2.5, +3.2, −1.5, +1.7 | | |
| all 24 from JUDGE (= the JUDGE adapter) | +10.7 [+6.8, +14.9] | +14.0 [+7.9, +20.8] | **−12.2** [−17.0, −7.4] |
| **Controls** | | | |
| 0–5 with SOLVE's update removed (base weights) | +0.4 [−3.6, +4.5] | −3.7 | |
| 0–5 filled with JUDGE's layers 16–21 (same size and type of change, wrong place) | −2.7 [−6.7, +1.3] | −4.0 | |
| 0–5 from RECONSTRUCT | −2.0 [−6.3, +2.1] | −2.3 | |
| 0–5 from mixed | +12.6 [+8.7, +16.4] | +16.6 [+10.0, +22.9] | +0.8 [−2.4, +4.0] |
| *Reverse: JUDGE adapter with SOLVE's layers 0–5* | *JUDGE's +10.7 falls to +1.6* | | |

- The JUDGE adapter's update is spread evenly over depth (each 6-layer block holds 24–26 % of its norm), so the
  effect is not where the update is largest.
- The skill is distributed over roughly the first four layers and adds up across them (single layers sum to about the
  block).
- Causal in both directions: adding JUDGE's early layers to SOLVE confers the skill; removing them from JUDGE takes it
  away.
- **The composite beats both parents.** Among answers that give a verdict, exact first-error localization on
  ProcessBench is SOLVE 47.5 %, JUDGE 48.4 %, composite **59.3 %**, mixed-trained 61.0 %: JUDGE RL alone mostly taught
  the model to give a verdict; its early layers combined with SOLVE's later layers localize errors as well as a model
  trained on all three tasks, with no training.
- **It generalizes** to unseen, harder subsets and keeps most of SOLVE (SOLVE test set: 400 questions x 4 samples,
  16k cap; F1 on 1,000 solutions per subset; same run for all four adapters):

| Adapter | OlympiadBench F1 | Omni-MATH F1 | SOLVE test accuracy (change, 95% CI) | pass@4 |
|---|---|---|---|---|
| SOLVE | 44.2 | 35.0 | 66.6 | 84.0 |
| **SOLVE + JUDGE layers 0–5** | **53.1** | **46.6** | 62.7 (−3.9 [−6.4, −1.4]) | 83.75 |
| JUDGE | 54.0 | 42.2 | 49.8 (−16.8 [−19.7, −13.9]) | 77.75 |
| Mixed | 53.2 | 43.9 | 66.5 (−0.1 [−2.6, +2.3]) | 83.0 |
- **Mixed training does not localize.** Mixed's early layers carry checking (+12.6 into SOLVE), but removing them from
  the mixed adapter costs little (−2.2 [−5.5, +1.0]): joint training spreads the skill over depth, specialist RL
  concentrates it early.

## 2. What transfers between task forms is mostly response bias

Signal-detection split of each model's verdicts: sensitivity d′ (separating wrong from right solutions) and criterion
c (negative = quick to say "wrong").

| Model | JUDGE test d′ / c | ProcessBench d′ / c | ProcessBench exact step, given a flag |
|---|---|---|---|
| Untrained | 0.73 / −0.04 | 2.13 / +0.25 | 49.7 % |
| SOLVE-trained | 1.17 / +0.13 | 2.35 / +0.40 | 55.0 % |
| JUDGE-trained | 1.64 / +0.30 | 2.50 / +0.68 | 52.9 % |
| RECONSTRUCT-trained | 1.05 / **−0.46** | 2.25 / **−0.18** | 54.4 % |
| Mixed | **2.32** / +0.27 | **2.63** / +0.45 | **61.1 %** |

RECONSTRUCT training "transfers" to checking by making the model suspicious, not discerning; it matched JUDGE's
ProcessBench F1 with SOLVE-level sensitivity. On natural errors the untrained model already discriminates well; most of
the trained F1 gain is giving a parseable verdict, the criterion, and localization.

## 3. An error representation exists before training, and fails exactly where verbal checking fails

A crosscoder (shared TopK dictionary, 8,192 latents) on the untrained and mixed models' residual streams:

- No model-specific latents at layers 12 or 18 (decoder-norm share 0.48–0.52 for every live latent); GRPO changed
  activations by 8–9 %. The LoRA RL adapters reuse existing features.
- A shared latent at layer 18 flags the first wrong step: held-out AUROC 0.80, unchanged when controlling for step
  position (0.80), excluding final-answer steps (0.80), within wrong solutions only (0.80), and adding to a
  position + length + final-step baseline (0.69 → 0.82). It transfers to OlympiadBench / Omni-MATH (0.73 at layer 12)
  and to the synthetic set (0.74), across all 12 ProcessBench generator models (0.67–0.82, lower for 72B writers).
- **It is at chance (0.50–0.53) on solutions freshly sampled from our models** (the untrained 2B, the mixed model, the
  9B, condensed or not), as is verbal JUDGE (0.49–0.67).

## 4. Why checking fails on the model's own attempts: length and error distribution, not self-blindness

JUDGE (specialist / mixed) AUROC at telling wrong from right attempts, 200 dev problems × 4:

| Attempts | Mean length | AUROC |
|---|---|---|
| Own, step format | 6,317 tokens | 0.58 / 0.54 |
| Untrained 2B's | 4,662 | 0.55 / 0.49 |
| 9B's | 1,902 | 0.63 / 0.59 |
| Own, condensed to 6 steps by the 9B | 482 | 0.67 / 0.59 |
| Composite adapter / SOLVE adapter as judge, own step format | | 0.61 / 0.61 |

No self-blindness (others' attempts are no easier). Length matters for verbal checking; neither verbal nor latent
checking transfers from curated error benchmarks to the policy's own failure distribution.

## Negative results kept

- Specialist-written hints for always-wrong GRPO problems did not beat a plain "answer X is wrong" hint.
- Writing solutions in a step format cost 6 points of SOLVE accuracy and did not make selection beat majority vote.
- Converting GRPO failures into JUDGE / RECONSTRUCT items was not measurably better than replaying them as SOLVE
  (separate pilot: +1.0 at step 24, CI [−2.8, +4.9]).

## Caveats

One adapter per task (one seed); the transplant result rests on one SOLVE / JUDGE pair. Verdict-level d′ changes from
transplants are not significant; the gains are in verdict production, criterion and localization. ProcessBench scores
use this project's prompt and temperature-1 sampling.
