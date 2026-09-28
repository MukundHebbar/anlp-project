# RECONSTRUCT autoresearch: protocol, decisions, and evidence

Latest execution: the user-directed richer-information bracket reached2 verified development recoveries in6 scheduled examples, with one disclosed mathematical adjudication. [Report and candidate](../../artifacts/reconstruct/bridge-composition-ax/decision.md). The immediate recovery goal is achieved; next work is fresh validation and remaining distribution/judge requirements. Historical queues below are not instructions to rerun completed studies.


Current execution priority supersedes historical queues below: [consolidated protocol](../design/reconstruct/CURRENT_PROTOCOL.md), [evidence report](../research/reconstruct/current-evidence.md). AP/AS independent math and AT judge-scope calibration are complete. No candidate is promoted; independent reference validation and resolution of the remaining judge errors precede new generator selection. No confirmation or final candidate is authorized by a historical pilot selection.


Status: execution plan. Targets below are acceptance criteria, not achieved results. This plan supersedes the scheduling guidance in the earlier eight-hour plan; previous raw runs remain immutable evidence. The user confirmed that the Qwen target is **average rubric score 20–75 out of 100**, not a 20–75% success rate.

Current execution queue: [next-session plan](reconstruct-next-session.md), superseding sections11 and13 below. **Latest user requirement:** [grounded semantic recovery and strict disclosure](reconstruct-semantic-recovery-gates.md) adds at least5/25 grounded reconstructions of the same essential original question and mandatory leakage checks. This overrides earlier descriptions of recovery as merely diagnostic. Historical rubric scores remain unchanged; the new joint endpoint is additional.

## 1. Objective and scientific scope

### Additional user requirement: fixed generator with a middle-heavy rating distribution

Treat a stable, middle-heavy distribution as a development selection objective alongside validity, semantic recovery and coverage. On a five-level 1–5 display scale, prefer rating3 as the most common category, ratings2 and4 as intermediate-frequency categories, and ratings1 and5 as uncommon tails. This is an ordinal shape preference, not a Gaussian assumption, an exact quota, or a requirement for perfect symmetry. Numerical tolerances have not been specified; do not invent them after seeing confirmation results.

The current stored rubric is0–4. For display only, rating1–5 equals stored score+1; normalized score remains25*(display rating-1). Preserve historical labels and rubric meanings. Do not silently reinterpret an old zero as20/100 or treat the displayed rating as a correctness probability. A future substantive rubric revision requires independent calibration and a versioned comparison.

Compare fixed conversion procedures on the same preselected development sources. Each procedure must specify its prompt/examples, clue-selection policy, model settings, retry/abstention rules and fixed judging rubric before its run. Adjust global conversion policies between registered development experiments; do not adjust individual examples until Qwen receives a desired rating, change judge severity to shape the histogram, or discard low/high outcomes. If using an information-level mixture, freeze its weights and source-independent assignment before confirmation.

Every comparison must report counts at all five rating levels, the valid-score denominator, missing/invalid outputs separately, conversion eligibility over all allocated sources, and semantic/grounded recovery. Use source-balanced summaries when multiple seeds are present. A middle-heavy histogram is useful only if partial-credit labels are independently justified; it cannot compensate for leakage or incorrect judging. Freeze the selected generator and evaluator before fresh confirmation and report the observed distribution, including a failure to match the desired shape. Retain the existing20–40% semantic-recovery, at-least5/25 grounded-recovery and mean20–75/100 objectives as separate criteria.

Develop a simple, few-shot RECONSTRUCT procedure that presents a final answer and sparse, supported solution observations, then asks for a plausible self-contained question and concise grounding verification. Preserve meaningful uncertainty without exposing the original premise-and-target bundle. Valid alternative questions may pass.

The main project remains controlled transfer among SOLVE, JUDGE, and RECONSTRUCT. This study calibrates the third task. It cannot establish training transfer or prove that the tasks correspond to independent cognitive mechanisms.

Success means all three conditions hold together:

