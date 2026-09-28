# RECONSTRUCT: eight-hour adaptive research and implementation plan

Status: executed on 2026-09-20. Implementation and development experiments are complete; C was deliberately left untouched because D2 failed the readiness range. See [the pilot report](../research/reconstruct/pilot-2026-09-20.md) and [`freeze.json`](../../artifacts/reconstruct/pilot-v1/freeze.json).

## 1. Intended outcome

By the end of eight hours, produce the best-supported RECONSTRUCT version among the versions actually tested: a simple task definition, compact conversion/student/evaluation prompts, a few useful demonstrations, a functioning local pipeline, and an evidence-backed report explaining what worked and why.

The work includes fixing the task and rubric when examples expose problems. It is not merely running a predetermined grid. At the same time, retain a fresh confirmation set so improvements on development examples are not mistaken for generalization. The resulting task must be suitable for the later SOLVE/JUDGE/RECONSTRUCT training-transfer study.

“Best” means a useful balance of valid generation, incomplete but informative evidence, grounded student responses, reliable evaluation, and low prompt complexity. It does not mean maximizing Qwen accuracy, hitting a desired percentage, or finding a globally optimal prompt within eight hours.

## 2. Confirmed model and environment decisions

The retained [Qwen SOLVE artifact](../../artifacts/qwen3-4b/solve/113/results.json) contains this original run configuration in `metadata.raw_metadata`:

| Setting | Earlier results | New reconstruction work |
|---|---|---|
| Model | `Qwen/Qwen3-4B` | Same model ID; no Instruct-2507 substitution |
| Thinking | `enable_thinking=false` | Explicitly false in the actual chat template |
| Temperature / top-p / top-k | 0.7 / 0.8 / 20 | Initially unchanged |
| Max new tokens | 8,192 | 16,384 headroom; small matched 8K/16K check |
| Backend | vLLM on an L40S | CUDA llama.cpp on laptop first |
| Precision/revision | Exact values not established by retained metadata | Pin and record GGUF revision, quantization, and SHA-256 |

