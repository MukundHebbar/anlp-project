---
name: reconstruct-math-task
description: Build, calibrate, and evaluate mathematical RECONSTRUCT examples for the SOLVE/JUDGE/RECONSTRUCT transfer study.
version: 0.2-pilot
---

# RECONSTRUCT: task specification and experiment procedure

Active research process: [autoresearch protocol](../../plans/reconstruct-autoresearch.md). Track **mean rubric score20–75/100** separately from the latest **20–40% semantically correct reconstruction** target. Equivalent mathematical formulations count as correct. Retain the stricter grounded-recovery gate and report verification errors separately. Use independent quality checks, decision rules, and evidence records before promoting a version.

Additional distribution objective: a fixed generation procedure should naturally produce a modal rating3, intermediate-frequency ratings2/4 and uncommon ratings1/5 on development data. The1–5 display is the existing0–4 rubric plus1, without changing score meanings or historical records. Tune global conversion policies, not individual outcomes or judge severity; freeze before confirmation. Report all five counts, missingness, coverage and separate semantic/grounded recovery. See the autoresearch protocol for the full selection rule; no exact quotas or Gaussian fit are required.

Latest checkpoint: [the richer-information bracket](../../../artifacts/reconstruct/bridge-composition-ax/decision.md) achieved2 verified recoveries among6 scheduled development families using two symbolic intermediate clues and the existing premises-first p14 prompt. Four raw semantic matches reduce to2 after disclosure/copying gates. One of the two needs a disclosed correction of a mathematically contradictory verifier rejection, backed by an independent implication check. Mean raw quality66.67/100; histogram[2,0,0,0,4], so distribution and production-validation goals remain unmet. [Completion audit](../../../artifacts/reconstruct/bridge-composition-ax/completion-audit.json) and [candidate manifest](../../../artifacts/reconstruct/bridge-composition-ax/candidate-manifest.json) preserve exact evidence.

Current follow-up: [AF/AG](../../../artifacts/reconstruct/partial-exposure-ag/decision.md) found no semantic recoveries from richer observations or independently audited three-clue prefixes. [AI matched SOLVE controls](../../../artifacts/reconstruct/matched-solve-ai/decision.md) returned 4/12 correct answers and 3/12 strictly verified explanations on the same twelve original questions. This reveals forward-mathematics failures as well as reconstruction-specific failures; it is not a training-transfer result or a hard reconstruction ceiling. [AH](../../plans/reconstruct-amendment-ah.md) now tests preserving the target and all but one essential premise, with a private inverse certificate. [AH/AJ completed](../../../artifacts/reconstruct/one-gap-ah/decision.md) with0/3 recoveries in both output orders; neither is adopted. [AK/AL](../../../artifacts/reconstruct/constructive-gate-al/decision.md) tested the fresh sixteen-source allocation: the original policy admitted2 inputs, and removing an inconsistent public-answer veto admitted6. Exact common student draws were reused. Neither policy produced a semantic recovery; AL mean10/100 on5 scored outputs, with1 token-cap failure. One response correctly inferred a missing parameter but reversed the requested unknown, so latent parameter inference is recorded separately. The reduced gate remains experimental and is not adopted. Older candidate choices below remain historical.

Historical execution checkpoint: [AA/AB/AC completed](../../../artifacts/reconstruct/richer-exposure-aa/final-report.md):15 scheduled local draws,14 parsed,28 teacher judgments. Three versus six clues and grouping the same six into three entries produced no original recoveries with the incumbent prompt. Two concise prompt follow-ups each recovered1/3 questions semantically, but verification errors left grounded recovery0/3. DeepSeek incorrectly awarded full marks to one flawed verification. Only3/12 source families passed all input gates; disagreement certificates expose disclosure false positives. No final task version,5/25 confirmation, or near-perfect teacher reliability has been established. The simpler inverse-example prompt is a development candidate only. Older sections below are historical evidence, not current acceptance claims.

Follow-up [AD mathematical verification](../../../artifacts/reconstruct/math-verifier-ad/comparison.md) matched12/12 paired development controls, including the missed incorrect proof. [AE](../../../artifacts/reconstruct/certificate-adjudication-ae/decision.md) tested one additional certificate-reviewed richer input; Qwen still omitted an essential premise and failed mathematical verification. The separate verifier is a provisional veto, not an adopted replacement score or a claim of near-perfect accuracy. Source137 remains excluded after an adjudication that contradicted the written inverse-inference rule; its raw rejection is preserved.