1. The frozen Qwen procedure has mean normalized score in the requested 20–75 range on fresh data, with its distribution and grounded-success rate reported.
2. Conversion produces mathematically supported, partial, interpretable evidence at useful coverage; it does not attain apparent correctness by rejecting almost everything.
3. DeepSeek judgments agree closely with independently established mathematical labels, including difficult wrong answers and valid alternatives.

“Best” means the simplest reliable version supported by comparisons among the tested alternatives under stated data and compute limits. No finite sweep proves global optimality. Do not keep inspecting the same test set until all thresholds pass.

## 2. What the existing evidence says

Read [the historical pilot](../research/reconstruct/pilot-2026-09-20.md), [the validity audit](../research/reconstruct/followup-validity-audit.md), and [the registered follow-up](reconstruct-followup-controlled.md) before proposing more variants.

- Historical D2: mean 1.33/4 = 33.33/100, but only 1/12 grounded successes.
- Follow-up baseline at seeds 0 and 1: mean 1.25/4 = **31.25/100**, with 2/24 grounded successes across 12 sources. Both seeds have 1/12 successes. This already meets the numerical mean target on development data.
- The final pilot judge passed 11 authored fixtures. That is a smoke test, not evidence of near-perfect accuracy on generated cases.
- D2 errors include choosing an intermediate quantity as the target, computing an answer different from the supplied answer, omitting necessary conditions from the actual question, and attaching unused clues.
- The completed 96-output prompt screen gives means of 31.25, 32.29, 29.17, and 27.08 for p1/p5/p6/p7. All paired source-bootstrap difference intervals include zero. Retain p1 provisionally for simplicity; this is not equivalence or superiority evidence. See [the completed screen](../../artifacts/reconstruct/followup-v2/prompt-screen.md).
- Role augmentation, self-revision, answer placement, and the sparse-role comparison are now analyzed. None supports adopting added role guidance or extra revision compute. Copied artifacts contain imported records; raw record totals are not new experiment sample sizes. See [the evidence index](../../artifacts/reconstruct/followup-v2/evidence-index.md).
- Updated validity finding: public-only re-auditing rejects baseline source 131, which accounts for both baseline grounded successes. On the eleven accepted banks the baseline has 0/22 grounded successes, despite mean 26.14/100. Preserve the original results and report this post hoc [validity sensitivity](../../artifacts/reconstruct/followup-v2/baseline-validity-sensitivity.md). A numerical mean in range is demonstrably insufficient here.

The first priority is therefore measurement and conversion validity, followed by controlled task improvements. Merely moving the mean inside the requested interval is already insufficient to justify the task.

## 3. Fixed definitions and release gates

For source i and decoding seed s, let y_is be the existing integer score 0–4 and z_is = 25*y_is. Average seeds within each source first, then average equally across sources. A normalized score is a rescaled rubric score, **not percent correct**; the ordinal scale also limits interpretation of small differences.

Keep these outcomes separate:

| Outcome | Meaning |
|---|---|
| Mean normalized score | Primary requested difficulty measure, 0–100 |
| Score histogram | Whether the mean consists of genuine partial work or mostly wrong attempts |
| Grounded success | Score >=3, well-posed, independently correct answer, no shortcut, all displayed evidence substantively grounded |
| Full verification | Score 4 |
| Exact/related source recovery | Diagnostic against the private source; not the primary validity rule |
| Conversion coverage | Accepted source banks / all attempted source banks |
| Judge abstention | Unresolved judgments / all submitted outputs |
| Operational failures | Missing, malformed, truncated, timed-out, or thinking-mode outputs |

Proposed release gates:

| Component | Required evidence | Gate |
|---|---|---|
| Qwen difficulty | Frozen protocol, source-disjoint confirmation, source-bootstrap interval | Mean and its 95% interval contained in [20,75]; report sample size and all score bins |
| Mathematical usefulness | Direct review of successes and partial-credit cases | Demonstrated substantive reconstructions on multiple source families; no claiming usefulness from an all-score-1 mean of 25 |
| Accepted-bank validity | Independently reviewed accepted banks | Target >=98% valid, with 95% lower confidence bound >=95% before claiming near-perfect quality |
| Bank leakage | Review of whole public inputs, not individual sentences alone | Target <=2% direct-restatement/full-solution defects; publish counts and upper confidence bound |
| Conversion coverage | All preselected sources included in denominator | Target >=80%; report topic/answer-type exclusions and retry counts |
| Judge pass/fail correctness | Frozen independent reference cases, balanced valid/invalid conditions | Target >=98% overall and 95% lower bound >=95%; inspect class-specific performance |
| Dangerous false acceptance | Wrong-answer, contradiction, tautology, and unsupported-clue controls | No unresolved systematic false-accept pattern; bound false-accept rate, not just overall accuracy |
| Judge scoring | Reference score ranges and duplicate blinded scoring | Target mean absolute score error <=0.25/4, weighted kappa >=0.80 where applicable, report pass/fail flips |
| Judge coverage | All outputs submitted, no selective abstention | Target >=95% resolved; report conservative bounds for the rest |

The 98%, 95%, 80%, and agreement thresholds are **predeclared quality goals**, not experimentally proven hyperparameters. Record any later change and its reason before fresh validation. Do not quietly relax them to declare success. If reference labels cannot be independently established, label the gate unverified.

About 200 genuinely independent reference cases with 196 agreements can support a roughly 95% lower accuracy bound. Twelve or twenty perfect cases cannot. Several edits of one source are one family for uncertainty analysis; do not present 200 correlated perturbations as 200 independent sources. Exact binomial calculations are appropriate only when their independence assumptions hold; otherwise bootstrap source families.

## 4. Data separation and reference construction

Use the existing partition manifest, not a new convenient sample:

- D1: 12 sources, already used for exploration.
- D2: 12 sources, already used for adaptive checking; it is no longer a held-out test.
- C: 24 untouched sources, used once after freezing a candidate.
- Reserve: 65 sources. Before reading new items, group near-duplicates and reserve a topic-balanced allocation for additional development, replication, and untouched contingency. Save exact IDs and allocation seed.

All renderings, clues, perturbed responses, and all three task forms of a source must stay within its source family. Check demonstration-template overlap before assigning fresh splits. Do not replace a source because Qwen fails it. Eligibility exclusions must follow source/audit rules fixed before student inference.

The 113-source pool alone is not enough to support every near-perfect-quality claim. Expand with independently checked sources for converter and judge validation as needed. Keep the gold calibration-development set separate from the final gold validation set and the Qwen confirmation set. Record source provenance, solution checks, and duplicate groups. Do not count teacher answer agreement as a proof audit.

Build gold cases in stages:

1. Start with 40 development cases to expose rubric defects quickly.
2. Include valid original and alternative reconstructions, missing optional proof steps, wrong answers, missing domains, conflicting assumptions, decorative clues, answer copying, ambiguous inputs, and genuinely unjudgeable mathematics.
3. Use matched positive/negative edits where possible. Check the edit actually changes the mathematical property; a grammatical perturbation is not a reasoning error.
4. Establish labels through saved mathematical derivations, exact enumeration, symbolic verification with stated domains, or independent human adjudication. A second DeepSeek pass is useful disagreement detection but is not an independent gold label.
5. Freeze a separate validation set large enough to support the claimed confidence bounds. Aim for 200 independent cases/families for the near-perfect claim, expanding beyond the pilot pool when required.
6. Save reference labels and acceptable score ranges before the tested judge sees the cases. Blind the judge to model, arm, expected label, and reference question for primary reconstruction scoring.

Human-reviewed, assistant-reviewed, mechanically verified, and teacher-only labels must have distinct provenance. If human review is unavailable, provide the mechanically certified subset and label the broader result provisional; do not invent a human agreement statistic.

## 5. Autoresearch controller: the loop

Each cycle has one diagnosis, a falsifiable hypothesis, a minimal change, a matched experiment, and a decision.

