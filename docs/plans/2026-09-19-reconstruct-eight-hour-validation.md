# Eight-hour RECONSTRUCT setup and validation plan

**Superseded:** use the [20 September adaptive research plan](2026-09-20-reconstruct-adaptive-eight-hour-plan.md). The user requires the original `Qwen/Qwen3-4B` from earlier results with thinking disabled, not Instruct-2507. The environment variable is now `DEEPINFRA_API_KEY`. Model-choice and key-name statements below are retained as historical planning context only.

Status: plan with hardware and model-catalog preflight completed; no local inference server, paid completions, or reconstruction experiments have run in this phase. Time blocks are relative to the start of execution. The eight-hour target is a working, measured pilot and frozen candidate protocol, not a completed training-transfer paper.

## Objective and scope

Make the RECONSTRUCT pipeline work end to end using local non-thinking Qwen3-4B Instruct as the student and reasoning-enabled DeepSeek V4.1 Flash on DeepInfra for conversion, auditing, reference generation where needed, and evaluation. Establish whether concise prompts and a small number of examples produce mathematically grounded reconstruction from incomplete evidence. Preserve its role as one condition in the SOLVE/JUDGE/RECONSTRUCT training-transfer study.

Complete setup first; increase experiment volume only after operational and scoring checks pass. Keep the current [task specification](../design/reconstruct/SKILL.md) as the mathematical contract, but this plan supersedes its initial model, decoding, and full-factorial execution defaults for the first eight hours. The 36-cell factorial remains a possible later study.

## Preflight findings

Observed on the laptop:

- Intel Core Ultra 7 155H; NVIDIA RTX 3050 laptop GPU with 6 GiB VRAM, nearly idle when checked.
- About 15 GiB system RAM, only 3.3 GiB available, and significant swap already in use. About 19 GiB free disk.
- CUDA toolkit 12.0 and NVIDIA driver 580.178.04 present. Driver-reported CUDA capability is not the installed compiler version.
- `uv`, `cmake`, `nvcc`, and SSH are present; `llama-server`, Ollama, and the repository `.venv` are absent from the inspected paths/PATH.
- Existing Hugging Face cache includes original `Qwen3-4B`; the inspected entries do not establish that the required Instruct-2507 checkpoint or GGUF is cached.
- `.env` contains nonempty `DEEPINFRA_KEY`; the existing SOLVE client expects `DEEPINFRA_API_KEY`. Support both names in the new client without printing the value or editing the user's secret unnecessarily.
- A model-list request with the configured credential returned HTTP 200 and listed `deepseek-ai/DeepSeek-V4.1-Flash`. This establishes catalog access, not that a paid reasoning completion succeeds.
- Existing runners default to older `deepseek-ai/DeepSeek-V4-Flash-0731` and `Qwen/Qwen3-4B`. Historical results must remain separately labeled.
- The ignored local Turing guide mentioned by README is absent. Do not guess credentials, paths, or scheduler rules.

## Fixed model choices and runtime checks

### Student

Use **Qwen/Qwen3-4B-Instruct-2507**, whose [official model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) describes it as non-thinking-only. Do not substitute original Qwen3-4B with a prompt saying not to think, and do not use the Thinking-2507 checkpoint.

