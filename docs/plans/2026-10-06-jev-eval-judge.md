# Plan: replace the DeepSeek evaluation judge with Jev

> **Revision (2026-10-06, supersedes the judge roles below):**
> - **Jev** is the *training-time* signal: the GRPO reward (with checkable rewards first) and
>   dev checkpoint selection.
> - **Qwen3.8-27B** (vLLM logit judge) scores the *final* tests.
> - The OPD teacher, if one is used, is Qwen3.5-9B, never the 27B.
> - The student starts from `Qwen/Qwen3.5-2B` (post-trained), as in all existing runs. This was
>   confirmed 2026-10-06 on the literature alone; a base vs post-trained probe was cancelled.
>   - A base start would count shared format learning as cross-task transfer.
>   - Zero-RL at ≤3B is slow and fragile to format and templates (SimpleRL-Zoo, Dr. GRPO,
>     Li et al. 2507.17512).
>   - On-policy distillation recipes start from post-trained or SFT'd students (Qwen3,
>     Thinking Machines, GKD).
>
>   A base-start SOLVE arm stays optional, as an ablation only.
> - The old matrix arms were distilled from the 27B, so they are not compared with new arms under
>   the 27B judge.
>
> Sections 3–4 (Jev rubric questions, calibration against DeepSeek) still apply, because they now
> validate the reward. Section 7's logit-judge build becomes the final judge. Before any GRPO run,
> check that Jev ranks the 8 saved matrix answers per test question like DeepSeek does.

Date: 2026-10-06. Scope: the model-judged evaluation scores (`judge_score` V/L/E/M and
`recon_score` P/T/E/M, plus `recon_same`) that `scripts/judge_baseline.py` produces for
every checkpoint evaluation. Training rewards and the JUDGE *task* are out of scope.

## 1. Where things stand

| Task | Primary metric | Who scores it today |
|---|---|---|
| SOLVE | answer accuracy | deterministic (`solution_verification.compare_answer_detailed`), no LLM |
| JUDGE | verdict accuracy, first wrong step | deterministic parser (`scores.jsonl`) |
| JUDGE | V/L/E/M /100 (secondary) | DeepSeek V4.1 Flash, `judge_eval_p1.md`, 1 call per item |
| RECONSTRUCT | PC-v4 /100 (primary), same-question % | DeepSeek, fidelity (P,T) + validity (E,M,shortcut), 2 calls per item |

So only JUDGE V/L/E/M and RECONSTRUCT P/T/E/M need a new judge. SOLVE is already free.

**Current cost and failure profile** (8 test arms in `artifacts/baselines/final-v3/test/matrix-*`):
about $1.55 per 400+400 test evaluation and $0.25–0.55 per dev evaluation. DeepSeek leaves
**~16% of RECONSTRUCT judgments unresolved** (e.g. base: 63/400 failed validation), and those
items silently drop out of the mean. Calls also hit DeepInfra 429 back-pressure.