The original [Qwen3-4B model card](https://huggingface.co/Qwen/Qwen3-4B) supports explicit non-thinking mode; [official GGUF conversions](https://huggingface.co/Qwen/Qwen3-4B-GGUF) exist. The locally cached original-model snapshot is `1cfa9a7208912126459214e8b04321603b3df60c`, and its tokenizer template includes `enable_thinking`. This does not establish that the historical job used that exact snapshot.

Local configuration: one server slot, loopback binding, initial Q4_K_M conversion of original Qwen3-4B, GPU offload, approximately 24K context including input/output, quantized KV cache if required and supported. Use the checkpoint's chat template with thinking disabled. A parser setting that hides reasoning is not a substitute for disabling thinking. Inspect the rendered template and raw responses: an empty template-inserted think block is different from generated reasoning content. A concise mathematical justification in the visible answer is expected and is not thinking-mode activation.

The laptop preflight found an RTX 3050 with 6 GiB VRAM, 15 GiB RAM with limited availability, and about 19 GiB free disk. Recheck at execution. Download one model variant first. Do not close unrelated applications or delete user caches. Timebox installation; prefer a compatible pinned binary, otherwise build the CUDA runtime using the installed compiler/toolkit. Do not assume driver-reported CUDA version equals compiler version.

The user corrected `.env`; `DEEPINFRA_API_KEY` is present and nonempty. Use it normally and never print it. The previous authenticated model-list request included `deepseek-ai/DeepSeek-V4.1-Flash`; the user reports the environment now works. A live probe on 20 September showed that DeepInfra rejects numeric reasoning effort for this endpoint and requires one of `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, or `max`. Use `high` initially and record it. DeepSeek handles conversion, audit, and evaluation in separate calls. Do not reuse the old model ID or old price constants silently.

Keep 16K student output headroom throughout the main pilot, without encouraging verbose answers. Record length stops and perform an 8K/16K comparison on the same development inputs before deciding that a smaller cap is adequate. Reject context overflow rather than truncating clues. DeepSeek starts at a 16K combined completion allowance and can increase to 32K if reasoning consumes the cap before the required output; any change is logged and applied consistently within comparisons.

Local quantized runs and historical vLLM runs share the model family/checkpoint ID but are not identical experimental conditions. Preserve that distinction. No historical 54.87% SOLVE score should be presented as a new local baseline. A small fresh SOLVE sanity run can catch serving mistakes; it is not a quantization-equivalence study.

## 3. What stays fixed while we adapt

The following are task commitments, not knobs to change until scores look attractive:

- Student sees the final answer and partial solution observations, not the original question or complete solution.
- Student returns a self-contained question and a concise, checkable justification.
- The candidate must have the supplied answer, and all displayed clues must fit substantively into one coherent solution.
- Legitimate alternatives can pass. Original-source recovery is a separate diagnostic.
- Copying the answer, disguising it as the target's premise, or appending unrelated clues does not pass.
- The evaluator must distinguish a wrong response, an insufficiently justified response, and its own inability to judge.
- No selecting or editing individual items based on whether Qwen gets them right.

What can change on development evidence: converter wording, clue selection strategy, clue count, specificity, representation, demonstrations, output schema when parsing genuinely obstructs the task, and operational rubric wording. Changes to the mathematical success definition are substantive: preserve old scores, explain the reason, and re-evaluate compared versions using the revised common rubric. Do not compare incompatible scoring versions.

## 4. The iteration loop

Work in 20–40 minute cycles, normally on 4–8 sources. A cycle ends with a decision, not just more outputs.

1. **Observe:** inspect the entire case: source, checked solution, public evidence, reconstructed question, justification, evaluator decision, and runtime metadata.
2. **Diagnose:** identify whether the problem is source mathematics, clue construction, ambiguity, student inference, grounding, prompt/schema following, evaluator behavior, or serving/truncation.
3. **Hypothesize:** write one sentence predicting how a specific change should address that failure and how it could fail.
4. **Change:** revise the smallest relevant component. Hold the others fixed where possible.
5. **Compare:** run old and new versions on the same sources/evidence/seeds. If the converter changes, compare matched sources and explicitly acknowledge that evidence changed.
6. **Check beyond the motivating case:** test a few other development sources. A fix is not adopted solely because it repairs the example that suggested it.
7. **Decide:** adopt, reject, or keep uncertain. Record outputs, mathematical reasoning, effects, and the next unresolved issue.

Do not impose an arbitrary two-revision limit. Iterate as needed until the freeze time, while keeping batches small and preserving confirmation/report time. Add complexity only when an observed failure justifies it. Stop tuning a component when repeated cases show it is no longer the main bottleneck.

### Case inspection checklist

For each deeply inspected case, answer:

1. Are the source and every clue mathematically correct?
2. What does each clue reveal: a given, target, intermediate relation, numerical value, or structural constraint?
3. Does the joint evidence still leave meaningful missing structure, or does it effectively restate the question?
4. Is the proposed question well-posed and does its answer actually equal A?
5. Where exactly does each clue appear in a valid solution? Is any connection decorative or contrived?
6. Are the chosen unspecified details reasonable, and has the student verified them?
7. Is a difference from the source a legitimate alternative rather than a failure?
8. Does the evaluator's score follow from the mathematics and stated rubric?

Use algebra, symbolic checks, or small enumeration when appropriate, with a saved verification snippet/result. Inspect all early smoke outputs; later inspect all suspicious/uncertain cases plus a balanced sample of apparent successes and failures. Label this as assistant mathematical review, not an independent human-annotator study. User-provided human judgments can be recorded separately if they arrive; they are not a prerequisite for moving through development.

## 5. Data organization before experiments

Start with the existing 113 teacher-answer-correct source pool. Join to available worked solutions by stable source ID. Confirm the correctness of the solution portions used for clues; answer agreement alone is not a proof audit.

Before reconstruction generation, group duplicates and near-duplicates of the demonstration templates. Fix a seeded topic-balanced partition:

| Split | Target size | Use |
|---|---:|---|
| Exploration D1 | 12 | Repeated small cycles, prompt writing, failure analysis |
| Development check D2 | 12 | Check whether promising fixes extend beyond their motivating cases; it remains development once used |
| Confirmation C | 24 | Only after the final prompt/rubric/configuration freeze |
| Unused reserve | 65 before exclusions | Remains untouched; potential later confirmation if C exposes a fatal flaw |

Aim for three sources per topic in D1/D2 and six per topic in C, subject to actual eligibility. Record all exclusions and denominators. Do not replace difficult Qwen failures. If runtime requires a 12-source confirmation, choose a predeclared balanced prefix before viewing any C reconstruction results.

Do not require four clues merely to retain a source. During discovery, allow up to four distinct supported observations and record bank size; never pad. A 1–4 count comparison uses the common subset with four valid clues. Production suitability and eligibility for that particular comparison are different fields. If this differs from the old converter, version it explicitly as a new converter policy.

## 6. Eight-hour work schedule

| Time | Main work | Decision / output |
|---|---|---|
| **0:00–0:45** | Bring up original Qwen locally with non-thinking template; tiny DeepInfra reasoning probe; save exact configuration. | Correct models, usable runtime, initial latency/memory. Decide early whether fallback is necessary. |
| **0:45–1:15** | Minimal reusable runner, source partition, public-only rendering, resumable outputs, first 2–4 full cases. | End-to-end smoke results and first failure ledger. |
| **1:15–2:30** | Fast cycles improving clue validity and the task contract; inspect every small-batch result. Intersperse evaluator controls. | Candidate v1 with concrete before/after cases and a working rubric. |
| **2:30–3:30** | Paired zero-/one-/two-shot comparisons; inspect successful and failed reasoning. | Smallest useful prompt/demonstration set; converter and student changes disentangled. |
| **3:30–5:00** | Targeted evidence experiments: count first, then specificity/format if count evidence is usable. Check repeatability and cap adequacy. | Evidence for the selected clue policy and unresolved limits. |
| **5:00–5:45** | D2 recheck, evaluator disagreement review, simplify unnecessary rules; write freeze manifest. | Final candidate definition, prompts, rubric, seeds, backend settings. |
| **5:45–7:15** | Fresh confirmation of the frozen candidate and selected controls. Analyze while batches finish. | Held-out paired results, representative cases, failures preserved. |
| **7:15–8:00** | Complete relevant checks, consolidate artifacts, write final report and update skill-style procedure. | Runnable pipeline and a traceable explanation of conclusions. |

These allocations can shift in response to findings. Two boundaries remain: freeze before confirmation, and reserve the final 45 minutes for a usable report. At 1:00, 3:00, and 5:00 reforecast runtime/cost and drop low-value experiments first. Do not wait until hour seven to discover that the confirmation will not fit.

## 7. Research questions and experiment queue

### RQ1: Does the intended task exist in practice?

First four complete cases should cover different topics and include sufficient evidence, sparse evidence, and an alternative reconstruction. Inspect them directly. Identify whether the failure is bad conversion, insufficiently constrained task design, inability to infer, or an unreliable judge. Fix definition errors before measuring large batches.

A high grounded score with little source recovery is not automatically a student error. It can indicate broad but valid abduction, or that the task is too weakly tied to the intended mathematical structure. Examine the examples; do not silently change the primary score to exact-source similarity.

### RQ2: What clue-generation approach produces usable evidence?

Compare only if the initial converter has a clear failure: concise observations drawn from the solution versus supported rewrites of those same observations. Hold source problems fixed. A contrast between random audited excerpts and curated observations is a useful simple baseline.

Judge acceptance coverage, correctness, joint disclosure, remaining uncertainty, redundancy, and student grounding. Reject the idea of writing hand-coded transformations per topic. Fix global instructions or demonstrations and retest on several sources. Conversion is judged for quality independently of Qwen success.

### RQ3: How much prompting is actually needed?

On identical evidence from 12 D1 sources, run P0 compact zero-shot, P1 same instruction plus one example, P2 plus two complementary examples. Target 150–250 instruction words, excluding clues/examples; measure actual tokens. First pass: 36 responses. Repeat two finalists on a second seed if the difference matters: up to 24 more.

Examples must clarify grounding and permissible uncertainty. Do not stack several examples just to teach the JSON schema. Separate parse/format rate from mathematical correctness. If P2 appears better, note that extra content and extra tokens co-vary; claiming a special benefit of an alternative-answer demonstration requires an equally sized ordinary-demonstration comparison, if time permits.

### RQ4: What amount and presentation of evidence is useful?

Start with count 1,2,3,4 at medium specificity using sentence bullets. Use seeded permutations of each fixed bank, take nested prefixes, and match identities/order across conditions. Repeat a subset with a second permutation to check whether a count result actually depends on a particular clue.

Only then extend the same matched bank to low/high specificity at k=3 and fragment/paragraph representations at k=3. Paragraphs concatenate identical sentences; they must not introduce logical links. Fragments must preserve information. Some clues have no honest specificity refinement; mark ties rather than inventing differences.

The complete first-pass screen has 11 conditions: four counts; two extra specificity levels; two extra formats; answer-only, full-solution, and audited random-excerpt controls. Maximum at 24 development sources: 264 responses. If time is short, keep count + answer-only/full-solution comparisons and defer format. Do not claim full factorial interactions from this screen.

Read two outcomes together: evidence-compatible grounded success and source recovery. More clues tighten constraints and can reduce the set of valid outputs, so a monotonic rise in the primary pass rate is not guaranteed. A lower pass rate alone does not prove worse clues. Use cases to distinguish useful constraints from leakage and arbitrary difficulty.

For the chosen medium bank, a small leave-one-out check can reveal redundant or decisive clues. This is a context-dependent performance effect, not a numerical measure of information in bits.

### RQ5: Can the evaluator distinguish real grounding from superficial success?

Use about 16 authored cases covering valid equivalents/alternatives, wrong answers, contradictory clues, irrelevant clue mentions, ill-posed questions, shortcuts, and unsupported justification. Include matched cases differing in exactly one error and equivalent mathematical answers with different formatting. Keep primary evaluator source-blind.

DeepSeek must substantiate checks instead of merely agreeing with student prose. Repeat a small fixed subset to measure score instability; do not repeat until a preferred label appears. Log false accepts and false rejects separately. If a numeric boundary is unstable, simplify the primary pass criterion and preserve detailed diagnostics rather than adding arbitrary weights.

Any revision to the rubric requires rescoring compared candidate versions under the final evaluator configuration. Old judgments remain in the record. A perfect authored-fixture result does not prove reliability on hard generated questions. Report uncertainty and assistant-reviewed counterexamples.

### RQ6: Does the chosen procedure generalize?

Freeze before C: source IDs, converter/selection/presentation policies, student prompt, few-shot examples, evaluator rubric, model/configuration, and scoring script hash. Freeze protocol before generating C evidence; do not inspect it and then tune the converter. Mechanical/source audits may exclude invalid conversions under fixed rules, with coverage reported.

Evaluate primary policy plus answer-only and full-solution controls, and random excerpts if feasible. Twenty-four sources ×4 conditions ×2 decoding seeds =192 responses; a smaller predeclared run is acceptable if clearly reported. The same source subset must support paired comparisons, or coverage differences must be shown explicitly.

Do not revise using C and continue calling it held out. A serious discovered flaw is a valid finding: label the freeze unsuccessful, diagnose it, and leave the unused reserve for a later clean confirmation.

## 8. Failure-to-action guide

| Observed failure | First diagnostic and next action |
|---|---|
| Qwen begins long generated think content | Inspect the actual chat template/enable_thinking flag; fix serving before changing task prompts. |
| Responses stop mid-proof or JSON | Check finish reason and context/output limits; run a matched cap diagnostic. |
| Converter emits source-question paraphrases | Show a contrastive leakage example in converter/auditor prompts; regenerate matched development banks. |
| Converter invents mathematics | Trace clue support to checked W, correct source or reject; never paper over it in judging. |
| Four-clue bank mostly repeats one fact | Allow fewer honest observations; record coverage; use only valid four-clue banks for count=4 comparisons. |
| Student only guesses a question | Add one concise worked grounding example; check whether justification becomes substantive. |
| Student produces a valid different question and judge rejects | Correct the reference bias; primary judge stays source-blind. |
| Student produces an easy generic problem and receives full credit | Check whether every clue genuinely constrains its solution. If yes, diagnose underconstrained task design rather than inventing a hidden response requirement. |
| Stronger clues increase recovery but mostly reproduce the source | Prefer less disclosure; keep the strong condition as a diagnostic, not a disguised production task. |
| JSON failures dominate otherwise sound responses | Use a tolerant deterministic parser or simplify schema; do not conflate formatting with mathematics. |
| Prompt win disappears on other sources/seeds | Mark tentative or reject the change; do not promote a one-example fix. |
| Judge or mathematical correctness remains uncertain | Record unresolved; review directly and report success bounds if unresolved at reporting time. |

## 9. Runtime, cost, and fallback decisions

Measure real prefill/generation times and output distributions after the first small batch. Forecast wall time from observed median and slow-tail cases. A 16K cap does not mean every response consumes 16K tokens. A sensible planning range is roughly 150–550 student responses; choose based on throughput and research value, not a response-count quota.

Use the previously proposed $5 DeepInfra ceiling unless the user supplies another cap. This is an operational self-limit, not a user-confirmed preference. Track input, output/reasoning, cached discounts only when observed, retries, and pending-request reservations. Check current rates rather than using old V4 constants. Reserve 25% for confirmation. Start concurrency one, raise to two only when stable. No routine request for permission is needed to make authorized small calls within this budget.

Turing is a fallback, not a parallel default run. Trigger investigation if no local generation works by about minute 45–60, or measured throughput/thermal/memory issues threaten the essential experiment. Read cluster instructions and use existing authorized connection details; no GPU work on a login node. Prefer the same GGUF if only moving location. If using vLLM/unquantized weights, label the change and run overlap cases rather than pooling it invisibly with local results. Do not waste hours perfecting local speed when the fallback is available, or assume a cluster queue will be immediate.

## 10. Minimal implementation and meaningful checks

Build only what enables the research loop:

- A local server launcher/health check and a verified DeepInfra client.
- A source split/join and public-only renderer.
- A resumable orchestrator for convert → audit → student → evaluate, with separate source comparison.
- A case viewer/export showing source, clues, response, score, mathematical checks, and costs side by side.
- A comparison/report command reading versioned raw records.

Reuse existing atomic storage and provider-client code where sound. Do not overwrite old SOLVE artifacts. Cache identities must include source ID, evidence and prompt hashes, model/revision/quantization, sampling configuration, and seed. Skip completed identical requests; never reuse outputs after a prompt change. Record transport retries separately from new scientific attempts.

Tests should target real risks: hidden-source leakage into public inputs, cross-split duplicates, incorrect non-thinking template flags, mismatched cache keys, truncated response handling, score/uncertainty parsing, budget accounting, and factual correctness of authored math fixtures. Keep API calls mocked in deterministic tests. Avoid building general-purpose infrastructure unrelated to this pilot.

## 11. Findings, decision records, and reporting

For every meaningful revision record:

```text
iteration_id / time / parent_version
observed_failure and case IDs
hypothesis and expected effect
changed_component / exact prompt or rule diff
comparison sources / evidence IDs / seeds / model settings
before_after_metrics / confidence or uncertainty
mathematical case review, including a counterexample where possible
decision: adopt / reject / uncertain
cost / runtime / next_question
```

Report coverage, grounded success, mathematical answer correctness, clue compatibility, source recovery, proof adequacy, shortcuts, format errors, evaluator uncertainty, truncation, and token/latency cost. Source problems are the independent units; seeds/clue variants are nested observations. Use paired source-level comparisons and bootstrap intervals where sample size supports them. Discovery comparisons are exploratory; do not present the best of many tried prompts as a preplanned significant win.

Final narrative should answer: what is the final task; which earlier definitions failed; what evidence distinguishes inference from copying; which clues and examples mattered; which alternatives should pass; how trustworthy the evaluator is; and what remains uncertain. Use a few complete positive and negative case studies, not just aggregate scores.

## 12. Completion criteria

1. Same original Qwen model ID works in explicitly verified non-thinking mode; exact local configuration is recorded.
2. Reasoning-enabled DeepSeek V4.1 Flash works and spend is accounted for.
3. At least one complete source-to-scored-response path is reproducible from saved public inputs.
4. The final task contract is coherent, concise, and illustrated with correct positive/negative examples.
5. Prompt and clue choices have paired development evidence and direct mathematical inspections behind them.
6. Evaluator failures and uncertainty are characterized; no unsupported claim of human calibration.
7. A frozen fresh confirmation has run, or its precise blocker and the untouched reserve are documented.
8. All raw cases, versioned prompts/configurations, findings, failed hypotheses, and rerun commands are available.

Update [RECONSTRUCT/SKILL.md](../design/reconstruct/SKILL.md), the prompt pack, and the report with measured findings only after execution. No training-benefit claim is warranted until the later cross-task training matrix is run.