Primary local backend: CUDA-enabled llama.cpp server, loopback interface, one inference slot. Use a pinned, provenance-checked Q4_K_M GGUF conversion of the exact checkpoint; [Unsloth's conversion](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF) is a candidate. Record repository revision, filename, SHA-256, tokenizer/chat-template identity, and llama.cpp build commit. Do not download multiple full checkpoints speculatively.

Starting resource configuration: 24,576 context tokens, 16,384 maximum new tokens, GPU offload, and quantized KV cache if needed and supported by the pinned build. Context must include both input and output. Reject an oversized request explicitly rather than clipping evidence or silently shifting the context. Use [llama.cpp's server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) and the installed build's help to determine exact flags.

Starting sampling: temperature 0.7, top_p 0.8, top_k 20, min_p 0, fixed recorded seeds, following the official model's guidance. A large output cap is headroom, not an instruction to produce a long response. Ask for concise justification. Log termination reason, output length, repetition, and any apparent reasoning-channel output.

If 24K context does not fit, first check KV-cache precision and buffer sizes. A 20K context can still accommodate a compact prompt and 16K output headroom. Do not silently shorten completion budgets to force memory fit. CPU offload is a measured fallback, not the initial assumption. Do not kill unrelated processes or delete caches to reclaim memory.

Briefly compare 8K versus 16K output caps on a fixed development subset after smoke tests, checking truncation and task outcomes. Keep 16K as the main cap unless evidence justifies a global change before freezing. Length-stopped outputs remain recorded; targeted diagnostic reruns must not replace failures in the original condition.

Quantization is part of the experimental configuration. Label all local results accordingly. A BF16 Turing run is a separate condition; do not merge it invisibly with the GGUF results or historic Qwen results.

### Teacher and evaluator

Use **deepseek-ai/DeepSeek-V4.1-Flash** through `https://api.deepinfra.com/v1/openai`. The [DeepInfra model listing](https://deepinfra.com/deepseek-ai/DeepSeek-V4.1-Flash) and live catalog confirm the ID. Before experiments, confirm its currently supported reasoning parameter/schema using provider documentation and one tiny completion. Do not assume the old V4 client's `reasoning_effort="medium"` has unchanged semantics. If the requested configuration is unavailable, report it rather than silently substituting a model.

Use reasoning for all substantive teacher/evaluator calls. Pin the accepted reasoning setting after the smoke test and record it. Start with a 16K completion budget inclusive of any provider-counted reasoning; raise globally to 32K before the pilot if reasoning exhausts the cap before producing valid output. Detect empty visible content, incomplete JSON, and length stops. A larger cap is not an excuse for verbose instructions.

Preserve response usage, finish reason, latency, request configuration, reasoning-token accounting where provided, and visible output separately. Initial concurrency one; increase to at most two only after success and with spend reservations. Retry only transport/rate-limit failures with a bounded policy and request ledger; do not retry mathematical failures until they pass.

### Budget

A spending-cap preference has been requested. Pending an answer, use a conservative **$5 total operational ceiling**, including reasoning, input, output, retries, and judge calls. The user's request authorizes DeepInfra use; this ceiling is a self-imposed limit, not evidence of an answered budget question.

DeepInfra's [catalog](https://deepinfra.com/) currently displays standard V4.1 Flash rates of $0.20/M input and $0.60/M output, with other discounted displays also appearing. Recheck the actual service tier at execution; reserve costs using the higher applicable rate and no assumed cache discount. At $0.60/M, a 16K output ceiling alone is about $0.01 per call, so hundreds of teacher/judge calls still require a real cost ledger.

Reserve each request's maximum plausible input/output spend before submission and update from returned usage. Count reasoning once according to provider billing, not again if already included in completion tokens. Reserve at least 25% of the total ceiling for confirmation and reporting diagnostics. If actual prices, usage semantics, or balance cannot be established, stop expansion at the small smoke stage and report the uncertainty.

## Eight-hour schedule

| Time | Work | Exit evidence |
|---|---|---|
| 0:00–1:00 | Set up isolated dependencies and pinned llama.cpp CUDA runtime; download one GGUF; fix client key-name compatibility; local health check and tiny DeepInfra reasoning call. | Both endpoints respond; exact identities/settings logged; local memory and throughput measured. |
| 1:00–2:00 | Build a small resumable reconstruction runner around existing storage/client utilities. Test 4–6 development sources with short prompts and no demonstrations initially. | Conversion → audit → Qwen → evaluator works; public/private separation and failure handling verified. |
| 2:00–3:00 | Inspect actual failures, calibrate judge with authored controls, and compare three bounded prompt strategies on 12 development sources. | Evidence-backed global prompt revision; no per-source hand fitting. |
| 3:00–5:00 | Run matched clue-count, disclosure, and format comparisons on up to 24 development sources. Add length-cap and limited repeatability checks. | Complete paired condition tables within the measured throughput/spend budget; documented exclusions and uncertainty. |
| 5:00–6:00 | Recheck scoring failures, inspect representative successes/errors, select and freeze one candidate policy. | Prompt/configuration hashes, chosen count/disclosure/format, revised definition where evidence requires it. |
| 6:00–7:15 | Evaluate frozen policy and controls on a preselected fresh confirmation subset. | Held-out results with no tuning on that subset. |
| 7:15–8:00 | Consolidate artifacts, run relevant implementation checks, write findings and remaining limitations. | Reproducible commands, raw records, measured report, updated skill-style procedure. |

These are time allocations, not promises of throughput. If setup takes longer, reduce experimental breadth and retain a valid frozen confirmation. Stop launching bulk requests at 7:15 and finish/report in-flight work. Do not spend the reporting window filling a sweep that will remain uninterpretable.

## Staged experiment design

### 1. Separate source data before prompt iteration

Use the existing 113-source teacher-correct pool, joined to worked solutions by stable source ID. Audit solution correctness where it supports clues; gold-answer agreement alone is insufficient. Group duplicates and examples too close to demonstrations before splitting.

Preselect 24 development sources balanced across the four available topics, 24 confirmation sources (six per topic where coverage permits), and leave the rest unused. The smoke sources and 12 prompt-comparison sources are nested subsets of development. Never choose confirmation examples after seeing Qwen's reconstruction performance. Any reduction for runtime uses a predeclared balanced prefix and is decided before confirmation outputs are inspected.

Record conversion failures and eligibility. A source lacking four honest observations must not be padded. It can contribute to a smaller-k production analysis if declared, but count comparisons use one common eligible subset. Preserve coverage by topic/difficulty and do not filter by Qwen success.

### 2. Start with short prompts

Keep the full specification as an operator reference. Send each model only the compact instructions relevant to its role. Initial student instruction should fit roughly 150–250 words, excluding actual clues. Ask for a question, concise verification, and assumptions. Use a compact converter schema and a short judge rubric. Do not send entire markdown files, administrative sections, or the hidden source to the student.

On the same 12 development sources and fixed clues, compare:

- **P0:** compact instruction, zero-shot.
- **P1:** same instruction plus one clear reconstruction example.
- **P2:** same instruction plus two examples, with the second demonstrating a valid alternative and its grounding.

First pass: 12 ×3 = 36 Qwen responses. Compare the two finalists on a second decoding seed: up to 24 additional responses. Separate schema-following gains from mathematical gains. Choose examples to clarify the contract, not mirror specific test templates. Permit at most two documented global revision rounds on development within this window.

Hold clues fixed during the student-prompt comparison. If converter prompts change, freeze a newly generated bank version and rerun the affected paired comparisons; never compare prompt variants using different evidence without labeling the confound. New strategy hypotheses discovered after examining development results are exploratory.

### 3. Validate the score before ranking strategies

Create a small authored suite containing correct source-equivalent questions, valid alternative questions, correct answers with incompatible clues, wrong answers, missing essential proofs, ill-posed questions, answer-copy shortcuts, and equivalent output formatting. Aim for 16 controls, repeated once on a subset to check evaluator stability.

DeepSeek evaluates only public evidence and the response. Source recovery is a separate diagnostic. Verify simple mathematical fixtures deterministically where possible. Inspect a stratified sample of actual outputs and manually document concrete mathematical certificates/errors. Repeat a small judge subset to detect unstable decisions, not to manufacture a majority label after unlimited retries.

An assistant review and repeated DeepSeek calls are not an independent human annotation study. The two-human reliability check in the longer protocol remains outstanding unless human annotations are actually obtained. Report pilot scoring as provisionally validated, with unresolved cases and success bounds. Do not claim human agreement statistics from model-generated judgments.

### 4. Controlled clue screening

Use one audited bank per source with nested subsets and matched order. Freeze the student prompt before this screen. Recommended first-pass grid is **11 conditions**, not the earlier 36-cell factorial:

| Factor / control | Conditions |
|---|---|
| Count | k=1,2,3,4; medium disclosure; sentence bullets |
| Disclosure | low and high at k=3; medium is already in count grid |
| Format | fragments and paragraph at k=3, medium; bullets already included |
| Baselines | answer only; full worked solution; audited random excerpts matched to k=3 where feasible |

Maximum 24 ×11 = **264 Qwen responses** for one decoding seed. Sentence bullets and paragraph use identical sentences; fragments preserve the same facts. Disclosure levels vary information while preserving observation identities. Excerpt lengths are reported rather than treated as automatically matched.

This estimates simple effects around a fixed operating point. It does **not** identify the full count×disclosure×format interaction surface. If there is time, repeat the primary condition on a second seed and check a small predeclared count×disclosure subset. Otherwise defer interaction claims.

Run the 8K/16K cap check on 12 fixed development examples, up to 24 outputs. Record latency, tokens, termination and mathematical score. Analyze whether a cap truncates outputs rather than selecting whichever cap happens to improve accuracy on a tiny sample.

### 5. Freeze and confirm

Choose a globally applied policy using clue validity, meaningful remaining uncertainty, primary grounded performance, source-recovery diagnostics, shortcut rate, and evaluator stability. Do not force a medium percentage or choose a weak rubric to make scores attractive. Accuracy alone is insufficient because vague clues can admit easy constructions.

On 24 held-out sources compare the chosen policy, answer-only, full-solution, and audited random excerpts; two student seeds give up to **192 responses**. If measured runtime permits only 12 balanced sources, declare that before starting confirmation, yielding 96 responses. Do not tune on these results. If a critical flaw is discovered, label confirmation failed and any subsequent work exploratory; preserve an untouched set for later confirmation.

Maximum main student work is roughly 60 prompt-comparison +264 clue-screen +24 length-cap +192 confirmation = **540 responses**, plus a few smoke and optional repeatability responses. This is an upper planning target, not a launch command. The minimum useful outcome is a small working end-to-end run, interpretable prompt comparisons, validated fixtures, and a frozen small confirmation, with complete failure accounting.

## Throughput decision and Turing fallback

Measure prefill and generation latency on real short/long pilot prompts. Forecast remaining wall time from observed token lengths and p50/p90 latency, not the maximum completion cap or advertised tokens per second. Compute the feasible source/condition budget after reserving confirmation and report time.

Use Turing only if the laptop cannot load the required configuration, suffers persistent memory/thermal failures, or measured throughput makes the core pilot infeasible. Read the cluster skill and discover existing authorized connection details before any remote job. Never run the GPU model on a login node. Queue availability may prevent a same-night fallback.

Prefer the identical GGUF/checkpoint/settings remotely when changing only execution location. If a different precision/backend is necessary, create a separate labeled run and perform a small paired overlap check. Do not pool precision changes as if they were more random seeds. No arbitrary model substitution.

## Implementation requirements

Reuse existing atomic storage and provider-client patterns where suitable. New work should be a small configurable pipeline, not a second training framework:

1. Local server launch/health/stop commands with PID ownership and no public network binding.
2. Configuration-driven local and DeepInfra clients, environment-name compatibility, reasoning setting verification, token/cost accounting, timeouts, and bounded transport retries.
3. Source grouping/splitting, audited bank generation, public-only rendering, student inference, primary evaluation, and separate source comparison.
4. Resumable records keyed by source, prompt hash, evidence hash, model revision, sampling configuration, and seed. Never reuse a cached response under a changed prompt or configuration.
5. Relevant tests for private-field exclusion, split integrity, cache identity, parser behavior, uncertain judgments, length-stop accounting, and budget reservations. Mock network responses for deterministic checks.
6. A report including every attempted condition, eligibility, failures, unresolved evaluations, quantization, throughput, costs, and source-cluster uncertainty. Do not count repeated generations as independent source problems.

Store large weights/builds/raw transport artifacts under ignored local paths; curate only useful manifests, prompts, code, and result summaries. Do not overwrite historical SOLVE results. Guard API keys from logs and reports.

## Eight-hour deliverables and honest limits

- Working local non-thinking student and a tested reasoning-enabled DeepInfra client, with exact reproducible settings.
- One functioning RECONSTRUCT path from checked source through scored student output.
- Short prompt versions with measured zero-/one-/two-shot comparisons.
- A modest controlled clue study, groundedness/shortcut diagnostics, and a frozen held-out pilot.
- Updated specification, prompt pack, rerun commands, and a report explaining changes with examples.

Not promised in eight hours: a globally best prompt, exhaustive factorial conclusions, a human-calibrated evaluator without human labels, completed SFT/RL training, or the final cross-task transfer matrix. Those follow once RECONSTRUCT is stable enough to serve as a training/evaluation condition.