1. **Inspect:** read public evidence, response, judge record, and source support. Review all first-batch cases, then all disagreements/uncertainties plus a balanced random sample of successes and failures.
2. **Locate the defect:** runtime, source mathematics, conversion, disclosure, student inference, response formatting, judge interpretation, or measurement code. Do not fix a judge error by altering student prompts.
3. **Register:** save the hypothesis, changed factor, fixed factors, source IDs, seeds, sample size, expected outcome, rejection criterion, and cost allowance before generation.
4. **Probe:** use 4–8 development sources to catch mechanical failures. This is discovery, not a reported win.
5. **Compare:** run incumbent and candidate on the same 12–24 development sources, using at least two decoding seeds. Reuse cached outputs only when source, evidence, prompt, model, runtime, and sampling hashes match.
6. **Review:** inspect mathematical validity, leakage, denominator changes, token use, and apparent improvements. Keep teacher judgments unchanged in the raw artifact even if an adjudicator disagrees.
7. **Analyze:** aggregate by source, estimate paired effects and uncertainty, and check whether apparent gains come from more evidence, easier retained cases, extra compute, or actual improvement in the intended factor.
8. **Decide:** adopt provisionally, reject, or mark inconclusive. Inconclusive is not “no effect.” Prefer simpler procedures when extra complexity has no credible practical benefit.
9. **Replicate:** test promising changes on unused development families or an additional predeclared seed. Adaptation uses development only.
10. **Freeze and confirm:** save candidate/protocol hashes before C conversion. Run C once, then replication on a fresh reserved set. No prompt changes from C while retaining its held-out label.

Each cycle emits a machine-readable record and a short rationale. No large automatic sweep begins until its smoke examples and evaluator controls are sound. The controller may run calls concurrently, but a single writer merges records and a global budget accounts for concurrent calls across artifact files.

Continue research rounds while a gate is unmet and there is a new testable diagnosis. Three consecutive inconclusive changes to the same component trigger a root-cause review, not another cosmetic prompt rewrite. If the current data are exhausted, obtain fresh data; do not recycle a test split. If independent labels are unavailable, report the gate as pending. Success ends only after all declared gates pass; finite time or spend ending a session produces a checkpoint, not a success claim.

## 6. What to change in each failure case

| Observed evidence | Diagnosis to check | Next controlled change | What would support adoption |
|---|---|---|---|
| Wrong result already exists in source work | Source defect | Independently verify the relevant derivation; exclude under a recorded rule or repair with provenance | Clues have sound support; exclusions reported |
| True clues refer to undefined variables | Unusable evidence | Make sentences locally interpretable using a global converter instruction/example | Higher audit validity without revealing the full question |
| Four clues repeat one fact | Padding/redundancy | Allow fewer honest observations; use common eligible subsets for fixed-count studies | Better coverage and distinctness, not merely higher student score |
| Public input restates premise and target | Leakage | Remove the revealing relation or weaken specificity, then rerun joint audit | Independent leakage review passes while evidence remains informative |
| Qwen confuses answer with an intermediate value | Missing target orientation or inverse reasoning | Compare inverse-construction demonstrations; separately test an explicit broad role cue | Better answer consistency on matched data, no leaked conditions |
| Qwen notices mismatch but keeps the question | Premature commitment | Verification-first output or bounded self-revision | Gains survive equal-compute controls and a fresh seed |
| Conditions appear only in assumptions | Incomplete final question | One instruction/example requiring all chosen conditions in the question | Fewer independently verified well-posedness defects |
| Extra clues lower scores | Added constraints may be doing useful work | Inspect grounding failures; compare recovery and correctness together | Evidence of useful constraints rather than an unsupported “more clues is worse” claim |
| A different valid question is rejected | Reference bias | Fix source-blind rubric/fixtures; rescore all compared arms | Alternate-valid recall improves without false accepts |
| Judge accepts a false or decorative argument | Judge reliability defect | Add a matched gold counterexample; explicit independent calculation/checks | Improves held-out gold accuracy, not only the motivating case |
| Judge cannot decide difficult mathematics | Uncertainty/coverage issue | Record abstention; use exact checks or separate adjudication | Higher resolved coverage without optimistic forced labels |
| JSON is malformed but mathematics is readable | Output-format defect | Deterministic documented repair or simpler schema | Same mathematical content preserved; format flag retained |
| Length stops or generated thinking occur | Runtime defect | Fix template/cap/context before scientific comparisons | Raw request/response checks pass on a matched runtime probe |
| Candidate improves one source only | Overfitting/sampling noise | New decoding seed and other development families | Source-level improvement persists |
| Mean is <20 | Possible floor | First check measurement and input validity, then evidence usefulness and prompt clarity | Higher mean from substantive reconstruction, not looser scoring |
| Mean is >75 | Possible ceiling or leakage | Audit leakage first; test fewer/weaker clues through global rules | Lower mean with valid, supported, still-grounded evidence |
| Mean is in range but almost all outputs score 1 | Degenerate difficulty metric | Inspect task utility and score semantics; report success distribution | Multiple substantive successes/partial constructions across families |

