# Transfer study status report and end-to-end runbook

Date: 2026-10-07. Model: `Qwen/Qwen3.5-2B` (post-trained, non-thinking). Data: FINAL-v3. This report covers
everything run so far, the current SOLVE work, and how to run the whole pipeline from scratch.

## 1. The study in one paragraph

We train Qwen3.5-2B on one task at a time and measure it on all three:
- **SOLVE**: solve a DeepMath problem; the final answer is checked.
- **JUDGE**: decide whether a worked solution is correct and name its first wrong step.
- **RECONSTRUCT**: recover the question from a final answer plus clues.

Each task has 4,000 rows (from DeepMath-103K): 3,600 train (a 200-question dev slice is held out, leaving 3,400 to
train on) and 400 test. The main result is a 3×3 transfer matrix of Δ against the untrained model on each test
set. GRPO, as **Dr. GRPO**, is done. On-policy distillation (OPD) from Qwen3.5-9B is postponed.

## 2. What has been run

### 2.1 Judges

| Role | Judge | How it was validated |
|---|---|---|
| SOLVE answer check | Deterministic checker, no LLM (`solution_verification.py`; v3 since 2026-10-07, §2.6) | Audited on 7,465 answer pairs |
| JUDGE verdict and step | Deterministic parser + strict gates | — |
| Training reward and dev scoring for JUDGE explanation and RECONSTRUCT | **Jev** API (`jev-1.13.0`, `jev_judging.py`): gate → few-shot shortcut stage → calibrated questions | Against DeepSeek on 500 answers. Its agreement with DeepSeek on total scores is about the same as the 27B's |
| Final test judge for JUDGE V/L/E/M and RECONSTRUCT PC-v4 | **Qwen3.8-27B**, logit-reading (`qwen_judging.py`, `calibration-qwen27b-v1.json`) | Against DeepSeek: JUDGE r 0.940, RECONSTRUCT r 0.840 |

The two judges differ on purpose: a checkpoint is never selected and finally scored by the same judge.

**Strict gates** (`strict_gates.py`) are applied before any score or reward; a failed gate scores 0:
- SOLVE: disagreeing `<final_answer>` tags;
- JUDGE: several or contradictory decisions or steps;
- RECONSTRUCT: answer written into the question, monologue or drafting, no question.

The student prompts are v2: one final block, a brevity line, and the gate rules stated.

### 2.2 Baselines (test, 4 samples per question, pass@1 = mean over samples)

| Metric | Qwen3.5-2B | Qwen3.5-9B |
|---|---:|---:|
| SOLVE accuracy (checker v2 / **v3**) | 51.0 / **52.6** | 79.8 |
| SOLVE pass@4 | 77.8 | 89.2 |
| JUDGE verdict | 64.3 | 87.6 |
| JUDGE step (incorrect solutions) | 34.8 | 87.9 |
| JUDGE V/L/E/M (27B) | 53.9 | 85.7 |
| RECONSTRUCT PC-v4 (27B) | 40.1 | 72.7 |
| RECONSTRUCT same question | 2.9% | 19.6% |

Full tables: `artifacts/baselines/final-v3/v3-report/baseline-pass4.md`.

### 2.3 Dr. GRPO transfer matrix (2026-10-06/07)

**Configuration** (`opd.GRPO_CONFIG`):
- advantage = reward − group mean (no ÷ std); loss = token sum / 16,384;
- β 0, LoRA r64, AdamW lr 5e-5 constant, grad clip 1.0;
- 8 questions × 8 answers per step, T 1.0, 16k cap, truncated answers kept with reward 0;
- 104 steps, about 55 GPU-h on at most 6 L40S GPUs;
- checkpoint chosen on the arm's own dev slice among steps 26/52/78/104.

**Rewards:**
- SOLVE: 1 for a verified correct answer, else 0.
- JUDGE: 0 for a wrong verdict; else 0.5 + 0.25 for the right step + 0.25 · Jev(E+M)/8.
- RECONSTRUCT: Jev staged score / 100, −0.1 for several drafts.

