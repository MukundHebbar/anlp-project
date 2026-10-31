> **Historical handoff (28 October).** The runs were subsequently completed. For current results see
> [the Llama evidence](../../artifacts/baselines/llama3b/README.md) and [completed-run documentation](../../phase2/llama_transfer/README.md).

# Project handoff — 28 October 2026

**Work stopped at the user's explicit request. Do not resume experiments or submit jobs without a new instruction.**

## Goal and deadline

Finish the NLP reasoning cross-task transfer project by **31 October**. Extend the existing Qwen3.5-2B
GRPO transfer study to a model from another family, keeping the historical per-task recipes comparable.
The selected student was **meta-llama/Llama-3.2-3B-Instruct**, one training seed (0), with separate SOLVE,
JUDGE and RECONSTRUCT adapters. Evaluate each selected adapter on all three tasks.

The important project documents are the latest mid-submission document, Phase 2 experiments/report,
and cross-transfer study. Useful repository references:

- `docs/reports/mid-submission/mid_submission.pdf`
- `docs/reports/2026-10-08-grpo-transfer-report.md`
- `docs/design/reasoning-transfer-study.md`
- `phase2/docs/` and `docs/reports/phase2-full-report_yashas.md`
- Historical actual training configs: `docs/reports/latex/configs/{solve_new,judge,reconstruct}.json`

## Current branch and source state

- Local branch: **phase2-failure-driven**, HEAD **c71f10bbde8e91fd48db0eb0cb36b106412d4336**.
- No branch switch, commit, merge or push was performed during the Llama preparation.
- There were already **14 modified tracked files**, plus many untracked experiment/result files, before
  this preparation. Those existing changes were preserved. More changes/new files were added afterward.
- Based on cached refs, HEAD is ten commits ahead of `origin/grpo-transfer-2026-10`, and two commits
  behind `origin/phase2-experiments`: `c468e78` and `f7f419a`. These refs were not freshly fetched.
- The newer phase2 commits add analyses/results. They were not merged into the dirty working tree.
- Historical calibration files matched the original transfer branches; their last source-changing commit
  was `a49610c19964be02a7a3fa1004bf22728500836e`.
- `phase2/llama_transfer/provenance.json` records an **uncommitted file-hash snapshot**, not a Git commit
  containing all new work. Previous runs also saved their own `code-provenance.json`.

## Decisions already authorized

- Student: **meta-llama/Llama-3.2-3B-Instruct**, pinned revision
  `0cb88a4f764b7a12671c53f0838cd831a0843b95`.
- **Gemma 4 12B supplies training rewards**, replacing the broken Jev service. The user accepted the
  measured reconstruction limitations after calibration.
- **Qwen/Qwen3.8-27B remains the final evaluator**, matching the original Qwen study.
- No new Jev or DeepSeek calibration calls: reuse saved requests and DeepSeek reference scores.
- Keep calibration economical. Do not repeatedly manually poll downloads/jobs.
- Hugging Face adapter archive is public; **exclude OPD-trained adapter weights**. OPD-era response
  examples used as calibration references are separate from those weights.
- Official Llama gated-model access eventually succeeded; weights downloaded and were checksum verified.

## Calibration results

Gemma model: `google/gemma-4-12B-it`, revision
`707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7`.

Full calibration job **52402** completed in **9m17s**: **1,947 requests / 4,252 rubric questions**,
zero extraction failures with explicit allowed-label probabilities. Same saved rubric inputs, original
four-checkpoint fit/four-checkpoint evaluation split, threshold grid and quadratic weighted kappa recipe.

| Held-out metric | Gemma | Qwen27B, matching responses |
|---|---:|---:|
| JUDGE calibrated total Pearson r, n=176 | 0.929929 | 0.937946 |
| RECONSTRUCT calibrated total Pearson r, n=241 | 0.778055 | 0.802953 |

Gemma RECONSTRUCT **continuous training reward** correlation is **0.762641**. Continuous rubric-only
correlation on the 232 reference non-shortcuts is **0.792176**, versus Qwen **0.840035**.
Gemma caught **3/9 shortcuts**, with **one false positive**. Production scoring and manual aggregation
matched exactly. Low allowed-label probability mass remains a reliability concern even when extraction succeeds.
These results measure the original one-token protocol, not the model's best possible prompting performance.