**What Jev is** ([docs](https://docs.typesafe.ai/models.md)): TypeSafe System One `jev-1.13.0`.
It takes a state plus typed Score/Choice/Noul questions and returns probabilities and confidence.
It costs $0.042 per M input tokens (output is free), allows 80 requests/s, and has a
**32k-token limit on state + longest question**. "Laya" is not a TypeSafe model; Jev is the only one.
Documented weaknesses ([jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)):
- reads instructions literally
- weak at math and numeric precision ("keep arithmetic in code")
- cannot count
- score expectations are not numerically calibrated between levels
- biased toward the first option in a Choice
- distracted by large, irrelevant state

**Existing evidence** (`artifacts/jev-agreement-v1/`, `scripts/compare_jev_judges.py`, older
Qwen3-4B responses):

| | Total Pearson | 1–5 rating exact | Per-dim κ | Notes |
|---|---:|---:|---|---|
| JUDGE (78) | 0.98 | 92% | V .97, L .97, E .95, **M .75** | M inflated +0.54 |
| RECONSTRUCT (100) | **0.77** | **53%** | **P .41**, T .54, **E .41**, M .78 | shortcut 99% agree; same-question 14 vs 2 |

Measured Jev cost: ~$0.00006 per JUDGE item and ~$0.0003 per RECONSTRUCT item, so about
**$0.15 per test evaluation (~10× cheaper)**, with no unresolved outputs.

**Conclusion.** Jev can replace DeepSeek on JUDGE almost as-is, except that M needs a bias
correction. RECONSTRUCT is the real work: the gap is in P and E, which are rubric levels Jev
must infer, and the semantic-equivalence yes/no badly over-calls. Section 3 targets exactly that.

## 2. Calibration set (no new DeepSeek calls)

Reuse every saved DeepSeek judgment on FINAL-v3. These are the same prompts, the same response
format and the same student family as future evaluations:

- 8 test arms × 400 JUDGE (3,190 DeepSeek-scored) and ~2,400 scored RECONSTRUCT items
- dev evals in `artifacts/opd/evals/matrix-dev-*` (~800 JUDGE, ~600 RECONSTRUCT)

**Split by arm, not by item**, because future use means scoring *new checkpoints*:
- **fit**: `base`, `sft-judge`, `opd-judge-s52`, `opd-reconstruct-s52`, all dev evals
- **held out** (touched only once, in phase 4): `opd-judge-s104`, `opd-reconstruct-s104`,
  `opd-solve-s52`, `sft-reconstruct`

Re-scoring all of it with Jev costs under $3 in total.

**Noise ceiling (recommended, ~$0.50).** Re-run DeepSeek once on 100 JUDGE and 100
RECONSTRUCT fit items. DeepSeek's agreement with itself is the ceiling Jev is measured against.
Without it, we cannot tell whether κ 0.5 on P is Jev's fault or the rubric's.

## 3. Build the Jev judge

New module `src/anlp_project/jev_judging.py` with the same `run(split, key)` /
`summarize(split, key)` interface as `baseline_judging.py`. Port the transport, question
builders and gating from `scripts/compare_jev_judges.py`, with these changes:

1. **Same inputs DeepSeek sees.** Build state from FINAL-v3 rows (`row["private"]` answer key
   incl. `error_type`, `teacher_target_response`; RECONSTRUCT via `extract_reconstruction`,
   source question, clues, final answer). The old script used a different, older item format.
2. **JUDGE**: keep the V/L/E/M questions and the rubric's gating (V=0 ⇒ L=E=0). V and L stay
   model-based: the regex parser agrees with DeepSeek V only 92.9% and with L only 83%, so
   switching them to code would shift the scale. Randomize Choice option order (seeded per uid)
   to remove first-option bias.
3. **RECONSTRUCT: decompose into literal atomic questions** (TypeSafe's "composite scoring"
   pattern) and do the counting and arithmetic in code:
   - **E (evidence)**: one Noul per observation, "Does `response.question` / `justification`
     substantively use observation *i* (not just mention it)?" plus one Noul for "any
     contradiction". Count in code, then map the count to a level 0–4.
   - **M (validity)**: separate Nouls for "well-posed on its own", "answer equals
     `final_answer`", "justification only restates the answer", and "states a false
     mathematical claim", then combine with the rubric's logic in code.
   - **P / T**: keep the Score questions, but add the boundary cases from `judge_fidelity.md`
     as explicit criteria (literal reading).
   - **Same question**: drop the stand-alone yes/no. Derive it as P=4 ∧ T=4 ∧ a fitted
     threshold on the equivalence Noul.
   - **Shortcut**: keep it as is (99–100% agreement).
   - *Only if P stays below the gate*: build a one-off premise checklist per source question
     (fixed question side, ~$0.30 once, cached in `data/`) and ask one Noul per premise.
4. **Calibration map.** For each dimension, fit monotone cutoffs from Jev outputs (Noul counts
   or expected score) to DeepSeek's 0–4 levels, maximizing quadratic-weighted κ on the fit
   arms. Use pure Python (the repo has no numpy or sklearn). Freeze the result as
   `data/jev-eval/calibration-v1.json` alongside the pinned model `jev-1.13.0` and a version
   tag `jev-eval-v1`. This step absorbs biases such as JUDGE M's +0.5.
5. **Context limit.** 739 of 6,400 responses contain `<think>` blocks and about 4 exceed ~25k
   tokens. Policy:
   1. strip `<think>…</think>` from JUDGE state, since this cuts distractors (accept the change
      only if it does not lower agreement on the fit arms);
   2. if still over the limit, keep the head and the tail and record `truncated: true`;
   3. never send a request that is over the limit.
6. **Iteration loop.** Iterate only on fit arms. Each variant reports per-dimension κ and the
   total Pearson against DeepSeek. Stop when the fit-arm gate passes or after 3 variants.

## 4. Acceptance gate (held-out arms, run once)

These are system-level checks, because the study reports arm means and paired Δ against base:

| Check | JUDGE | RECONSTRUCT |
|---|---|---|
| \|arm mean Jev − DeepSeek\| | ≤ 3 points | ≤ 4 points |
| paired Δ vs base (`report_matrix.py` method) | same sign wherever DeepSeek's CI excludes 0; \|ΔJev − ΔDS\| ≤ ½ CI width | same |
| arm ranking, Kendall τ (all 8 arms) | ≥ 0.8 | ≥ 0.8 |
| item total Pearson | ≥ 0.95 | ≥ 0.85, or ≥ 90% of DeepSeek's self-agreement |
| 1–5 rating exact | ≥ 85% | ≥ 70% |
| shortcut agreement | — | ≥ 97% |

Compare only on items both judges resolved, and report separately how many items DeepSeek left
unresolved but Jev scored, since that changes the denominator.

**If RECONSTRUCT fails**, fall back to a cascade: Jev scores everything, and items whose
minimum dimension confidence is below τ are re-judged by DeepSeek. Pick τ on the fit arms so
that ≤ 15–20% escalate, then re-check the gate. Cost stays ≈ 3–4× below today's.

## 5. Integrate end to end

- `scripts/judge_baseline.py --judge {jev,deepseek}` (default `jev`). Outputs go to
  per-judge files (`judgments.jev.jsonl`, `judged-scores.jev.jsonl`,
  `judged-summary.jev.json`), and every row carries `judge: "jev-eval-v1"`. The existing
  DeepSeek files stay untouched.
- `report_matrix.py` / `compare_dev.py`: add `--judge` (default `jev`). They refuse to compute
  a Δ when base and arm were scored by different judges, and the report header names the judge.
- `pull_and_judge.sh`: run the Jev judge (it now finishes in minutes, not tens of minutes).
- Re-score all 8 test arms and the dev evals with Jev, so the matrix has a complete Jev column
  plus the DeepSeek column for comparison.
- Key: `JEV_KEY` in `.env` (it is currently missing). The pinned model ID is logged per record.
- Tests (`tests/test_jev_judging.py`, no network): gating, the calibration map, Noul→level
  counting, choice shuffling and the truncation policy, all on recorded Jev responses.

## 6. Document

Add a "Judge" section to `docs/research/transfer-study/baselines-and-opd-method.md`. It covers
the change, the calibration report (`artifacts/jev-calibration-v1/report.md`: fit vs held-out,
DeepSeek ceiling, cost) and the rule that numbers from different judges are never compared
directly.

## Budget and order

| Phase | Spend | Output |
|---|---|---|
| 0 key + smoke (5 items/task) | ~$0 | working transport on FINAL-v3 rows |
| 1 port + baseline Jev on fit arms | <$1 | v0 agreement on current data |
| 2 DeepSeek noise ceiling (optional) | ~$0.50 | ceiling numbers |
| 3 decomposition + calibration (≤3 variants) | <$2 | `calibration-v1.json` |
| 4 held-out gate | <$0.50 | pass/fail report |
| 5–6 integrate, re-score all, docs | <$1 | matrix report on Jev |

Total under ~$5 of API spend. Each new checkpoint evaluation then costs about $0.15–0.30.

## 7. In-training judge (open model)

Decision (2026-10-06): **Jev scores final test evaluations; an open model judges everything
during training.** That covers dev-slice checkpoint selection, SFT warm-up filtering
(`--sft-keep`) and any optional judge reward. The two judges differ on purpose: a checkpoint is
never selected and finally scored by the same judge, so gains that only exploit the judge
cannot carry into the reported numbers.

Constraints: in-training inputs are ≤ 8k-token rollouts plus the problem and answer key. The
account caps all jobs at 8 GPUs and the teacher and students already use 5–6. Volume is about
64 judgments per step plus 200-question dev slices.

**Chosen (2026-10-06): A, the teacher logit judge.** Kev-4B is kept only as a fallback if A
fails the acceptance check below, which now validates A rather than choosing between A and B.

**Candidates considered:**

| | A: teacher logit judge | B: Kev-4B |
|---|---|---|
| Model | Qwen3.8-27B, already served by vLLM (`opd_train.serve_teacher`) | `jaredpalmer/kev-4b` (LoRA + head on Qwen3.5-4B, Apache-2.0) |
| How | `/v1/completions`, prompt ends at the answer slot, `max_tokens=1`, `logprobs=20`; read P("0".."4") / P(yes) | its `/v1/systemone` server, Jev-compatible; reuses the Jev question builders from §3 |
| Extra GPUs | **0 during training**; 2 for a standalone dev eval | 1 (~14 GB), or shares the student's GPU |
| Reasoning | strong (27B; open-alternative-jev reports 73.7% for Qwen3.6-27B vs Jev 72.7% on typed decisions) | weak on reasoning (MMLU-Pro 0.57 vs Jev 0.84); validated to 8k |
| Risk | teacher both sets the OPD target and judges, so its scores correlate with the training signal | less accurate on math validity (M) |

A and B share one code path: `jev_judging.py` question builders → a `backend` switch
(`typesafe` | `vllm-logits` | `kev`), so the rubric, gating and calibration map are identical
across judges.

**Bake-off** (no new labels needed): score the dev-eval folders in `artifacts/opd/evals/matrix-dev-*`
(15 runs, already DeepSeek-judged) and the fit arms with A and B. Pick the candidate with the
higher **checkpoint-ranking agreement with Jev and DeepSeek** (Kendall τ over dev runs),
because ranking checkpoints is all an in-training judge is for. Tie-break on item-level r.
Accept if τ ≥ 0.8 and JUDGE total r ≥ 0.9. Cost: ~1 GPU-hour on Turing for B; A runs while a
teacher is up.

## Open decisions

1. Approve the ~$0.50 DeepSeek self-agreement run (recommended).
2. If RECONSTRUCT misses the gate: accept the Jev + DeepSeek cascade, or accept Jev alone with
   its measured (lower) agreement reported?
3. Rejudge the 8 existing arms with Jev and make Jev the headline column, or keep DeepSeek as
   headline for already-reported results?
