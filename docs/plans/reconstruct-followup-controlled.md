# RECONSTRUCT controlled follow-up

User clarification: the requested 20–75 range concerns mean normalized score, not success rate. Preserve this registered study's grounded-success analysis, but use [the autoresearch protocol](reconstruct-autoresearch.md) for subsequent selection and release. The baseline's low pass rate alone does not mean it misses the requested mean-score band.

Registered before follow-up generations. Historical pilot-v1 is exploratory. D1 and D2 are development; C remains a fresh 24-source confirmation set. No source will be dropped because the student fails.

## Hypothesis and matched interventions

Historical errors often commit to a question before discovering in the justification that its answer is wrong. Test visible verification before final question while keeping non-thinking Qwen3-4B, accepted convert_p2 banks, full-bank sentence evidence, and evaluate_p2 fixed.

- Baseline: student_p1, question first.
- Order-only: student_p5, identical instruction and demonstration semantics, JSON verification first.
- Verify-and-revise: student_p6, verification first with a concise consistency instruction; otherwise the same example.

Run all 12 D2 sources at seeds 0 and 1. Reuse exact cached baseline seed-0 responses, label reuse, and generate seed 1. Student output cap 8192, temperature .7, top-p .8, top-k 20. These are two samples per source, not 24 independent sources. All arms receive identical public clues and ordering per source. Freeze evaluator evaluate_p2; do not change score thresholds to improve student rates.

Primary endpoint: grounded success under the existing score>=3 and all-clue compatibility/grounding checks. Secondary: correct answer, well-posedness, score4, mean score, source recovery, token/latency cost, formatting, and truncation. Report unresolved judgments as missing with lower/upper bounds, never silently discard them. Audit every apparent new success and representative failures directly; distinguish assistant review from independent human labels.

Select highest source-averaged D2 success; ties favor the smallest prompt change, then baseline. If no revision improves, retain baseline and report a negative result. Selection is development only. Preserve all variants and failures.

Before C, save prompt and protocol hashes and selected arm. Run baseline and selected revision on C using seed 0 (two seeds if resources permit); audit conversion independently of student performance and report all 24-source coverage. Do not tune from C results. Pair comparisons on common accepted sources and also report intent-to-evaluate bounds including invalid/missing banks. Fresh confirmation can be informative even at low accuracy; a target performance band is not a validity gate.

Controls on a predeclared topic-balanced C prefix: answer-only and full-solution with the selected prompt. For answer-only, score mathematical validity separately because no displayed clues exist. Recover against the original source to distinguish answer-compatible invention from reconstruction. Controls do not establish training transfer.

## Analysis and claims

Use source as the independent unit. Report Wilson intervals for single-sample binary rates; use paired source bootstrap intervals for source-averaged success differences and exact paired sign/McNemar tests for seed-0 outcomes. No treating clues or seeds as independent sources. Small samples support only limited conclusions. Best means best supported among tested procedures, not globally optimal. Publish generated cases and executable summary code, including failures and exclusions.

Reassess historical wording: format and disclosure screens are suggestive and underpowered; changed rubrics cannot be pooled into one causal comparison. Bank acceptance by the same teacher does not prove mathematical or leakage validity. A separate review must check this, and benchmark readiness requires more than fixture agreement.

Operational budget: retain $5 provider ceiling; use reasoning-enabled DeepSeek V4.1 Flash with low effort and 8192 completion cap. Preserve exact local quantization/runtime. Never expose .env contents.

## Adaptive amendment A (before student_p7 generation)

Inspection of initial p5/p6 outputs found acknowledged answer mismatches surviving into the final question. Add student_p7 on the same D2 sources and seeds: two compact demonstrations of inverse constraint construction, replacing the forward-verification demonstration. This changes demonstration content, count, and wording together; it tests the prompt package, not a causal claim about any one of those components. No C outcomes have been generated or inspected. Include p7 in the same development selection rule and preserve the original three-arm comparison.