Do not handcraft clues for individual Qwen failures, give source-specific hidden hints, select easy outputs, or train the judge to agree with desired student scores.

## 7. Experiment ladder and hyperparameter evidence

Run staged comparisons rather than an immediate full factorial. Use a common source set and matched clue identities wherever the factor allows it.

| Choice | Initial comparison | Fixed controls and required evidence |
|---|---|---|
| Student instruction | Existing p1 vs p5 vs p6 vs p7 | Same complete bank, same seeds, same judge; p7 tests a prompt package, not an isolated example-count effect |
| Answer-role cue | Complete bank vs same ordered bank plus one short role cue | Audit joint leakage first; report added token/clue count; this alone does not isolate role semantics from extra evidence |
| Role-specific benefit | Added role cue vs added source-supported non-role observation at similar length | Both independently audited; common eligible sources; otherwise claim only the package effect |
| Clue count | Nested k=1,2,3,4; add k=5 only for the explicit role condition | Two fixed permutations; common eligible bank subset; coverage outside that subset reported |
| Per-clue contribution | Complete bank vs each leave-one-out bank on a small fixed subset | Same prompt and seed; estimate context-dependent removal effects, never “bits of information” |
| Specificity | Low/medium/high rewrites of the same observations | Audit entailment and ties; match observation identity; do not confuse more tokens with more information |
| Presentation | Ordinary sentence bullets vs equivalent fragments vs concatenated sentences | Same facts and ordering; paragraph adds no connective reasoning; report token lengths |
| Few-shot count/content | Zero, one, two examples; then content-matched comparisons if needed | Keep evaluation templates out of demonstrations; token-matched control needed for a content-specific claim |
| Sampling | Start with historical temperature .7, top-p .8, top-k 20 | These are inherited controls, not optima. Compare temperature 0/.4/.7 only after task/evaluator stability; log effective backend defaults such as min-p |
| Output cap | Start at 8192; inspect real lengths; compare 2048/8192 on a fixed subset if shortening | Truncation and exact cost measured. A cap setting is not a target response length |
| Judge reasoning | Reasoning enabled, initially low effort; compare low/medium on fixed gold cases | Same visible-output allowance or report budget differences; record abstention, accuracy, latency, and reasoning-token usage |
| Self-revision | Single call vs two-call draft/check/revise | No teacher correctness labels during Qwen inference; compare with equal-budget independent sampling. Report pass@1 separately from multi-call performance |
| Converter simplicity | Incumbent few-shot converter vs one globally motivated revision | Audit on all preselected sources before observing student performance; compare quality, coverage, and tokens |

Test interactions only after identifying credible main effects—for example, role cue by clue count or format by specificity. A sequential screen cannot support claims about all interactions. Different eligible subsets require separate coverage tables, not a pooled winner table.

A setting can be retained for reproducibility, runtime feasibility, or simplicity. Mark it “inherited” or “engineering choice” if no controlled comparison supports superiority. Every claimed empirical choice must link to its experiment IDs, comparison table, uncertainty, and representative cases. Never retroactively manufacture an experimental reason for a default.