**Results (test, Δ against the untrained 2B, paired 95% CI):**

| Trained on → | SOLVE acc | JUDGE step % | JUDGE false alarm % | JUDGE Youden J | RECON PC-v4 |
|---|---:|---:|---:|---:|---:|
| SOLVE (step 104, old recipe; superseded by §2.9) | **−2.2 [−5.7, +1.0]** | −3.2 | −18.8 | +1.4 | −6.7 |
| JUDGE (step 26) | −0.8 | **+17.2 [+10.2, +24.0]** | **−24.2** | **+28.4** | +6.0 |
| RECONSTRUCT (step 104) | −10.6 | +14.2 | +10.2 | +7.9 | **+21.4 [+19.1, +23.5]** |

**JUDGE headline metrics** (user decision): step %, false-alarm rate and Youden's J. Combined accuracy rewards
answering "correct", so it is shown only next to the per-label split.

**Reading the matrix:**
- JUDGE and RECONSTRUCT gain strongly on their own tasks.
- **SOLVE does not.**
- RECONSTRUCT's JUDGE step gain comes with more false alarms, because it calls most solutions incorrect.
- Report: `artifacts/baselines/final-v3/v3-report/grpo-matrix.md`.

### 2.4 Why SOLVE failed (diagnosis from the 6,656 training rollouts)

- **Little signal per step.** Questions whose 8 answers got different rewards fell from 5.6 to 3.5 of 8 per step,
  and only 28 of 64 rollouts still produced a gradient by the end. With lr 5e-5, each update was a large, noisy
  step from about 3 questions.
- **More finished but wrong answers.** Wrong answers rose from 23% to 33%. Truncation fell from 10% to about 2%, but
  the answers that used to be cut off now finish wrong.
- **Under-used data.** The run saw 832 of 3,400 training questions, each once. Run length was set by time, not
  data.
- **Not the main cause:** the reward formula (a binary verified reward is standard) and the length cap (16k covers
  99.3% of the base model's correct answers).
- **Minor:** about 16% of rollouts were "unverified" by the checker and earned 0. Most are really wrong; a few are
  right in an unusual form (fixed in v3).

### 2.5 Comparison with published recipes

| | lr | Questions/step × answers | Other |
|---|---|---|---|
| DeepMath-1.5B (official, same data source) | 1e-6 full FT | 128 × 16, refills all-same groups | KL 0.001, T 0.6, 24k + overlong penalty |
| Typical LoRA RL ("LoRA without regret") | ~1e-5 | 32–512 | — |
| Our first SOLVE run | 5e-5 LoRA | 8 × 8 | — |

### 2.6 SOLVE checker v3 (2026-10-07)

`solution_verification.compare_answer_detailed`, used by the reward, the evaluations and the gates, now
applies the following layers in order. The first four can only turn an answer into "correct":

1. The original rules (normalised exact match, booleans, exact arithmetic, SymPy), with notation fixes: `≥`
   variants, `\bmod`, `\ln 2`, `+\infty`, degrees, `\sqrt[n]{}`, `|x|`, true/false ↔ yes/no.
2. The rules on cleaned forms of the answer:
   - `n = 2^k`, `(p, q) = (2, 2)`, `x=0, y=0, z=0`, `2^k \text{ for } k ≥ 1`;
   - a cleaned form must be pure mathematics, and a removed part may not contain hedge words (or, not, maybe…).
3. Numeric closeness:
   - exact numbers must be equal exactly;
   - a decimal key with 4 or more decimals fixes the precision;
   - infinities are never compared numerically.
4. **DeepMath's official checker pair**: OpenMathInstruct `math_equal` (vendored in `third_party/`; tolerance
   tightened from 1e-4 to 1e-9 because 1e-4 accepted 88327 for 88329), then **math-verify**. Both only see
   pure-maths answers that do not list more values than the key.
5. A hard 10 s limit per check: an alarm in the main thread, a process pool when called from trainer threads.