Calibration examples are historical/test-derived, and held out by **checkpoint, not question**.
The user explicitly authorized reuse of that recipe. Do not describe them as an untouched-question test.

Results: `phase2/results/local-judge-calibration/gemma-full-explicit/` and
`phase2/results/local-judge-calibration/qwen27b-full-matched/`.

Earlier Selene failed as a drop-in reconstruction judge: its shortcut gate falsely zeroed every held-out
answer. The initial small Gemma screen had 48 planned held-out responses/task, but only 40 valid RECONSTRUCT
responses because top-20 extraction failed. Its initially optimistic small-sample result was superseded by
the full calibration above.

## Frozen training plan

| Arm | LR | Questions/update × rollouts/question | Updates | Warm-up | Rollouts |
|---|---:|---:|---:|---:|---|
| SOLVE low LR probe | 1e-5 | 32 × 8 | 8 | 5 | asynchronous |
| SOLVE high LR probe | 2e-5 | 32 × 8 | 8 | 5 | asynchronous |
| SOLVE full run | select from probes | 32 × 8 | up to 106 total | 5 | asynchronous |
| JUDGE | 5e-5 | 8 × 8 | 104 | 0 | synchronous |
| RECONSTRUCT | 5e-5 | 8 × 8 | 104 | 0 | synchronous |

- Seed 0. BF16; native Llama instruct chat.
- LoRA rank 64, alpha 64, dropout 0; q/k/v/o/gate/up/down projections.
- AdamW betas (0.9,0.999), weight decay 0, gradient clip 1.
- Dr. GRPO: reward minus group mean, **no standard-deviation scaling**, constant 16,384-token
  normalization, importance sampling cap 2, KL coefficient 0.
- Sampling T=1, top_p=1, top_k disabled; training output cap 16,384.
- RECONSTRUCT drops truncated rollouts; SOLVE/JUDGE retain them with zero reward.
- Reuse original `opd.matrix_prompts` order and the disjoint **200-item dev slice**.
- Compare probe step-8 adapters using **200 dev questions × 4 samples** and strict correctness; prefer
  lower LR on an exact tie. Test results must not choose the LR.
- Full SOLVE config currently contains provisional 1e-5. If 2e-5 wins, the full-run config/runner needs to
  use it explicitly. Continue the selected step-8 checkpoint with optimizer state, rather than restart.
- JUDGE/RECONSTRUCT dev selection among checkpoints 26/52/78/104; SOLVE rolling-reward candidates
  confirmed on dev. Final evaluation uses Qwen27B on the cross-task matrix.
- The Gemma reward substitution differs from historical Qwen training with Jev and must be disclosed.

## What actually completed

1. **Official Llama download:** verified **6,434,740,971 bytes**. Master copy:
   `/tmp/mukund-anlp-llama-transfer/llama`; node08 copy:
   `/scratch/mukund.hebbar/llama-transfer/models/llama`.
2. **Integration smoke 52422:** completed in **8m39s**, including an actual Llama update, positive
   gradient/update signal, and runtime adapter reload. Gemma server/client comparison also passed the
   revised scoring checks described below.
3. **Untrained baseline 52424:** completed in **34m53s**. Generated all three tasks; SOLVE uses
   400 test items × 4 samples, JUDGE/RECONSTRUCT one sample each. Local collected outputs:
   `local/llama-transfer/baseline/`.
   **Strict mean SOLVE accuracy was calculated as 9.0%.** This is substantially weaker than the saved
   Qwen3.5-2B baseline (52.625%) and Ministral baseline (27.5625%) on the shared protocol. Do not claim
   Llama matched Qwen's starting math performance. Final Qwen rubric judging of Llama baseline outputs
   has not been established as completed.
4. **Low LR training:** all **8 updates completed**, final mean rollout length ~1,671, no truncation in
   step 8, eight-step mean training reward **0.0737**. The adapter **and optimizer state** were saved.

Preserved low-LR run (node08-local path):

`/scratch/mukund.hebbar/llama-transfer/runs/llama3b-probes-20261028/solve-probe-low/`