## 8. Controls and independent validation

For the frozen candidate, include:

- **Answer-only:** measures answer-compatible invention. Its mathematical-validity score is not evidence-grounding success; original-source recovery remains useful.
- **Full worked solution:** checks whether the model can recover a problem from high-information evidence. It is a control, not a legal sparse RECONSTRUCT item.
- **Wrong-source/shuffled clues:** use as evaluator/evidence-sensitivity diagnostics, not as normal well-posed task items unless feasibility is independently established. Arbitrarily mixed clues may admit no valid solution.
- **Valid alternative reconstruction:** prevents exact-source matching from becoming a hidden primary requirement.
- **Minimal incorrect edits:** verify sensitivity to wrong answers, omitted domains, conflicting conditions, and decorative grounding.
- **Fresh local SOLVE subset:** checks underlying mathematical capability and runtime under the same checkpoint/quantization. Historical vLLM SOLVE scores cannot substitute for it.

The converter, bank auditor, and judge use separate calls and no shared conversation state. This reduces direct contamination but does not make their errors independent. Randomize response order; normalize field order for the judge; hide arm, prompt version, model name, and expected label. Independently recheck apparent successes and a preselected sample of failures.

## 9. Statistical analysis and selection

- Primary Qwen endpoint: source-average normalized score and a 95% source-cluster bootstrap interval. Keep all planned sources in coverage accounting.
- Missing score bounds: assign unresolved planned responses 0 and 100 for lower/upper sensitivity analyses. Also report the resolved mean explicitly; do not let missing difficult cases improve the headline.
- Compare candidates through paired source-level score differences with bootstrap intervals. Report a predeclared practical margin, initially 5/100, as a design choice rather than an observed optimum.
- Binary grounded success: report source-level outcomes, Wilson intervals for a single independent generation per source, and paired exact McNemar/sign tests where applicable. Cluster repeated seeds.
- With many candidate tests, report the whole search and use fresh confirmation for the primary superiority claim; use Holm correction if making several confirmatory significance claims on the same set.
- Select from versions that pass input/evaluator validity gates. First prefer valid evidence and reliable scoring, then a mean within the user target and a useful distribution, then simpler prompts/lower cost. Do not maximize accuracy past the desired ceiling.
- If two candidates are statistically indistinguishable, report uncertainty and retain the simpler one provisionally. “Not significant” does not establish equivalence; an equivalence claim needs a predeclared margin and sufficient precision.
- A claim that one version is better needs matched evidence and confirmation. A claim that a setting is optimal is limited to the tested grid. Descriptive correlations do not identify causal mechanisms.

The follow-up analysis now implements paired binary outcomes, normalized-score means, source-level score bootstrap intervals, and missing-score bounds. Adjudication sensitivity and final source-family grouping still require validation before paper claims.

## 10. Evidence packet for every cycle

Each experiment directory must contain:

```text
protocol.json          hypothesis, endpoints, exact factors, source IDs, seeds, budget
provenance.json        checkpoint/GGUF hashes, runtime/build, effective sampling, code revision
prompts/               immutable prompt texts and hashes
sources.json           provenance and split/group IDs; private source separated from student input
public-inputs.jsonl    exactly what the student saw, including ordering and role cues
raw/                   every request, response, usage, finish reason, error, and retry
reviews.jsonl          independent mathematical checks, leakage flags, label provenance
results.json           source/seed outcomes and all inclusion/abstention decisions
analysis.json          effect sizes, intervals, denominators, cost, and paired comparisons
decision.md            adopt/reject/inconclusive, evidence, limitations, next hypothesis
```

Do not save API keys. Store prompt hash, model identity, provider configuration, timing, token use, and request identifiers when available. Ledger costs of failed calls when exposed; label totals lower bounds when unavailable. Preserve negative results and rejected banks. Keep raw teacher labels plus adjudicated labels and report both; never overwrite a judge result to make a table cleaner.

Maintain a paper claim ledger:

