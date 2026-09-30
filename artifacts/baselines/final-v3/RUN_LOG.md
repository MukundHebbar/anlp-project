# FINAL-v3 baselines: run log

What was decided, what went wrong, and what was changed, in order (2026-09-29). Results
are in [REPORT.md](REPORT.md); the method is in [README.md](README.md).

## Before generation

- **Models.** Student `Qwen/Qwen3.5-4B`, teacher `Qwen/Qwen3.8-27B`. OPD needs the two
  models to share a tokenizer. This was checked on Modal (CPU):
  - All 248,070 student tokens have the same IDs in the teacher.
  - The teacher has 7 extra audio/TTS special tokens, which the student never generates.
  - 41/41 sample texts (final-v3 prompts, long reference solutions, unicode and special-token strings) encode identically.
  - The rendered non-thinking chat prompt is token-identical, although the template files differ.
- **Prompts.** These are the existing repository prompts; no prompt was tuned.
  - SOLVE: `solve_no_reference.md`, as in the earlier Qwen SOLVE runs.
  - RECONSTRUCT: `final_v1/student.md`. It is byte-identical to the student prompt in the manifests of the DeepSeek-scored `final-100-v1` and `valid-100-recovery-v1` runs (sha256 prefix `eb903d62c441`), and it is sent the same way: one user message, thinking disabled.
  - JUDGE: `judge_student_p1.md`. The FINAL-v3 `training.input` ends with the task instruction but does not specify an output format, so three lines were added giving the `Decision:` / `First wrong step:` / `Explanation:` format. That format matches the teacher targets and the existing parser.
- **Sampling** follows the earlier Qwen3-4B runs: temperature 0.7, top_p 0.8, top_k 20, seed 0, one sample, at most 8,192 new tokens.

## Train pilot (100 per task)

The pilot exists to catch problems before the test set is touched. It was run on
fixed train IDs ([manifest](../../../data/manifests/final-v3/pilot-train-100.json)).

- **Verbosity.** Qwen3.5-4B hit the 8,192-token cap on 14–16% of answers. These are not
  repetition loops: in non-thinking mode the model re-checks its work at length in plain
  text. The teacher hit the cap on 0–5%.
- **RECONSTRUCT JSON.** Only 5/100 student answers are valid JSON as returned; with the same
  prompt, Qwen3-4B failed to parse 2/52 times. The failures are malformed JSON, not prompt
  mismatch:
  - 22 had an `assumptions` array that was never closed, `")}` endings, or invalid `\'` escapes;
  - 14 were cut off at the cap;
  - 7 had unescaped LaTeX backslashes;
  - 6 had other delimiter errors.
- **Decisions after the pilot:**
  - Keep the 8,192-token cap and count cap hits as failures, reported separately.
  - Keep the prompt.
  - Add a deterministic lenient extractor that recovers the `question`/`justification` strings from broken JSON without rewriting them. Report the strict-JSON rate separately.

  Generation settings were then frozen for the test run.

## Judging

- JUDGE V/L/E/M and RECONSTRUCT PC-v4 judges are the repository's, run on DeepSeek V4.1
  Flash through DeepInfra (temperature 0, reasoning low, 8,192 tokens), with the
  repository's validators.
- Concurrency was raised from the protocol's earlier limit of 4 to 8–16 at the user's
  request. At 32 simultaneous calls the provider returned `429 Model busy` on about a third
  of calls. **Retry policy:**
  - A call that never returned a judgment (transport failure) may be sent once more, with backoff on 429. That makes at most two attempts in total.
  - A judgment that returned but failed validation is never retried; it stays unresolved.

## Incidents and fixes

| Incident | Cost | Fix |
|---|---|---|
| Weights first downloaded to the container's disk, not the Volume (`HF_HOME` was set after `huggingface_hub` was imported) | a few cents CPU | Set `HF_HOME` in the image; the job now checks the weights are in the Volume |
| Student pilot result lost after generation: the return value called `torch.cuda` in the main process | ≈ $0.30 GPU | Results are written to the Volume before returning; errors return as text; GPU info from `nvidia-smi` |
| Teacher pilot failed at start: vLLM's default of 1,024 sequences exceeds the 27B hybrid model's ~325 recurrent-state blocks | ≈ $0.25 GPU | `max_num_seqs = 256` for both models (affects speed, not outputs) |
| Teacher test run aborted after 12 minutes: the local Modal client lost its heartbeat and Modal stopped the non-detached app | ≈ $1 GPU | Runs launch with `modal run --detach`; a `collect` step can finish a run from its Volume copy |
| SOLVE verifier crashed on one teacher answer: sympy raised `IndexError` on a collapsed sentence | none | `IndexError` added to the verifier's parse-failure exceptions, so the answer is `unverified`; regression test added |
| Teacher test judging failed before any call: a response contains the literal text `{{1}}`, which `render_template`'s leftover-placeholder check treats as a missing value | none | A one-pass renderer fills only the template's own placeholders. All 1,374 already-recorded judge prompts are byte-identical under it |

The student pilot ran with vLLM's default concurrency, before `max_num_seqs` was set;
every other run used 256. Concurrency does not change what is generated for a given seed.

## Test run

- Generation settings were unchanged from the pilot. The student and teacher ran on separate H100s.
- **Student:** loaded in 164 s, generated 1,200 answers in 404 s.
- **Teacher:** loaded in 188 s, generated in 1,562 s. This was the run relaunched in detached mode.
- **Judging** used the same two-attempt rule.
  - Connection drops and 429s are waited out within an attempt, so they do not use up the attempt. This was added after a burst of connection errors at the start of the teacher's judging.
  - Concurrency varied between 6 and 24 during the run. It affects speed only; every call used the same prompt, model and settings.