**Audit on 7,465 distinct (key, answer) pairs:**
- 161 unverified and 8 wrong answers became correct, each checked by hand;
- 1 answer lost "correct": `z ∈ iℝ … or z = 0` for 0, a hedge;
- false positives found during the audit are now regression tests (`tests/test_solution_verification.py`).

**Effect:** the untrained 2B scores 52.4% on dev and 52.6% on test (+1.6–2.2 points). Old results were re-scored
with `scripts/rescore_solve.py`; the first rewrite keeps a `scores.v2.jsonl` backup.

### 2.7 In progress: SOLVE probes (round 1, started 2026-10-07 05:26 UTC)

These are short runs to validate that a lower lr with larger batches learns where 5e-5 × 8 questions did not.
Everything else is unchanged: Dr. GRPO, 16k cap, T 1.0, binary reward with checker v3, and **no difficulty
filtering** (user decision).

| Run | lr | Batch | Warm-up | Dev check |
|---|---|---|---|---|
| `solve-p1-lr1e-5` | 1e-5 | 32 × 8 | 5 steps | steps 10, 20 (200 dev × 4) |
| `solve-p1-lr2e-5` | 2e-5 | 32 × 8 | 5 steps | steps 10, 20 |

**Reference points:**
- untrained 2B dev: **52.4%** (v3 checker);
- the old run's dev: 45.6 at step 26 (old checker, base 50.2 then);
- success means dev at or above base at step 10–20, with a rising training reward.

The GPU cap was lowered to 4 during round 1, so:
- the lr 5e-5 control (same 32 × 8 batch) was cancelled after 2 steps;
- both probes were stopped at step 8.

**Round 1 results (step 8, 256 questions seen; dev 200 × 4, paired against the untrained 2B):**

| Checkpoint | Dev accuracy | Δ (95% CI) |
|---|---:|---:|
| Untrained 2B | 52.4% | — |
| **lr 1e-5, step 8** | **56.1%** | **+3.8 [−0.2, +7.6]** |
| lr 2e-5, step 8 | 56.2% | +3.9 [+0.2, +7.5] |
| Old run (lr 5e-5, 8 × 8), step 26 | 47.9% | −4.5 |

**Decision: lr 1e-5.** The two lrs tie on dev, and a tie goes to the literature value. The larger batch turned the
early dev trend from −4.5 to +3.8.

### 2.8 The full SOLVE run (running since 2026-10-07 13:40 IST)

**Recipe:** Dr. GRPO, LoRA r64, lr 1e-5 (5-step warm-up), 32 × 8, T 1.0, 16k cap, checker v3, β 0, all training
questions, one pass = 106 steps.

**Two additions:**
- **Overlapped rollouts** (`async_rollouts`): step s+1's answers are generated while step s trains. The
  rollouts lag the trained policy by one update, and the capped IS ratio corrects for it. Step time went from
  ~15 to ~9 min; the vLLM/trainer log-prob gap is unchanged at 0.011.
- **Best-by-reward checkpoints** (`best_window=8`, `best_keep=3`): the 3 adapters with the highest 8-step rolling
  mean training reward are kept in `adapters/best-step<k>`. In a first pass every step's questions are unseen,
  so this measures accuracy on new questions.

**No early stopping.** Training runs to step 106 or a manual stop.

### 2.9 Result: SOLVE GRPO works (2026-10-07, final)

**Run and checkpoint choice:**
- The user stopped training at **step 79** (2,528 questions seen; ~15 GPU-h of training).
- Final model: **step 66**, the best by 8-step rolling training reward (0.691, up from 0.53 at the start).
- Dev check for step 66: **72.4% vs 52.4%, +20.0 [+15.9, +24.1]**.
- No dev or test question appears in the 3,392 training prompts.

**Test, Δ against the untrained 2B (paired, 95% CI); SOLVE pass@1 over 4 samples; JUDGE and RECONSTRUCT with 1 sample,
judged by the 27B:**