## Adaptive amendment B (before role-cue generation)

After inspecting recurring intermediate/target confusions, test an explicit additional answer-role cue. Generate one 6-15-word sentence with convert_role_p1, then compose it mechanically with the complete historical bank. No source numbers, variables, thresholds, formulas, or actual answer may be included in the new cue. The combined bank receives audit_role_p1 for joint leakage before student generation. Accepted banks have 2-5 observations; this is an experimental extension of the earlier 1-4 policy, not a silent change.

Run the existing compact student_p1 at seeds 0 and 1. Compare with baseline on identical sources, retaining rejected banks in coverage and reporting matched accepted-source results separately. This contrasts an evidence package with an added role cue; it does not isolate semantic orientation from one extra clue/token count. The clue may legitimately guide target class, but the premise/target bundle must remain incomplete. Select this task variant only if its D2 grounded success improves on the audited common-source baseline. Freeze before any C conversion. C compares baseline and the selected variant under the same independently audited common banks. No C tuning.

## Audit-boundary correction before role student generation

Source-aware audit_role_p1 falsely counted an unexposed definition in source 73 as public. A wording-only correction, audit_role_p2, still explicitly hallucinated that the definition was public. Therefore audit_role_p3 receives only the public answer and observation sentences, with no source question, worked solution, or hidden support. Existing source-aware support checks are retained for truth; public-only auditing supplies the separate disclosure gate. This is a visibility intervention, not merely another wording variant. All three auditor records remain available, and the source-73 issue has assistant mathematical review in audit-review.json. These development examples do not establish held-out audit accuracy.

The runner now revokes an old acceptance after a newer rejection. A deterministic parser repair for a missing assumptions-list closing bracket also recovers the original student_p7/source-144/seed-0 output with no new generation, preserves its mathematical text and format-error flag, and retains the failure record. This repair applies globally, not according to the response's score.

## Adaptive amendment C: two-call self-revision

After all 96 prompt-screen responses were scored, no prompt-only revision showed a credible improvement. Test student_p8_revision on every baseline D2 response at seeds 0 and 1. Qwen sees its own draft, the same public answer/clues, and a consistency-check instruction. It receives no teacher verdict, source question, or source solution. The primary comparison is paired normalized final score against the original draft; retain final failures. Count both calls and both token costs. This is a two-call policy test, not an isolated prompt or equal-compute reasoning effect. Existing independent baseline draws provide a sampling reference but are not an oracle best-of-two comparator. A winning two-call policy needs a later explicitly budget-matched selection control before attributing benefits specifically to self-revision. No C data are used.

## Adaptive amendment D: position of the supplied answer

Basic local probes produce the correct values floor(100/11)=9 and v_11(100!)=9, while reconstruction drafts assert incorrect values or choose an inconsistent target. This makes input-constraint use a plausible bottleneck beyond raw arithmetic. Test student_p9_answer_last: exactly the baseline instruction, example, schema, and evidence, moving only the final-answer line after the observations. No additional information or demonstration is added. Use all D2 sources and seeds 0/1, evaluate_p2, and the same runtime. Hypothesis: making the supplied answer the last input constraint reduces answer mismatch. Counter-risk: more answer copying or tautological questions. Report both; adaptive development only.

## Adaptive amendment E: baseline disclosure and representation audit

The role experiment accepts only seven of twelve sources, and public-only auditing corrected a source-aware false rejection. Before any count or format sweep, apply the same public-only audit_role_p3 to the original convert_p2 banks on all twelve D2 sources, in a separate copied artifact. There is no role clue in this condition, so the role-specific restriction is inactive. This measures whether the baseline's earlier source-aware acceptance survives the corrected visibility boundary. Do not overwrite historical banks, student outputs, or audits. No student performance selects the audited sources.