- Final judge-call outcomes:
  - Student: 1,074 valid, 35 validation failures, 7 transport failures after two attempts.
  - Teacher: 1,118 valid, 42 validation failures, 20 transport failures after two attempts.
- Judge calls are slow because DeepSeek V4.1 Flash reasons before answering. RECONSTRUCT validity judgments produce a median of about 4,000–4,500 output tokens, and some reach the 8,192 cap. Such a call returns only reasoning; it is recorded as `IncompleteCompletionError` and counted as a transport failure.

## Scoring change after the test run

- At the user's decision, a SOLVE answer with several `<final_answer>` tags is now scored on its **last** non-empty tag.
- These answers come mostly from the student, which sometimes reasons, writes a stray `</think>` and answers again.
- Previously the repository extractor counted them as `missing`. That extractor is unchanged; the rule lives in `anlp_project.baseline.extract_solve_answer`.
- All stored runs were re-scored:
  - student test 70.0% → 73.0% (26 answers changed status);
  - teacher test 80.5% → 80.8% (1 changed);
  - student pilot 67.0% → 69.0%.
- Generation was not repeated.

## Student-size and token-cap check (test SOLVE, first 200 questions by uid)

- At the user's request, Qwen3.5-2B (8k and 16k caps) and Qwen3.5-4B (16k) were run on 200 SOLVE test questions. These runs are in `test/qwen3.5-2b*`, `test/qwen3.5-4b-cap16k`.
- This uses test data to inform the choice of student model and cap; that is noted here as a limitation.
- Runs are not bit-identical across caps: 26 of the 181 4B answers that finished under 8k changed at 16k, probably through vLLM batching numerics.

## Final protocol: 2B student, 32k evaluation cap

- **Decision (user):** switch the student to Qwen3.5-2B, train on 16k-token rollouts, and evaluate at 32,768 tokens.
- **Reasons:**
  - The 4B left SOLVE almost no correctness headroom once the cap stopped binding.
  - A 32k evaluation matches standard practice.
- **2B pilot:** JUDGE and RECONSTRUCT on the 100 train-pilot questions, at 16k, judged: JUDGE verdict 53%, first step 19%; RECONSTRUCT PC-v4 50.4 on scored items.
- **Full test runs:** both models on all 1,200 test questions at 32k, in parallel on two H100s (detached).
  - 2B: loaded in 145 s, generated in 762 s.
  - 27B: loaded in 234 s, generated in 2,102 s.
- **Judging** (same two-attempt rule):
  - 2B: 1,064 valid, 39 validation failures, 9 transport failures after two attempts.
  - 27B: 1,132 valid, 39 validation failures, 13 transport failures after two attempts.
- **Bug fixed during this step:** a RECONSTRUCT answer flagged as a shortcut scores 0 even with an unresolved dimension, and the dimension averages failed on it. They now skip unresolved dimensions. Earlier summaries were unaffected.
- **Cost, from Modal's hourly billing report:** 2B $1.26, 27B $3.19, so $4.45 for both, of which $3.63 was H100 time and $0.82 CPU and memory. DeepSeek judging: $1.35 per model.

## Evaluation protocol v2 (final)

- **What triggered the change:** the OPD SOLVE trial (ARYAMA workspace) looped at T 0.7 after training: 89 of 200 dev answers hit the 32k cap. At the training temperature (T 1.0, top_p 1.0) it improved, from 52.0% to 61.5%.
- **What the literature does:** OPD maths papers either evaluate at the training temperature or use R1-style T 0.6–0.7; none uses the model card's settings or a presence penalty.
- **Decision (user):** evaluate at T 1.0, top_p 1.0, top_k off, no penalties, 32k cap, one sample per question.
- **Code:** `baseline.EVAL_SAMPLING`, `modal_baseline.py --protocol v2`. Folders are `test/<model>-final`.
- **Runs, in parallel on 2026-09-30:**
  - Teacher on SANGHA: 230 s load, 1,750 s generation, **$2.71**.
  - Student on ARYAMA (its own weight cache, `BASELINE_VOLUME=anlp-opd-cache`): 148 s load, 380 s generation, **$0.76**.
  - Both used the same pinned image (vLLM 0.30.0, transformers 5.17.0) and the same weight snapshots.
- **Judging:** each model's judging started as soon as its generation finished.
  - Student: 1,083 valid, 61 validation failures, 10 transport failures after two attempts; **$1.57**.
  - Teacher: 1,124 valid, 52 validation failures, 14 transport failures after two attempts; **$1.42**.
- **Wall-clock:** 1 h 34 min for everything.
- **Headline:** SOLVE 55.8% vs 79.5%; JUDGE verdict 57.5% vs 73.5%; RECONSTRUCT PC-v4 36.0 vs 70.1.

## Cost

- **Modal:** $7.21 for all of this work, including the failed attempts above. The workspace metered $82.86 before this work and $90.07 after, all covered by credits.
- **DeepInfra (DeepSeek judging):** pilot $0.65, test at 8k $2.69 (student $1.39, teacher $1.31). This was the total before the final-protocol runs.
- **By the end of the final-protocol runs:**
  - Modal: this project's app metered $13.53 for the day, of which $11.02 was H100 time.
  - DeepInfra: $6.38 in total across all judge calls, adding the 2B pilot ($0.34) and 32k test judging ($2.70).