**Current requirements override the historical pilot defaults below:** use the [next-session plan](../../plans/reconstruct-next-session.md) and [semantic recovery/leakage amendment](../../plans/reconstruct-semantic-recovery-gates.md). In addition to the mean-score target, require at least5/25 preselected source families to yield a grounded, semantically equivalent original question with valid non-leaking inputs. Other grounded alternatives retain their rubric credit but do not count toward this gate. Full-bank exposure is not an adopted production policy: its D3 coverage failed. Separate source support, public disclosure, grounded scoring, and source-aware semantic equivalence; calibrate these before confirmation.

Status: runnable development protocol with a completed local pilot. The best tested configuration is documented below, but it is not confirmation-frozen: D2 performance did not meet the proposed useful range, so C remains untouched. This is a repository-local operating specification, not an installed agent skill.

Measured results and the stopping decision are in [the 2026-09-20 pilot report](../../research/reconstruct/pilot-2026-09-20.md). Raw records are in `artifacts/reconstruct/pilot-v1/`.

The [adaptive eight-hour research plan](../../plans/2026-09-20-reconstruct-adaptive-eight-hour-plan.md) has been executed. The pilot used the original `Qwen/Qwen3-4B` in explicit non-thinking mode and reasoning-enabled DeepSeek V4.1 Flash through `DEEPINFRA_API_KEY`. It converged on compact prompts, complete honest banks of one to four observations, and a construct-aware evaluator. The larger factorial remains deferred because the D2 candidate did not justify opening the confirmation split.

## Purpose

Construct the incomplete-evidence condition of the [reasoning transfer study](../reasoning-transfer-study.md). The main project compares training and transfer across SOLVE, JUDGE, and RECONSTRUCT. This procedure first establishes a valid RECONSTRUCT task and a reliable score. The clue experiment is supporting calibration.

Use the supplied few-shot prompts. Do not invent a separate transformation rule for every mathematical topic or manually tune individual examples to make Qwen succeed.

## 1. Task contract