| Proposed claim | Required backing |
|---|---|
| Role orientation helps | Audited matched role/no-role comparison, fresh confirmation; extra-evidence limitation stated |
| Sentence format is preferable | Equivalent-fact format comparison; if tied, call it a readability choice |
| k clues balance difficulty and grounding | Matched nested-count curve, coverage, recovery, and validity outcomes |
| Compact prompts suffice | Matched example/instruction comparisons with precision limits |
| DeepSeek judges accurately | Independent gold validation, false-accept/false-reject breakdown, abstention, confidence bounds |
| Converter is reliable | Independent bank validity/leakage review and coverage, including rejected items |
| Qwen mean is 20–75/100 | Frozen fresh-source result, primary interval, histogram, and unresolved bounds |
| Training transfers across reasoning types | Later source-disjoint training-by-evaluation matrix; this pilot is insufficient |

## 11. Next execution order

Current execution priority: the four-arm prompt screen is complete. Preserve the historical sequence below as provenance, but resume by reconciling pending role, revision, and answer-placement experiments; inspecting the saved 41-case judge-development run; and measuring converter validity. Do not rerun completed calls merely because this checklist originally called them pending. A passing development fixture set is not independent final validation.

Latest checkpoint supersedes that earlier queue: the matched sparse comparison and information controls are complete. D3 source allocation and mathematical preflight are saved; eleven of twelve fresh sources are eligible, and one ambiguous source remains in the coverage denominator. D3 conversion/support/public-disclosure preparation is active under amendment I. Acceptance now requires both support and disclosure gates. Finish that preparation and inspect coverage before a nested-count student sweep. The production-derived judge fixtures resolve3/4 cases correctly, with one wording-dependent case still unresolved after its one permitted retry; no near-perfect validation claim follows.

1. Preserve and finish already-started follow-up calls; merge staged student outputs without overwriting judgments. Keep the malformed-output failure as a failure unless a deterministic semantic-preserving parser repair is applied consistently.
2. Analyze completed p1/p5/p6/p7 arms under evaluate_p2; finish missing judgments with a bounded technical-retry policy. Mark incomplete arms as incomplete.
3. Independently inspect the 12 generated role cues; compose each with its original bank and audit the **combined** public input before any role-condition student generation. Rejection is a conversion outcome, not an excuse to remove a difficult source invisibly.
4. Create the 40-case gold-development set, repair demonstrable judge/rubric defects, and rerun every candidate comparison under the same frozen evaluator if the rubric changes.
5. Add normalized-score analysis and score-distribution diagnostics. The current baseline already meets the numerical development mean target; focus on grounding quality and trustworthy measurement.
6. Run the role-cue comparison with two seeds only after audits pass. Inspect whether improvements preserve uncertainty and avoid explicit question leakage.
7. Choose the next factor from the observed failure taxonomy. Run count/specificity/presentation ablations only when inputs and judging are reliable; retain ordinary sentence cues as a valid option.
8. Expand independent validation data. Freeze the candidate, thresholds, source IDs, prompts, and analysis code before C. Run C and then fresh replication without tuning between them.
9. Release a candidate only when its declared gates are supported. Otherwise checkpoint the unmet gate and next hypothesis; continue on development or new data rather than optimizing the test set.

## 12. Time and resource policy

Use 20–40-minute diagnostic cycles and review progress after roughly 1, 3, and 5 hours in an eight-hour session. Reserve the final hour for analysis, saved artifacts, and the next decision. These are planning intervals, not evidence that eight hours was actually spent.

Start with local original Qwen3-4B Q4_K_M, explicit non-thinking operation, 8192 output cap, and the recorded llama.cpp build. Preserve the distinction from historical full-precision/vLLM runs. DeepSeek V4.1 Flash is used for conversion and judgment with reasoning enabled. Confirm the provider-supported request and usable visible output through a small probe before scaling.

Retain the current $5 research-session cap unless the user changes it. Account globally across concurrent workers and copied artifacts; imported historical costs must not be billed twice in the session ledger. Limit paid-call concurrency to four across the whole controller. Technical retries are capped and logged; never retry a mathematically poor student response until it happens to succeed.