Assistant inspection also identified unequal sentence/fragment content: source 95 c2 adds the entire definite integral in fragment form; source 30 c4 replaces an infinite expansion with a finite asymptotic expansion; source 40 fragments omit the squaring derivation. These representation differences preclude interpreting the historical format screen as a pure formatting effect. Preserve those results as exploratory packages. Before a new format comparison, make equivalent renderings of the same public propositions and record an equivalence audit; ordinary sentence versus concatenated paragraph can be isolated mechanically without rewriting facts.

Decision: if full banks fail joint disclosure, investigate sparse globally selected subsets or a globally revised converter before promoting a baseline. A smaller subset is not automatically valid: audit the exact public subset for interpretability and support. Count comparisons use common eligible source families and retain all exclusion denominators. Thresholds and the Qwen scoring rubric stay fixed.

## Adaptive amendment F: sparse observations with answer-role guidance

Registered before sparse-bank composition/auditing or student generation. The full-bank role policy has 58.3% accepted coverage, below the 80% target, while its matched seven-source mean improves by 10.71 points with a wide interval including zero. Test whether retaining two randomly selected original observations plus the same broad role cue preserves useful orientation with less disclosure.

Use all twelve D2 sources, fixed clue-selection seed 0, and the existing convert_p2 banks and convert_role_p1 cues. Select the first two observations from choose_clues' fixed seeded permutation; do not select by observed Qwen outcomes or manually edit sentences. Construct two banks per source: those two observations alone (base_sparse_2), and those same observations plus the existing role cue (role_sparse_2). Shuffle the two base observations identically in both student conditions, with role appended. Each exact public bank must pass public-only audit_role_p3 before inference; existing source-aware support records remain necessary provenance. Rejected role cues remain rejected; do not silently regenerate source 40's numerical role.

The first endpoint is audit coverage and disclosure defects on all twelve sources. If at least ten role banks pass, proceed to a four-source mechanical smoke check using the first four accepted source IDs, then all accepted sources at decoding seeds 0/1 if the mechanics are correct. Do not stop or expand based on the four-source scores. If fewer than ten pass, report the coverage failure and inspect conversion globally before a large student run. Compare Qwen scores on the common eligible sources, report exclusions separately, and retain all original full-bank results. This tests a sparse evidence policy, not the effect of role semantics at equal information or a proven optimum clue count.

Keep student_p1, evaluate_p2, runtime, sampling, token cap, and rubric fixed. No C data. Provisionally retain only if coverage meets the existing goal and direct review supports meaningful missing structure, then seek fresh-source replication. Merely increasing score by leaving decorative clues or permitting answer copying fails the intended task.

## Reserve allocation before fresh-source experiments

The reserve is now frozen in `data/manifests/reconstruct-reserve-allocation-v1.json` by `scripts/allocate_reconstruct_reserve.py`: seed 20260922, three fresh development sources (D3) and six untouched replication sources (R) per broad topic; remaining sources are contingency. D3 has 12 sources, R has 24, and contingency has 29. Allocation uses topic and a seeded shuffle, not student outcomes or hand-selected question content. Original D1/D2/C partitions remain unchanged. D3 is explicitly development once inspected; R is not to be tuned against.

An automated digit-masked equality and character-five-gram Jaccard screen (threshold0.8) flagged no pairs. This is a lexical screen with a design-chosen threshold, not proof of independent mathematical families. Inspect possible semantic relatives before any source-family-disjoint confirmation claim; do not quietly discard hard sources during that review. No fresh-source model outputs are generated by allocation.

## Adaptive amendment G: capability and information controls

Before control generation, freeze the same four source IDs selected for amendment F's mechanical smoke: 11,22,30,49. Run local Qwen student_p1 at seed0 with (a) answer only and (b) the complete checked solution. Keep the checkpoint, quantization, non-thinking mode, sampling, and8192-token cap unchanged. These deliberately change available information and are diagnostic controls, not legal sparse-task candidates. Store them separately from the concurrent sparse comparison.

