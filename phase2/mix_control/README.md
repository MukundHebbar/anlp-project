# Is there transfer into SOLVE under co-training? A SOLVE-only control for the mixed run

**Question.** The Phase-1 mixed model (⅓ SOLVE + ⅓ JUDGE + ⅓ RECONSTRUCT, step 75; transfer report §7b) saw only
750 SOLVE questions but matches the SOLVE specialist that saw 2,112 (test 69.8 vs 69.2). SOLVE-only arm A of the
failure-driven pilot reached only 59.9 on dev after 768 SOLVE questions. But the mixed run also took 3× more optimizer
steps (75 vs 24) at twice the learning rate (2e-5 vs 1e-5), so the existing runs cannot tell whether the JUDGE /
RECONSTRUCT data helped SOLVE or the steps and learning rate did.

**Control.** The mixed run's exact command (`artifacts/opd/evals/mixed-lr2e-5/submits.log`) with its JUDGE and
RECONSTRUCT prompts removed (`build.py`): every one of its batches held exactly 10 SOLVE + 10 JUDGE + 10 RECONSTRUCT
prompts, so the control trains on the same 750 SOLVE prompts in the same steps and order, 10 per step, for 75 steps;
lr 2e-5 (5 warm-up steps, then constant), async rollouts, 8 samples, 16k cap, Dr. GRPO, LoRA r64 (`scripts/train.sh`).
Two seeds (0, 1: rollout sampling seeds), because one run of an arm can be off by about 3 points (failure-driven
README: D2 repeated). The mixed step-75 adapter (`~/anlp-opd-shared/grpo/mixed75`) is re-evaluated with the same
evaluation in the same environment. Trainer code changes since the mixed run (prompts-file, extra answer keys, the
reward judge option, seeds, a guard against a checker hang) do not change SOLVE-only training at seed 0.

**Validation.** SOLVE dev (200) + `phase2/failure_driven/data/val_uids.json` (200), minus the 750 SOLVE questions
both arms trained on (51 of val200 are among them) and the reworded test duplicates; 4 samples, the matrix protocol.

**Decision rule** (`decide.py`, fixed 2026-10-25 10:26 UTC, sha256 2002ee57..., before any control result): the
JUDGE / RECONSTRUCT data helped SOLVE if mixed - mean(control seeds) > 0 with the 95% interval above 0 on avg@4 AND
mixed is above each control seed. The SOLVE test set is evaluated once, after the decision.

| File | Role |
|---|---|
| `build.py` | the control's 750 prompts from `opd.mixed_prompts(1134)` |
| `scripts/train.sh` | one control run (2 GPUs) |
| `scripts/run.sh` | local driver: train, then dev + val200 evals |
| `decide.py` | decision rule |

## Run log

| Run | Node | Jobs |
|---|---|---|
| ctrl-s0 (seed 0) | node04 | 50662 (75 steps, 4.7 h); evals 51043, 51069 |
| ctrl-s1 (seed 1) | node14 | 50673 (75 steps, 4.75 h); evals 50965, 50983 |
| mixed75 re-evaluated | node04 | 50837, 50862 |