A source record consists of a question Q, its final answer A, and a checked worked solution W. The converter creates a small bank of observations C from W. A student sees A and a selected subset of C, but not Q or W. It returns one self-contained question Q' and a concise mathematical justification J.

    (Q, A, W) → clue bank → (A, selected clues) → (Q', J)

A successful reconstruction satisfies all of the following:

1. Q' is a well-posed mathematical question: necessary domains, conditions, and target are specified.
2. Solving Q' gives the supplied A, allowing mathematically equivalent answer forms.
3. Every displayed clue can hold in a single coherent solution of Q'. Clues cannot be attached as unrelated commentary or justified using incompatible interpretations.
4. J demonstrates the connection between the proposed question, the displayed clues, and A. It may use a different sound method from W.
5. Q' is a substantive mathematical problem. It does not state the requested answer as a premise, ask to repeat A, or encode the output through a tautology such as “What is A?”

The student aims to recover the original mathematical task, without claiming that sparse evidence uniquely identifies it. Students may infer missing details and must identify those choices briefly. A different but grounded reconstruction can earn full grounding-rubric credit, but it does not count toward the required 5/25 grounded semantic recoveries. Report these two endpoints separately.

**Capability:** abductive construction with mathematical constraint checking. The student infers missing structure and verifies a candidate under uncertainty. Evaluation demonstrates task performance; transfer requires the later training interventions.

## 2. Who sees what

| Role | Visible information |
|---|---|
| Converter | Q, A, checked W; converter few-shot examples |
| Item auditor | Q, A, W, clue bank and its hidden support |
| Student / training-input renderer | A and selected displayed clues only; common task instructions and fixed demonstrations |
| Primary evaluator | Exactly the student's evidence, plus Q' and J; no source Q, W, reference reconstruction, model name, or experimental condition |
| Source-recovery evaluator | Q, W, displayed evidence, Q' and J; run separately |

Source IDs, topic/difficulty labels, eligibility reasons, hidden supports, and reference completions are metadata, not student input. Exposing additional context counts as additional evidence and requires a new condition. Do not silently add a topic hint to a difficult example.

DeepSeek can fill converter and evaluator roles through separate calls. That is a practical choice, not independent validation; human calibration is required. The student's J is a concise verification artifact, not a request to disclose private internal deliberation.

## 3. Simple production procedure

1. **Validate the source.** Check Q/A consistency and that the selected parts of W are mathematically sound. A final-answer verifier alone does not validate a worked solution. Prefer the verified dataset solution where available; audit any teacher rewrite.
2. **Convert once.** Apply [`convert_p2`](../../../data/prompts/reconstruct/runtime/convert_p2.md). Produce one to four distinct observations, stopping when no further honest clue exists. Each observation has a normal sentence, a mathematical/telegraphic rendering, and hidden source support. Return `NOT_SUITABLE` rather than padding with redundant facts.
3. **Audit the bank.** Apply [`audit_p2`](../../../data/prompts/reconstruct/runtime/audit_p2.md). Accept, flag for review, or reject. A converter retry may respond to a recorded audit defect, never to student performance.
4. **Select reproducibly.** For the best tested development procedure, use the complete accepted bank of one to four honest clues and randomize display order with a recorded seed. Never pad or choose a source-specific count based on student results. Use nested seeded subsets only for clue-count experiments.
5. **Render.** Use medium-disclosure clues as ordinary sentence bullets. The supplied answer is always visible. Low/high disclosure and alternate formats remain experimental factors.
6. **Run the student.** Use runtime prompt [`student_p1`](../../../data/prompts/reconstruct/runtime/student_p1.md), with the same fixed demonstration for every evaluated checkpoint. Capture the raw response and parsed fields.
7. **Score.** Apply [`evaluate_p2`](../../../data/prompts/reconstruct/runtime/evaluate_p2.md) without source access. Run the separately calibrated [`source_recovery_p2`](../../../data/prompts/reconstruct/runtime/source_recovery_p2.md) with source access for the required semantic-equivalence endpoint. Preserve per-clue checks, premise/target correspondence, and uncertainty. Every counted semantic success also requires independent mathematical and exact-input disclosure review under the current amendment.

This is one converter plus an audit, a reproducible subset rule, and an evaluator. The additional disclosure prompt is for the experiment, not a growing production pipeline.

## 4. What counts as a clue

A clue is one principal solution observation: an intermediate relation, a case distinction, a local operation, a structural property, or a boundary/checking fact. A small inseparable expression can count as one observation; do not put several independent facts into one long sentence to manipulate k.

Good clues constrain a possible solution without directly stating the source question. Examples: “Selecting the endpoint excludes its neighbour”; “One prime count is halved before taking a minimum.” Normal language is fully acceptable. Clues need not be literal excerpts.

Reject copied questions, direct paraphrases of the entire task, the original premise/target bundle, a complete worked solution, unsupported facts, and a full defining equation that merely encodes the source question. Exact numbers and named mathematical operations are not automatically forbidden: they can be useful intermediate evidence. Review individual clues and their joint disclosure.

An unordered set need not uniquely identify Q. It must leave something meaningful to infer. However, if a selected subset is vague, report its ambiguity rather than secretly supplementing it. At k=1, “same original problem” may be impossible; compatible reconstruction remains assessable and source recovery is interpreted accordingly.

Four bank observations are not required to be statistically independent. They must be distinct, non-padded observations. Redundancy is measured through subset and removal effects, not assumed absent.

## 5. Disclosure and format factors

Use [disclosure.md](../../../data/prompts/reconstruct/disclosure.md) only for calibration. It rewrites the same four observation identities into nested levels:

| Level | Intended information |
|---|---|
| Low | True qualitative structure with exact quantities or identifiers removed. |
| Medium | The bank's original observation: a useful relationship, sometimes including an intermediate value. |
| High | A more specific supported observation, adding numerical/structural detail while still withholding the complete question and solution. |

High must imply medium, and medium must imply low, for each observation. Some observations admit no honest refinement; mark a tied level rather than inventing extra facts. Proposed eligibility rule: at least two of the four observations must admit strict low→medium and medium→high refinements. Otherwise the source is ineligible for the disclosure comparison but can remain in the production pool. Keep tied observations in eligible banks and report their frequency; some selected subsets will therefore contain no disclosure difference. Analyze a common eligible source subset across all disclosure cells; report exclusions separately.

Each level has two equivalent strings: `sentence` and `fragment`. Three formats are rendered from these:

- **Sentence bullets:** one `sentence` per bullet.
- **Paragraph:** the exact same sentences concatenated, in the same order, without connective text. No new causal links or logical ordering.
- **Fragments:** the corresponding `fragment` strings, one per bullet. Notation must be understandable without the hidden source.

The audit checks sentence/fragment equivalence. This isolates representation as far as practical; report token counts because formats cannot generally be both information-equivalent and length-identical. Disclosure levels are ordinal manipulations, not measured bits of information.

## 6. Evaluation contract

The primary evaluator independently checks Q', rather than trusting its proposed justification. It outputs `well_posed`, `answer_correct`, `clue_checks`, `justification`, `shortcut`, a score, and a brief reason. Boolean checks allow `null` for uncertainty. The judge must not infer hidden reference requirements.

| Score | Definition |
|---|---|
| 4 | All mathematical conditions pass; every clue is substantively grounded; verification is sufficient. |
| 3 | Q' is valid, A is independently correct, every clue is compatible and substantively connected, and J has no mathematical error; a remaining proof or calculation step may be omitted. |
| 2 | Substantive relevant construction, but an essential clue connection is unsupported or a substantive grounding gap remains; no contradiction in Q' itself is established. |
| 1 | Substantive attempt with a demonstrated wrong answer, invalid/ill-posed question, or violated clue. |
| 0 | No usable reconstruction, answer-copying/tautological shortcut, or essentially unrelated output. |

Use `status: needs_review` and `score: null` if the evaluator cannot establish which category applies. Uncertainty is not evidence of a student error. Conversely, clear omissions in J can warrant score 2 without judge uncertainty.

Primary metric: **grounded reconstruction success rate**, score ≥3 with a well-posed question, independently correct answer, all clue compatibility checks passing, substantive clue grounding, and no shortcut. Report score-4 rate separately as complete verification. Also report mean score/4, answer correctness, clue-grounding failures, shortcuts, and uncertainty. Formatting is not mathematical correctness: use one deterministic tolerant parser; semantically readable off-schema outputs can still be scored and get a separate format-error flag.

Resolve uncertain outputs before final reporting where feasible. Otherwise report success bounds: confirmed successes / all examples to (confirmed successes + unresolved) / all examples. Do not silently drop unresolved cases or count them as known wrong. Mean-score summaries state their resolved denominator.

The source-recovery diagnostic is 2 = same essential mathematical problem, 1 = related structure with changed essential parameters/conditions/target, 0 = different mathematical problem. Cosmetic renaming is irrelevant. This diagnostic never lowers a compatible reconstruction's primary score.

## 7. Pilot: determine the clue policy

### A. Source and prompt calibration

The repository currently has 113 teacher-answer-verified sources, including existing Qwen SOLVE measurements. These are an evaluation/pilot pool, not a sufficient training corpus. Their worked solutions still require checking, and selection on teacher correctness limits generality.

Proposed split: 24 development sources, six from each available topic (Algebra, Number Theory, Discrete Mathematics, Calculus); reserve the remaining 89 for confirmation, subject to eligibility. Group duplicates before splitting. Record the seed and IDs before any reconstruction runs. Author-written few-shot examples below are format demonstrations and are excluded from measured data. If their mathematical templates occur in the pool, tag or remove near duplicates before splitting.

Use six development sources for an initial smoke audit; these remain part of development. Inspect bank validity, joint disclosure, hidden/public separation, and outputs. Fix global prompts, not individual question-specific rules. Then freeze prompt versions for the sweep. The runner is implemented in `scripts/run_reconstruct.py` and `src/anlp_project/reconstruct.py`; local serving is implemented in `scripts/run_local_qwen.sh`.

### B. Development factorial

Use k ∈ {1,2,3,4}, disclosure ∈ {low,medium,high}, and format ∈ {fragments,sentence bullets,paragraph}: **36 conditions per source**. Generate one checked bank per source and derive all conditions from it.

Use two independently seeded permutations of the four IDs. For each permutation, use its first k IDs so count comparisons are nested. Keep IDs and ordering matched across disclosure and format. At k=4, the two variants differ only in order. Subsets and seeds are experimental replicates, not new sources.

Run one student sample per item/condition/variant in the first sweep: up to 24 ×36 ×2 = **1,728 student outputs**. Add answer-only and full-worked-solution controls, one per source: up to 48 outputs. All controls use the same student instruction and evaluator; label their different information conditions explicitly. Retry transport failures, not poor mathematical responses.

Current student choice: Qwen/Qwen3-4B, matching the original model ID in earlier results, with `enable_thinking=false` explicitly applied in the chat template. Initially serve a pinned quantized conversion through llama.cpp. Starting settings are temperature 0.7, top_p 0.8, top_k 20, min_p 0, and max_new_tokens 16384. Earlier results used an 8192-token cap and vLLM; record this difference and do not pool configurations silently. Record exact checkpoint revision where recoverable, quantization, tokenizer/chat template, backend, seed, prompt tokens, completion tokens, and truncation. Validate context capacity, non-thinking operation, and cap adequacy as specified in the adaptive eight-hour plan. Use deepseek-ai/DeepSeek-V4.1-Flash with a verified reasoning-enabled request configuration for conversion and evaluation; freeze and log the provider-supported settings after the smoke test.

### C. How much does each clue reveal?

For each bank, audit whether each clue discloses an original given, the target, a derived relation, or several of these. Record direct-restatement and joint-restatement flags. This measures disclosure characteristics, not a universal numerical information score.

At medium disclosure with sentence bullets, the primary grid already supplies full-bank outputs. Add all four leave-one-out sets for each development source: at most **96 outputs**. For clue i, measure the source-averaged change from the full bank to the bank without i. Also use the nested subsets to estimate marginal gains as k grows. These are empirical contributions under a particular context; they need not be additive or positive.

Full development student budget: up to **1,872 outputs**, excluding transport retries and the small initial smoke runs. Conversion/audit/evaluation calls are additional and must be costed before execution. Do not equate output count with total provider calls.

### D. Human calibration and policy choice

Have two humans independently label 60 stratified development outputs, including passing/failing conditions and plausible alternatives, then adjudicate disagreements. Add 12 authored control responses (correct alternative, wrong answer, violated clue, tautology, and insufficient proof cases) to probe evaluator failure modes. A suggested readiness target is ≥85% binary-success agreement with adjudicated humans and no more than one false acceptance among the 12 controls; report uncertainty and subgroup results. These thresholds are operational proposals, not proof of judge reliability. If the rubric changes after inspecting these labels, validate the revised judge on a fresh sample of 30 outputs.

First consider only policies whose clues and renderings pass the structural audit and whose scoring is usable. A broad 35–70% development grounded-success band is a proposed useful operating range for Qwen, not a result to force. Prefer the least revealing, smallest k within that range; if indistinguishable, prefer ordinary sentence bullets for readability. Inspect source recovery and shortcut rates so broad generic clues do not qualify merely by admitting easy unrelated questions. Do not select a policy on accuracy alone. If none qualifies, revise the global converter using development only and document the revision.

Report all 36 cells, source-level paired differences, and exploratory count×disclosure/format interactions with uncertainty. With 24 sources, this is calibration, not strong evidence for small interactions. Use a source-cluster bootstrap (e.g. 2,000 resamples); decoding and clue variants stay within the source cluster. Do not treat 1,728 outputs as 1,728 independent problems.

### E. Frozen confirmation

Apply the chosen policy to the reserved sources once. Evaluate six conditions: primary policy; same policy with one fewer clue (minimum one); same policy with one more clue (maximum four); answer-only; full worked solution; and random sentence excerpts. If boundary clipping duplicates a condition, replace that comparison with the nearest unused clue count and record it before running. Keep confirmation selection independent of Qwen outcomes.

For random excerpts, first remove explicit question restatements and audit joint disclosure; then sample the same number of solution sentences. Report length differences and exclusion counts. This tests curated clues versus a simple valid excerpt baseline, not raw leakage-heavy text.

Use two decoding seeds per condition, keeping each input fixed across the seeds. Maximum: 89 ×6 ×2 = **1,068 outputs**. This confirms the chosen setting and count robustness, not the full factorial's interactions. Repeating all 36 cells on held-out sources is an optional larger study, with a separately declared budget.

## 8. Training handoff

After confirmation, freeze the converter, public prompt, evidence policy, rubric, and model versions. Construct training data from a separate source split. Generate one teacher completion from the same public evidence only, using the student prompt; validate it with the primary evaluator and human spot checks. The hidden Q/W can be consulted by an auditor but must not enter the teacher-completion prompt or student training input. Do not automatically use Q as the reconstruction target: that rewards recovery of information absent from the evidence.

Use valid grounded completions for SFT. If RL is later selected, its reward must implement the same mathematical contract; do not turn source similarity into the sole reward. Keep training method fixed across task arms and evaluate all checkpoints using the same RECONSTRUCT policy. Report training example acceptance and any source-pool changes across the matched three-task dataset. A separate training protocol sets corpus sizes and compute budgets.

## 9. Minimal record and artifacts

Persist the following fields; these are a schema specification, not runner code:

```text
source_id, split, source_group_id, topic, source_question, answer, checked_solution
converter_version, audit_version, generator_model, generation_attempts
bank[{id, sentence, fragment, hidden_support}], audit, eligibility_reason
condition{clue_ids, disclosure, format, selection_seed, display_order}
public_input{answer, clues}, student_prompt_version, student_model, decoding_config
raw_response, parsed_response{question, justification, assumptions}, format_error
primary_evaluation, source_recovery, human_labels, runtime, token_counts
```

Only `public_input` plus the fixed student prompt is sent to the student. Keep private records separate from exported prompts. Save rejected/uncertain items with reasons, not only successful examples.

Use [report-template.md](report-template.md) to record coverage, full pilot results, judge calibration, the frozen choice, and held-out results. Deliverables before training: checked source manifest, prompt versions, public/private examples, source-group split, pilot table, human audit, and frozen confirmation report. No claim of readiness until these checks have actually run.