Important files: `result-0.json` (`ok=true`, `steps_done=8`), `metrics.jsonl`, `events.log`,
`adapters/step8/adapter_model.safetensors`, `adapters/step8/adapter_config.json`,
`adapters/step8/optimizer.pt`. Read from the master using `/scratch/node08/` instead of `/scratch/`.

## Failures and latest exact state

| Job | Outcome |
|---|---|
| 52419 | First smoke failed before Llama training: one individual label probability differed by 0.034343, above the initial 0.03 tolerance. |
| 52422 | Revised smoke passed. |
| 52424 | Baseline completed. |
| 52425 | Failed at internal timeout after 2h55m (exit 124). Low-LR training finished after ~43 minutes, but its interpreter hung on shutdown; dev evaluation and the high-LR run never began. |
| 52596 | Recovery failed in one second (exit 127): portable Python binary was missing on node08. No training/evaluation progress. |
| 52637 | CPU-only runtime repair: Python restored from own home; packages restored from own node07 copy; Transformers 5.16.0 restored into own wrapper environment. Import/version check printed `RUNTIME_VERIFIED`. Allocation canceled after repair. |
| 52638 | CPU-only broader preflight failed: staged repository is missing `src/anlp_project/qwen_judging.py`. This is the **latest unresolved failure**. |

**No full-length training run has started. No high-LR probe or completed LR selection is established.**
At the last inspected probe state, no `dev-low` outputs existed; the only training result was low LR step 8.
The later recovery failed before reaching evaluation.

The local submission helper was edited/uploaded to name the next probe attempt `-r3`, with two GPUs and a
two-hour reservation. **That next GPU job was NOT submitted**: broader preflight failed first, and the user
then stopped this work. Do not mistake an uploaded submission helper for a submitted job.

The missing Python binary and missing package/source files show that staged scratch contents cannot currently
be assumed complete. **The deletion mechanism was not established.** Do not label it proven automatic scratch
cleanup or a GPU fault. Restored runtime imports passed, but full staged-code/model/checkpoint preflight did not.
The model and step-8 adapter filenames were present in earlier checks; the latest preflight failed before
finishing its model/checkpoint validation.

## Changes made and testing limits

- `src/anlp_project/student_models.py`: Llama causal LM loading/native EOS handling; preserve Qwen handling.
- `src/anlp_project/gemma_judging.py`: exact calibrated allowed-label IDs, tokenized prompts without duplicate
  BOS, explicit unmasked log probabilities, source identity checks and typed rubric answers.
- `src/anlp_project/opd_train.py`: student-family loading/termination and Gemma reward selection. This file
  already had unrelated uncommitted changes; preserve them.
- `src/anlp_project/rewards.py`: use the reward client's calibration for RECONSTRUCT diagnostics. Training
  remains the existing continuous reward; this file also had pre-existing modifications.
- `scripts/modal_opd.py`: ship the new student helper for the existing flat-module import path.
- `phase2/llama_transfer/`: configs, downloader, runner, staging/submission, smoke, probes, local background
  collector/orchestrator, README, provenance snapshot.
- `tests/test_llama_transfer.py`: five compatibility/config/HTTP contract tests.
- `tests/test_llama_probe_shutdown.py`: two actual subprocess regression cases: bounded teardown after a
  completed result, and rejection of exit without a completed result.

CPU checks passed: five compatibility tests, five existing reward tests, seven mixed-GRPO tests (including
train/dev separation), one instruct evaluation regression test, and Python compilation. GPU smoke was only
one update; **it did not test the full eight-step training-to-dev handoff**, which later failed.

The updated probe supervisor uses a separate process group, bounds teardown after a valid eight-step result,
and kills only its own training/engine process group. It skips a completed low-LR run and any completed dev
stage, requires the step-8 adapter, and computes strict dev accuracy from `correct_strict`, not the raw summary.
**That fix passed subprocess regression tests but has not completed a real recovered probe pipeline.**

The revised Gemma smoke logs full expected/actual answers. Numeric rubric expected scores must stay within
1% of their range; categorical/noul questions require <=0.03 probability drift and the same decision. The
first smoke's 0.034343 label discrepancy was not proven to arise from batching. Its evidence is preserved in
`local/llama-transfer/smoke-failed-52419/`.