(The drivers' copy-back of the evals failed on a missing local folder; fixed, results pulled by hand.)

## Result (2026-10-26, `decide.py`, validation 348 questions: 199 dev + 149 val200, step 75)

| Arm | avg@4 | pass@4 |
|---|---|---|
| mixed (750 SOLVE + 750 JUDGE + 750 RECONSTRUCT) | **71.0** | 85.3 |
| SOLVE-only control, seed 0 | 63.1 | 83.9 |
| SOLVE-only control, seed 1 | 68.2 | 87.4 |

- mixed - mean(controls): avg@4 **+5.4 [+3.0, +7.8]**; mixed is above both seeds (+7.9 [+5.2, +10.7] and +2.8
  [+0.1, +5.5]) -> **by the pre-set rule, the JUDGE / RECONSTRUCT data helped SOLVE** under co-training.
- pass@4: mixed - mean(controls) -0.3 [-3.0, +2.4]: the gain is in how reliably a question is solved (avg@4), not in
  how many questions are ever solved.
- **Caveat: the two control seeds differ by 5.1 [+2.3, +8.0]** on avg@4 (pass@4 3.4), more than the 2.8 between the two
  D2 runs. The mixed run is a single seed; if its own seed spread is as large, part of the +5.4 could be seed luck.
  A second mixed seed would settle it (it needs the JUDGE / RECONSTRUCT reward judge).
- Training reward on the same SOLVE questions (8-step blocks) was close throughout (e.g. steps 33-40: mixed 0.609,
  controls 0.637 / 0.650); mixed pulled ahead only in steps 65-72 (0.680 vs 0.578 / 0.625). Mixed's SOLVE answers were
  shorter in the middle of training (about 6.0k vs 7-9.7k tokens at steps 17-48).

## Test, once, after the decision (2026-10-26; 396 questions, reworded duplicates excluded; jobs 51242-51244)

| Arm | avg@4 | pass@4 |
|---|---|---|
| mixed | **69.2** | 83.1 |
| SOLVE-only control, seed 0 | 59.5 | 79.0 |
| SOLVE-only control, seed 1 | 66.7 | 85.9 |

mixed - mean(controls) avg@4 **+6.1 [+3.8, +8.5]** (pass@4 +0.6 [-2.3, +3.5]); mixed - seed 0 +9.7 [+7.0, +12.6];
mixed - seed 1 +2.5 [-0.1, +5.2]; seed 1 - seed 0 **+7.2 [+4.5, +9.8]**. Mixed re-evaluated here on all 400 test
questions: 69.1 (transfer report: 69.8), so the two evaluation setups agree.

## What the result does and does not show

- **Shown (validation and test agree):** with the mixed run's steps, learning rate and SOLVE questions, training on
  SOLVE alone gave a lower and much less stable SOLVE accuracy (two seeds 5-7 points apart) than training on SOLVE +
  JUDGE + RECONSTRUCT; the mixed model is above both seeds on avg@4 (on test, above seed 1 by +2.5, interval just
  touching 0).
- **Not yet isolated: content vs step size.** With Adam, each step's size is set by the learning rate; in the mixed
  run that step is shared by three tasks' gradients, in the control it is spent on SOLVE alone. So at the same lr the
  control takes larger SOLVE steps. The JUDGE / RECONSTRUCT data may help through their content (transfer) or by
  diluting and regularising the SOLVE updates; the large seed spread of the controls fits the second reading too.
  This was not anticipated when the control was designed.
- **Single mixed seed.** The control seeds differ by 5-7 points; the mixed run's own seed spread is unknown.
- **Follow-ups that would settle it:** (1) a SOLVE-only control at a lower lr (e.g. 1e-5 and 6.7e-6 = 2e-5 / 3), two
  seeds each: if it reaches mixed, the gain is step size, not transfer; (2) a second seed of the mixed run (needs the
  JUDGE / RECONSTRUCT reward judge: Jev as in the original, or the 27B on 2 more GPUs).

## Follow-up: SOLVE-only controls at lower learning rates (started 2026-10-26)

Tests the step-size reading above. The same control (`scripts/train.sh`, same 750 prompts, 75 steps) at lr 1e-5 and
6.7e-6 (= 2e-5 / 3, the SOLVE share of the mixed run's steps), two seeds each; seed 0 on node06, seed 1 on node07
(node04 not used, at the user's request). Decision rule `decide_lr.py` (fixed 2026-10-26 12:35 UTC, sha256
d41459ca..., before any of these results): transfer by content is supported only if mixed beats the control at
every lr (each by decide.py's rule); otherwise the gain is explained by step size at the lr that reaches mixed.

## Completed lower-learning-rate validation (2026-10-27)

The missing `ctrl-lr1e-5-s1` evaluation is complete. Training job 51700 had already finished all 75 steps;
evaluation job 51980 failed before model loading because its scratch Python environment was incomplete.
After repairing the environment, jobs **52201 (dev)** and **52202 (val200)** completed on **node07**, under
`mukund.hebbar` / account `priyesh.shukla`. No retraining or new test-set evaluation was performed.

Same protocol for all arms: 4 samples per question, T=1, 16k first pass with continuation to 32k, checker v3 and
strict gates. All seven arms have exactly the same **348 eligible questions: 199 dev + 149 val200**, after the
existing training-question and duplicate exclusions.

| Arm | avg@4 (%) | pass@4 (%) |
|---|---:|---:|
| Mixed, step 75 | **71.0** | 85.3 |
| SOLVE-only, lr 2e-5, seed 0 | 63.1 | 83.9 |
| SOLVE-only, lr 2e-5, seed 1 | 68.2 | **87.4** |
| SOLVE-only, lr 1e-5, seed 0 | 62.9 | 83.9 |
| **SOLVE-only, lr 1e-5, seed 1 (recovered)** | **63.1** | **84.2** |
| SOLVE-only, lr 6.7e-6, seed 0 | 62.1 | 84.8 |
| SOLVE-only, lr 6.7e-6, seed 1 | 61.3 | 84.8 |

| Control lr | Mixed minus mean of control seeds, avg@4 (points; 95% CI) |
|---|---:|
| 2e-5 | **+5.4 [+3.0, +7.8]** |
| 1e-5 | **+8.0 [+5.6, +10.5]** |
| 6.7e-6 | **+9.3 [+6.9, +11.8]** |

`decide_lr.py` passes its pre-set rule: mixed is above each seed, and its paired advantage over the mean of the
two control seeds has a positive lower confidence bound at every learning rate. These tested lower learning
rates do not remove the mixed model's avg@4 advantage. This supports a benefit from auxiliary-task co-training
under the tested settings; it does not establish a seed-independent effect or exclude every regularization or
optimization explanation. The mixed model still has only one training seed, and the intervals resample questions,
not training runs. The result concerns mean single-sample accuracy, not a demonstrated pass@4 advantage.

The recovered row alone is dev **63.2 / 85.4** and val200 **63.1 / 82.6** (avg@4 / pass@4, eligible questions).
The [curated results](../results/mix-control/README.md) retain all 11,200 source scores, evaluation metadata,
source checksums, paired question outcomes and the unchanged decision script's output. Full responses for the
recovered run are backed up locally under `local/mix-control/evals/` as `responses-solve.jsonl.gz`.