Judge with evaluate_p2 and inspect each proposed question mathematically. Report score and well-posed answer correctness; do not call an answer-only success evidence-grounded reconstruction. Compare original-source recovery separately if measured. Full-solution success tests ability to extract a question when information is sufficient; it does not establish successful direct SOLVE or isolate reasoning mechanisms. These four sources are development probes, not an independent accuracy estimate.

A further source-blind DeepSeek reconstruction probe may use exactly the same four sparse role inputs and student_p1 instruction, with reasoning enabled. It must see no original question/solution/support. This tests feasibility with a stronger model; its own grading is not independent gold, and mathematical review is required before counting successes. Do not pool teacher outputs with Qwen or present this as evidence that Qwen will learn the task.

## Adaptive amendment H: production-derived evaluator boundary controls

The information-control judge rejected source11's question with gap ratio1:2, despite its literal two-gap interpretation giving the unique answer4. Preserve this as a linguistic adjudication issue: repeat the exact case and pair it with an explicitly stated three-divisor version. The original case's expected score3–4 is conditional on interpreting the ratio list as complete; do not treat agreement/disagreement alone as conclusive judge accuracy on ambiguous wording. The clarified case has an unambiguous mathematical reference.

The source-blind teacher reconstruction for source49 chose r=1,p=0 and a valid asymptotic limit, but F(x)-x=-x^2 does not change sign at p=0 as the displayed clue requires. Add this as a clue-violation control (expected score1), paired with a correct r=2 scaled recurrence with limit1 (expected score4). Save algebraic certificates and all original records. Use unchanged evaluate_p2, low reasoning,8192 cap. These are adaptive development controls, not independent held-out validation and not four independent source families. No rubric revision or student rescoring follows without inspecting these results.

## Amendment I: fresh D3 source preparation and nested-count study

The sparse role comparison is complete:22 outputs per arm, means29.55 without role and26.14 with role, paired difference-3.41 with interval[-11.36,2.27]. It provides no support for adding the role. Stop adapting that prompt family on D2. Move to the frozen D3 development allocation and compare evidence quantity while retaining convert_p2 and student_p1.

Before D3 calls, `scripts/prepare_reconstruct_d3.py` saves mathematical source reviews. Source20 is flagged for unresolved primitive-root/domain notation: x=1 is allowed under one reading and gives3 instead of-4. Preserve it in the twelve-source denominator; do not silently repair or replace it. Source136's explicit option A maps to87429. A general tested option-label lookup performs that normalization with provenance, leaving original sources unchanged. Eleven sources are eligible for conversion. This is source-quality screening before student outcomes, not performance-based filtering. Independent human review has not occurred.

Start with a four-source conversion smoke check on the first four eligible IDs8,27,33,77, then complete all eleven with unchanged convert_p2 if the mechanics are sound. Audit support and sentence interpretability using audit_support_p1 with source access, then disclosure using public-only audit_role_p3. Acceptance requires BOTH; a public acceptance cannot override a support rejection. Unused fragments are excluded from this sentence-only support audit and cannot later be treated as equivalent-format evidence without review. Save all attempted/rejected banks and both source-pool and conversion-attempt coverage.

After bank audits, fix eligibility before student inference. Compare nested prefixes of the same original-bank permutation at k=1,2,3 and complete bank, using clue-order seed20260920 and decoding seeds0/1. No new synthesized subset bank or reshuffling is allowed: choose_clues(bank,k,seed) must be the prefix of choose_clues(bank,full,seed). Reuse identical full/k3 inputs when a bank has exactly three clues and label that reuse. Report count1–3 comparisons on common eligible banks with at least three clues; report separate coverage for shorter banks rather than padding them. A k4 effect is estimable only on four-clue banks; full-bank versus fixed-count is a policy comparison elsewhere. If fewer than eight original D3 sources qualify for the count1–3 comparison, diagnose conversion before a broad student sweep; preserve this failed-coverage outcome.