## Cluster/account/runtime details

- SSH: `mukund.hebbar@turing.iiit.ac.in`; Slurm account `priyesh.shukla`, partition `u22`.
- Node08 was used; node14 avoided for reported GPU faults, node04 excluded per user instruction.
- Maximum six assistant GPUs including queued reservations. Use existing ledger/launcher, not untracked jobs.
- Master control repo: `/home/mukund.hebbar/anlp-project-grpo` (export, no Git metadata).
- Isolated node08 repo: `/scratch/mukund.hebbar/llama-transfer/repo`.
- Runtime Python: `/scratch/mukund.hebbar/ministral-baseline/python/bin/python3.12`.
- Wrapper: `/scratch/mukund.hebbar/failure-driven/venv`; package copy under
  `/scratch/mukund.hebbar/yashas-anlp-env/venv/lib/python3.12/site-packages`.
- Verified imports after repair: vLLM 0.30.0, Transformers 5.16.0, PEFT 0.21.1, torch 2.13.0+cu129.
- Node08 does not mount this account's home; do not rely on home paths inside its jobs.
- Ledger: `artifacts/opd/turing/turing_budget.json` in the master control repo; total approved cap 500 GPU-hours.
  Latest displayed remaining budget was **2.775 GPU-hours while the six-hour recovery reservation was still
  outstanding**. That recovery failed immediately, so reconcile before treating this as available balance.
  No budget cap increase was made. Full runs may need more budget than remains.
- Credentials are in local `.env`; **never copy it into exports, manifests or public repositories**. Tokens
  were passed via stdin, not command-line arguments. This handoff contains no token.

## Why shutting down the laptop was not the cause

The Slurm probe job ran on Turing independently of the laptop. Its training/shutdown hang and the later missing
runtime were cluster-side problems. Local collectors could pause on laptop shutdown, but that did not stop the
original submitted job. The reassurance about unattended progress was too broad: full training was not queued,
and the complete training-to-evaluation handoff had not been validated.

## Remaining work, only if a future operator is authorized

1. Inspect/reconcile actual cluster jobs and budget. Do not assume local background scripts are alive.
2. Restore/verify the **entire isolated staged code and environment**, including the missing Qwen judge helper
   used by Gemma. Compare against local provenance; verify student weights and saved adapter/optimizer.
   Local `local/llama-transfer/code.tar` and master `/tmp/mukund-llama-code.tar` are earlier explicit code/data
   exports; later fixes must be overlaid deliberately. They are not guaranteed to contain the latest fixes.
3. Validate the real training process teardown/evaluation handoff with the preserved checkpoint; do not repeat
   the completed eight low-LR updates. Avoid another expensive allocation without a fresh environment preflight.
4. Evaluate low LR on 200 dev ×4; train high LR eight updates and evaluate identically; save LR selection.
5. Address budget before full training. Resume the chosen SOLVE probe with its optimizer and selected LR;
   run the JUDGE and RECONSTRUCT arms, perform dev checkpoint selection and final cross-task evaluation.
6. Collect/curate results and checkpoints, document the weak Llama baseline and reward-judge change, and
   update the final project report. Do not claim all training/results exist.

## Other project work and artifact locations

- Public non-OPD adapter archive: `https://huggingface.co/ransom32/anlp-reasoning-transfer-adapters`.
  Archive code/results: `phase2/adapter_archive/`, `phase2/results/adapter-archive/`. Earlier uploads included
  headline GRPO and all six mixed-control endpoints; verify final manifest for completeness. Some historical
  scratch checkpoints were already missing. Do not claim every historical adapter survived.
- Earlier missing mixed-control evaluation was recovered under `phase2/results/mix-control/`.
- Ministral baseline completed previously under `phase2/results/ministral-baseline/`. Its weights were not
  confirmed deleted, despite the earlier deletion request.
- Relevant local logs: `local/llama-transfer/{download.log,background.log,background-r2.log,runtime-repair.log}`.
- Master Slurm logs: `/scratch/node08/mukund.hebbar/llama-transfer/slurm-<jobid>.out`.
- `phase2/llama_transfer/README.md` contains earlier chronological notes. **This handoff supersedes its older
  status statements where they differ.**