| Trained on → measured on | SOLVE acc | SOLVE pass@4 | JUDGE step % | JUDGE false alarm | JUDGE Youden J | JUDGE V/L/E/M | RECON PC-v4 |
|---|---:|---:|---:|---:|---:|---:|---:|
| SOLVE, old run (lr 5e-5, 8 × 8) | −2.2 | −7.8 | −3.2 | −18.8 | +1.4 | +4.1 | −6.7 |
| **SOLVE, new run (lr 1e-5, 32 × 8, step 66)** | **+16.6 [+13.8, +19.1]** | **+7.2** | **+8.8** | **−13.8** | **+15.4** | **+9.0** | **+3.8** |
| JUDGE (step 26) | −1.1 | −4.2 | +17.2 | −24.2 | +28.4 | +18.3 | +6.0 |
| RECONSTRUCT (step 104) | −10.7 | −14.0 | +14.2 | +10.2 | +7.9 | +1.8 | +21.4 |

**Reading the table:**
- SOLVE accuracy: **52.6% → 69.2%**; pass@4: 80.2% → 87.5%.
- **The new SOLVE arm is the only arm that transfers positively to every other task.** On JUDGE it improves both
  error finding (step % +8.8) and false alarms (−13.8); RECONSTRUCT rises +3.8.

**Where the SOLVE gain comes from (test):**
- correct 52.6 → 69.2%;
- wrong 20.8 → 15.6%;
- unverified 16.2 → 12.6%;
- gated 6.8 → 1.4%;
- no answer 3.6 → 1.3%;
- mean length 8.1k → 8.6k tokens.

So it is about 6 points of format and 10 points of correctness.

**Files:**
- answers: `artifacts/baselines/final-v3/test/v3-grpo-lr1e-5-solve-step66`;
- training log: `artifacts/opd/evals/solve-p1-lr1e-5/` (`train-metrics.jsonl`, `best.json`, `config.json`);
- adapter on node11 scratch: `v3/solve-p1-lr1e-5/adapters/best-step66`;
- frozen copy: `~/anlp-project/runs-out/solve-lr1e-5-step66-adapter`.

**Consistency fix:** all SOLVE numbers in the matrix (base and every arm) now use checker v3. The old arms were re-scored
with `scripts/rescore_solve.py`, so their SOLVE Δ differ slightly from §2.3: JUDGE arm −0.8 → −1.1, RECONSTRUCT arm
−10.6 → −10.7.

**Compute:** the GPU ledger shows 211 GPU-h used of 500 in total (all work so far). Never more than 4 GPUs at once since
2026-10-07.

**What the pipeline would have done after training** (`scripts/solve_grpo_pipeline.sh`, unattended):
1. dev-evaluates 3 candidates: best by reward, best every-8 checkpoint by reward, last step;
2. picks the best on dev;
3. evaluates it on all three test sets;
4. runs the 27B judge, calibration and the transfer-matrix report.

## 3. End-to-end runbook

Commands are run from the repository root. Turing jobs are submitted from the login node with
`scripts/turing/launch.py`, which:
- keeps the GPU ledger (`artifacts/opd/turing/turing_budget.json`);
- refuses to go over **4 GPUs at once**.

Outputs go to node scratch, `/scratch/mukund.hebbar/anlp-opd/v3/<run>` (seen from the login node as
`/scratch/nodeXX/...`). The 50 GB home directory is for code and small records only.

### 3.0 One-time setup

```bash
uv sync                                                      # local env (math-verify included)
rsync -aq --exclude __pycache__ src scripts tests pyproject.toml turing:anlp-project/
sbatch -w node11 scripts/turing/setup_env.sbatch             # per node: venv + model cache on scratch
echo "JEV_KEY=..." >> .env                                   # Jev (JUDGE/RECONSTRUCT rewards, dev scoring)
```

Checker packages on an existing node venv (pure Python, copied from the workstation):

```bash
uv pip install --target /tmp/mv --python-version 3.12 --no-deps \
    math-verify==0.9.0 latex2sympy2_extended==1.11.0 antlr4-python3-runtime==4.13.2
rsync -a /tmp/mv/ turing:/scratch/node11/mukund.hebbar/anlp-opd/venv/lib/python3.12/site-packages/
```