Keep evaluate_p2, runtime, non-thinking Qwen, sampling, and token cap unchanged. Current evaluator boundary disagreements and technical failures remain explicit limitations. D3 is development, not confirmation; no C or R outcome is used. Any format comparison later uses exactly equivalent facts, beginning with mechanical bullet-to-paragraph rendering. Do not claim that k=2 is optimal from the prior sparse-role experiment.

Before the first D3 support audit, clarify its semantics: observations are local assertions from an unknown mathematical setup, not universal identities over unspecified variables. A withheld source constraint is part of the intended inverse inference, not automatically a support defect. Verify truth against the independently reviewed source setting and require a readable assertion; reject unresolved references or false claims. This clarification does not expose missing premises to Qwen. Public disclosure remains a separate conjunctive gate, and no D3 student results have been observed.

## Amendment J: audit the actual disclosed prefix, not only its parent bank

Before subset composition/auditing or D3 student inference, full-bank public audits reject at least sources8,33,86 for exposing complete solutions. With source20 unresolved upstream, at most8/12 original sources can qualify under the full-bank policy, below the predeclared80% coverage goal. Preserve that policy failure rather than weakening the leakage rule.

Materialize k=1,2,3 prefixes of each source-supported original bank's single seeded permutation (20260920). Keep every sentence byte-for-byte unchanged and preserve its position; no new clues, weakening, alternative seed search, or source-specific edits. Each materialized bank stores the original bank key, selected IDs, order seed, and exact fixed presentation order. The student runner must refuse a different order seed or partial selection from that already-audited materialized input.

Inherit support checks only for unchanged selected assertions from an accepted audit_support_p1 record, with an explicit provenance reference; this is not a fresh teacher judgment. Audit every exact public prefix with audit_role_p3. Require inherited support AND public acceptance. A full-bank rejection remains recorded but does not automatically reject a smaller public input. This is a globally specified exposure policy change, not cherry-picking the clues that produced good student answers. All eligible sources enter every feasible k's audit denominator; source20 and operationally missing banks remain visible in all-source coverage.

Freeze count-specific accepted IDs before inference. Compare k=1,2,3 on the common accepted set if at least eight original D3 sources qualify; otherwise report the failed common-coverage gate and diagnose the input policy before a broad sweep. Also report each count's separate coverage and score distribution on its accepted sources when studied, clearly separating matched effects from selection differences. Full-bank results remain a separate policy with their own eligibility. Reuse identical inputs only with explicit response-key provenance, never treating reused calls as independent samples.

Retain student_p1, evaluate_p2, decoding seeds0/1, non-thinking mode, original Qwen checkpoint/runtime, and8192 cap. D3 remains development. No C/R data or Qwen outcomes determine the prefix audits or eligibility. The initial result estimates this fixed selection policy; it does not establish an optimal random seed or robustness across all subsets.

## Amendment K: diagnose a measured auditor reasoning-budget exhaustion

The improved failure recorder establishes that the D3/source136 public audit used all8192 completion tokens as reasoning, finished for length, and produced no visible answer. This is direct evidence of budget exhaustion for that request, unlike earlier empty responses whose usage was lost.

Probe an explicitly separate operational condition on sources8 and136 with the identical public-audit prompt/model, low reasoning and temperature0, but completion cap16384 and timeout300 seconds. Source8 is a previously resolved rejection control; source136 is the measured exhaustion case. This is a targeted completion-budget/timeout package check, not an unbiased accuracy sample or proof that16384 is optimal. Preserve the original failed request and existing labels. Start a separate artifact with empty audits so the cache cannot reuse8192-token judgments. Do not merge these records into the count-study labels or change its settings silently. Adoption of a new audit budget would require explicit recording and consistent handling of compared conditions.