If infrastructure, data, independent reference labels, or budget prevent meeting a gate, report that limitation and the completed evidence. No promise of eventual near-perfect reliability can replace measuring it.

## 13. Concrete next eight-hour session

This is a conditional research schedule, not a promise that all release gates can be established in eight hours. Finish diagnosis before scaling. Runtime delays consume the same budget; cut optional comparisons before cutting validation.

| Time | Work | Required saved output / decision |
|---|---|---|
| 0:00–0:45 | Reconcile existing runs, cache keys, missing outputs, live jobs, effective runtime, and deduplicated spend. Finish already authorized incomplete comparisons before new variants. | One inventory separating planned, generated, judged, failed, imported, and independently reviewed records; no double billing of copied usage. |
| 0:45–2:00 | Review evaluator-development fixtures and real outputs. Inspect every apparent success, disagreements, and a seeded sample across score bins. Separate mathematical support checking from public-only disclosure checking. | Error taxonomy, reference derivations and provenance, reviewer disagreements, and evaluator freeze decision. If the evaluator changes, rescore all compared arms consistently. |
| 2:00–3:30 | Study clue quantity on the same banks: nested k=1,2,3,4 with two fixed permutations. Use the common eligible set for matched effects and report overall eligibility separately. Begin with 4–8 sources, then 12–24 only if audits pass. | Count curve with normalized score, grounded success, leakage, coverage, and tokens; representative successes and failures. If the clue bank itself is defective, repair the global converter before this sweep. |
| 3:30–4:30 | Test information content: remove one clue at a time on a fixed subset; compare lower/medium specificity for the same underlying observations. | Context-dependent clue contribution and semantic audit. Do not infer information quantity from word count or label contributions as information-theoretic bits. |
| 4:30–5:15 | Test presentation only after content is fixed: sentence bullets versus paragraph, then fragments if time allows. Keep propositions and order constant. | Matched format comparison. Choose ordinary sentences for readability if evidence is inconclusive; do not call that an empirical accuracy win. |
| 5:15–6:15 | Replicate the most promising candidate on unused development families. Include answer-only and full-information controls and a small matched local SOLVE diagnostic. | Determine whether sparse evidence helps meaningful reconstruction and whether failure reflects source difficulty, missing information, or inference. No oracle selection among student attempts. |
| 6:15–7:15 | Freeze candidate and evaluator only if validity checks support doing so. Use untouched C once; otherwise spend this hour resolving the failed gate and retain C. | Frozen hashes and confirmation result, or explicit unverified gate with the next discriminating experiment. Never tune on C and still call it held out. |
| 7:15–8:00 | Reconcile results, costs, exclusions, negative results, and mathematical reviews. | Reproducible report, claim-to-evidence table, candidate decision, and continuation checkpoint. |

Priority when time is tight: reliable measurement > valid evidence > clue-count comparison > fresh replication > specificity/format breadth. Independent validation for a near-perfect accuracy claim may require a later session and a larger source pool. Do not substitute extra perturbations of a few families for independent cases.

The task definition stays simple throughout: **given a final answer and partial supported observations, reconstruct a plausible original question and provide a short verification that grounds every displayed observation.** Score mathematical validity and evidence grounding separately from semantic equivalence to the original. Semantic equivalence is a required acceptance endpoint: at least 5/25 preselected source families must pass grounding, equivalence, and non-leakage together. Valid alternatives retain rubric credit but do not count as recovered originals. Ambiguity is allowed, but undefined clues and unsatisfiable evidence are conversion defects.

The later SOLVE/JUDGE/RECONSTRUCT study uses a source-family-disjoint training-by-evaluation matrix: no-task-training baseline plus each single-task training condition evaluated on all three tasks. Match initial checkpoint, training-token budget, source difficulty, and evaluation data; report task-specific metrics and transfer relative to baseline. Keep this downstream study separate from the present task-construction experiments so that a successful prompt screen is never presented as evidence of training transfer.