### 3.1 Baselines (pass@4 on test)

```bash
python3 scripts/turing/launch.py submit --name base-2b --gpus 2 --hours 4 --node node11 -- \
  python scripts/turing/eval_matrix.py --name base-2b --split test --samples 4 --out {out}
# 27B judging of JUDGE + RECONSTRUCT answers, then calibrated scores and the report:
python scripts/turing/qwen_judge_run.py --eval-dir test:<eval dir>/s0 --out <log dir>/answers.jsonl   # 2 GPUs
uv run python scripts/qwen_judge_calibration.py score <eval dir>/s0
uv run python scripts/report_passk.py artifacts/baselines/final-v3/test/<eval dir>
```

### 3.2 Dr. GRPO training (one arm, 2 GPUs: vLLM rollouts + trainer)

```bash
python3 scripts/turing/launch.py submit --name <run> --gpus 2 --hours <h> --node node11 -- \
  python scripts/turing/opd_run.py --task <solve|judge|reconstruct> --config grpo --steps <n> \
    --keep-steps <k1,k2,...> --set prompts_per_step=32 --set optimizer.lr=1e-5 \
    --set optimizer.warmup_steps=5 --student-port <free port> \
    --out /scratch/mukund.hebbar/anlp-opd/v3/<run>
```

- Any config key can be overridden with `--set key=JSON`.
- Each step logs one line to `<run>/metrics.jsonl`: reward, mixed groups, length, truncation, timing.
- `<run>/rollouts/step<k>.jsonl` holds every answer with its reward.
- Size runs by data: questions seen = prompts_per_step × steps; one pass over 3,400 at 32 per step is about 106
  steps.

### 3.2b The SOLVE recipe end to end (one command, from the workstation)

```bash
nohup bash scripts/solve_grpo_pipeline.sh > artifacts/opd/evals/solve-pipeline.log 2>&1 &
# stop training by hand: ssh turing scancel $(cat artifacts/opd/evals/solve-p1-lr1e-5/train_job)
```

The script runs training chunks (resuming from the newest optimizer state), then candidate dev evals, selection,
test, 27B judging and the report, never using more than 4 GPUs.

### 3.3 Dev selection → test → 27B judging (per arm)

```bash
python3 scripts/turing/launch.py submit --name <run>-post --gpus 2 --hours 6 --node node11 --after <train job> -- \
  bash scripts/turing/drgrpo_post.sh <task> <run>
bash scripts/drgrpo_finalize.sh       # local: pull results, apply 27B calibration, build grpo-matrix.md
```

`drgrpo_post.sh`:
1. dev-evaluates steps 26/52/78/104 on the arm's own task;
2. selects the best by the fixed rule (ties go to the later step);
3. test-evaluates the selected step and step 104 on all three tasks;
4. runs the 27B judge.

### 3.4 Reports

```bash
uv run python scripts/rescore_solve.py <eval dirs>   # after any checker change (SOLVE rows only)
uv run python scripts/report_grpo_matrix.py           # transfer matrix + JUDGE per-label table
uv run python scripts/report_passk.py <eval dirs>     # pass@1 / pass@4 tables
uv run python -m unittest discover -s tests           # 222 tests
```

### 3.5 Rules that keep the numbers honest

- **The same checker and judges for every compared number.** After a checker change, re-score everything (§3.4).
- **Checkpoints are chosen on dev only.** Test is evaluated once per selected checkpoint.
- **Jev only where required:** training rewards and RECONSTRUCT dev scoring.
- **Test sets use the 27B.**
- **At most 4 GPUs at once** (since 2026-10-07). No new Turing runs without the user's go-ahead.

## 4. Open items

1. ~~SOLVE~~ **done** (§2.9): +16.6 on test with lr 1e-5 and 32 × 8.
2. **Optional:** CompassVerifier-3B for answers the checker leaves unverified (needs a validation job).
3. **OPD arms** (postponed).
4. **Nothing from 2026-10-06/07 is committed yet.**
