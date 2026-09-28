# RECONSTRUCT: next autoresearch session

Status: prospective execution plan, written after D3 prefix auditing and the audit-budget probe. No new model experiment was run to write this plan. This document supersedes the execution queue and eight-hour schedule in `reconstruct-autoresearch.md`; that document retains the definitions, release gates, and evidence requirements. Amendments I–K remain historical preregistrations.

## Objective

Build an interpretable inverse-reasoning task: given an answer and a few supported observations, construct a plausible question and verify that its solution yields that answer and substantively uses every observation. Missing conditions may be inferred or constructed; valid alternatives are allowed. Matching the original wording is not the primary metric.

The intended skill is constrained hypothesis construction under incomplete information. This is an operational task definition, not evidence of a distinct cognitive mechanism. The eventual contribution is the controlled SOLVE/JUDGE/RECONSTRUCT training-and-transfer study.

The requested difficulty target is **mean normalized Qwen rubric score 20–75/100**. It is neither percent correct nor a requirement that every output lie in that interval. Average seeds within source, then sources equally. Report all score bins, grounded success, and unresolved cases alongside the mean.

**User-added recovery gate:** at least **5/25** preselected source families must produce a grounded reconstruction that is semantically the same question as the original. This is an additional required endpoint, not satisfied by five different valid questions sharing the answer. The [semantic recovery and leakage amendment](reconstruct-semantic-recovery-gates.md) defines the denominator, matching rules, strict disclosure checks, and confirmation allocation. It supersedes references to source recovery as merely diagnostic. Existing raw scores remain unchanged.

## Evidence determining the next step

| Finding | Implication | Saved evidence |
|---|---|---|
| Four student prompt variants have paired intervals containing zero | Keep compact p1 provisionally; no demonstrated winner | [Prompt screen](../../artifacts/reconstruct/followup-v2/prompt-screen.md) |
| Baseline mean remains 26.14 on accepted banks but has 0/22 grounded successes | A mean in range cannot establish useful reconstruction | [Validity sensitivity](../../artifacts/reconstruct/followup-v2/baseline-validity-sensitivity.md) |
| Sparse role guidance has no supported improvement | Do not spend another cycle on cosmetic role wording | [Sparse decision](../../artifacts/reconstruct/followup-v2/sparse-decision.md) |
| D3 full-bank auditing accepts 6/12 original sources | Full-bank disclosure policy fails the coverage goal | [Coverage report](../../artifacts/reconstruct/d3-v1/full-bank-coverage.md) |
| Prefix audit decisions conflict across nested inputs | Resolve disclosure measurement before selecting a clue count | [Raw prefix audits](../../artifacts/reconstruct/d3-v1/prefix-study.json) |
| A larger-budget repeat changes an existing rejection to acceptance | Increased cap is not demonstrated auditor accuracy improvement | [Budget probe](../../artifacts/reconstruct/d3-v1/audit-budget-report.md) |

In particular, source141's one-clue input is rejected while its two-clue superset is accepted; source123's shorter inputs are rejected while longer inputs are accepted. Inspect the actual propositions and reasons before adjudicating. A disclosure defect that already exists cannot disappear merely by adding unchanged clues. Other properties, such as interpretability, can improve with additional context: check the specific defect, not just the final accept/reject label.

## Keep the procedure simple

The production pipeline has four responsibilities, even if the same teacher serves several roles:

1. **Convert:** source question, verified solution, answer → a small bank of distinct solution observations. Use a compact instruction and a few examples, rather than source-specific rules.
2. **Check support and exposure separately:** source-aware support checker verifies truth; source-blind disclosure checker sees exactly the answer and displayed clues. Neither alone establishes both properties.
3. **Reconstruct:** non-thinking Qwen sees only the public input and returns a self-contained question plus concise verification.
4. **Judge:** source-blind evaluator checks well-posedness, answer correctness, substantive clue use, and shortcuts. A separate source-aware evaluator checks semantic equivalence to the original; this is a required acceptance endpoint. Generic grounded alternatives retain their rubric credit but cannot satisfy the 5/25 gate.

Never expose a complete solution chain as the sparse condition. Use recorded mathematical observations, not purported access to a model's private internal reasoning. Judge the question as written: necessary premises appearing only in commentary do not silently become part of it.

## Stage A — calibrate the disclosure boundary

Before calls, register amendment L with case IDs, prompt hashes, reference-label provenance, exact settings, and budget. Preserve audit_role_p3 as the incumbent.

Operational distinction: a missing question mark, task verb, routine arithmetic, or cosmetic wording does not create substantive uncertainty. A missing constraint, target, domain, or mathematical relation can create substantive uncertainty. Neither a short input nor an omitted original sentence guarantees this.

Create 24 development cases from at least eight families, including clear leakage, genuinely sparse inputs, and boundary cases. Review the mathematical content first. Include existing contradictory cases for diagnosis, but keep at least four families out of the prompt examples. Use the same exact inputs for incumbent and candidate. Repeat a fixed eight-case subset once to measure label stability. Repeats are not independent cases.

Candidate: one global definition correction and at most three few-shot examples. Example intentions, to finalize and label before calls:

| Public input | Expected lesson |
|---|---|
| Answer10; five people each shake hands once with every other person; pair count is 5×4/2 | Reject: premises, target, and computation are exposed; asking for the count is copying |
| Answer6; rectangle sides satisfy x+y=10; its area is x(10−x) | Potentially valid sparse input: an area constraint and target are absent; e.g. area24 and longer side recover6 |
| AnswerYes; a sequence's nth partial sum is 4n−2 | Missing property being asked about matters; do not invent a hidden target to claim a complete solution is exposed |

These are pedagogical examples, not accuracy evidence. The rectangle example must not license “assume the desired answer”: a complete reconstructed question supplies independently meaningful premises, such as perimeter20 and area24, and verifies the answer.

Save expected ACCEPT/REJECT/AMBIGUOUS labels and defect categories. Ambiguous cases measure abstention and disagreement, not binary gold accuracy. Maintain original teacher labels and separate assistant/mechanical/human adjudication provenance.

Progression gate for a small exploratory count study: all clear leakage controls rejected, all unambiguous sparse controls accepted, no unresolved contradictory disclosure labels on the planned D3 inputs, and reference disagreements resolved or explicitly excluded under a fixed rule. This is a development checkpoint, not the >=98% release claim. If it fails, inspect the defect and revise once; after another failure, spend the session on measurement rather than launch a student sweep.

If adopted provisionally, audit all 33 exact D3 prefixes consistently with the candidate, plus original full banks as diagnostic controls. Do not replace only inconvenient labels or select a favorable repeat. Freeze the eligibility manifest before any D3 student generation. At least eight common eligible sources are required by the registered count-study rule; keep all12 original sources in coverage accounting.

## Stage B — identify how much evidence to disclose

Use the existing D3 bank and order seed20260920, unchanged sentences, nested k=1,2,3, p1 student prompt, and decoding seeds0/1. This gives at most66 student generations for11 sources, fewer under frozen common eligibility. Review a four-source mechanical batch, then complete the predeclared batch regardless of its scores if mechanics are sound.

Primary comparison: paired source-average differences between counts. Also report score histogram, grounded successes, answer correctness, conversion acceptance, leakage, output length, truncation, and cost. Report each count's coverage on all12 sources; use the same eligible sources for causal count comparisons. Report full-bank conditions separately because eligibility differs.

Do not select a count because it happens to place Qwen closest to the middle of20–75. Select only among valid conditions; prefer the smallest count with substantive successful reconstructions across multiple families and acceptable coverage. If effects remain uncertain, retain a provisional count and label the choice unresolved. A second predeclared permutation on fresh development data tests robustness; never search clue-order seeds for a favorable score.

## Stage C — distinguish clue content from presentation

Run only after Stage B yields useful valid inputs. Register each comparison separately; these are optional within eight hours.

| Factor | Controlled comparison | What it can establish |
|---|---|---|
| Contribution of an individual clue | Complete selected input versus each leave-one-out input on a fixed source subset; audit each subset | Context-dependent usefulness of that clue; contributions need not add up |
| Specificity | Two globally defined renderings of the same observation, one withholding a nonessential detail; verify support and disclosure | Effect of the specified disclosure intervention, not information measured in bits |
| Format | Identical sentence text and order as bullets versus one paragraph | Presentation effect without changed propositions |
| Fragments | Only after semantic-equivalence review; same mathematical facts | Fragment-format effect subject to demonstrated equivalence |
| Student demonstration | One genuine inverse-construction example versus incumbent example, same evidence | Prompt-package effect; example count/content/length remain separate factors |

Do not run these as a huge factorial. One diagnosis chooses the next comparison. Reuse calls only when the complete public input, prompt, runtime, sampling, and seed match; report reuse explicitly.

## Stage D — validate teacher conversion and scoring

Maintain three separate evaluations: source support, public disclosure, and reconstruction scoring. High performance on one does not imply the others.

Extend the existing judge-development cases with production errors and valid alternatives, including wrong numerical answers, missing domains, contradictory clues, decorative clue use, tautologies, and linguistically ambiguous questions. Reference answers need saved derivations or appropriate mechanical checks. The same teacher agreeing with itself is not independent verification.

Freeze independent validation cases after development. The existing release goals remain >=98% point validity/accuracy with a95% lower bound >=95%, >=80% conversion coverage, and >=95% resolved judgment coverage. Also report false accepts, false rejects, score error, agreement, and abstention. About200 genuinely independent families may be needed; many edits of a few questions cannot support that claim. The current pool and an eight-hour session may be insufficient.

The teacher model must be the exact previously working provider ID, with reasoning enabled and recorded effective settings. Keep the original local Qwen checkpoint, quantization, chat template, explicit non-thinking mode, and8192-token output cap. These are inherited controls, not established optima. Measure truncation before cap changes; apply any changed setting consistently in new comparisons.

## Autoresearch decisions after every batch

| Observation | Next action |
|---|---|
| Source or clue mathematics is wrong | Fix global conversion/support procedure; preserve failed sources and exclusion counts |
| Disclosure auditor contradicts itself | Calibrate boundary and record repeat disagreement; no majority vote presented as truth |
| Judge rejects a verified valid alternative | Repair evaluator on development; rescore all compared arms consistently |
| Mean in range but almost all score1 | Diagnose grounding and constraint construction; do not release on mean alone |
| Mean below20 | Check judge, source validity, truncation, and feasibility before adding evidence |
| Mean above75 | Check leakage, then compare a globally sparser exposure policy |
| More clues improve answer correctness but reduce full grounding | Report both effects; inspect whether extra constraints are useful or redundant |
| Qwen fails while a source-blind teacher produces a verified solution | Evidence of feasibility on those inputs, not proof of Qwen learnability |
| Both fail sparse inputs but succeed on full information | Inspect ambiguity and information sufficiency; retain the control as diagnostic |
| Candidate wins on one family only | Replicate on fresh development families; do not promote based on pooled repeated seeds |
| Timeout, empty output, malformed format | One logged technical retry where permitted; preserve failures and uncertainty bounds |
| Budget/time ends | Save checkpoint with next discriminating experiment; do not declare gates passed |

Each iteration follows: inspect → diagnose → preregister → small mechanical probe → complete matched batch → mathematical review → paired analysis → adopt/reject/inconclusive. Change one component per hypothesis. After three inconclusive changes to the same component, review the task definition and measurement rather than continue cosmetic edits.

## Conditional eight-hour allocation

| Elapsed time | Work | Deliverable |
|---|---|---|
| 0:00–0:30 | Reconcile live jobs, raw artifacts, model identity, spend, and current contradictions | Inventory; no duplicate calls; registered next hypothesis |
| 0:30–2:00 | Stage A reference cases and auditor comparison | Audited boundary examples, repeat consistency, decision |
| 2:00–3:00 | Re-audit exact D3 prefixes if calibration passes | Frozen eligibility; coverage and exclusions |
| 3:00–5:00 | Stage B count study, two seeds, direct review | Count curve, paired intervals, grounded examples and failure taxonomy |
| 5:00–6:00 | One diagnosis-led content or format experiment, or repair a failed prior gate | Controlled comparison or explicit measurement failure |
| 6:00–7:00 | Fresh development replication and judge-reference expansion | Replication evidence; updated teacher reliability limitations |
| 7:00–8:00 | Analysis and paper evidence packet | Decision report, claim ledger, next-session checkpoint |

This is an allocation, not a promise of completion at local throughput. Estimate remaining runtime after the first batch. Cut optional Stage C breadth first. Retain the $5 session cap, global maximum four paid requests, and recorded retry policy. No paid calls are launched merely by creating this plan.

Do not open untouched C or R just to fill the schedule. Use C once only after freezing the complete candidate and evaluator with adequate development evidence; then use R for independent replication without tuning between them. If C motivates a revision, C becomes development and a new untouched confirmation set is required.

## Paper evidence and completion

Every cycle saves a protocol, immutable prompts and hashes, source-family split, exact public inputs, raw responses including failures, mathematical reviews, analysis, costs, and decision. Every reported count must distinguish sources, outputs, repeats, inherited records, and adjudicated labels.

For each chosen hyperparameter, label its basis: **inherited control**, **engineering necessity**, **readability preference**, or **empirically supported choice**. Only the last category supports a performance claim. Record rejected candidates and uncertainty intervals next to the adopted setting. A null comparison supports retaining simplicity provisionally; it does not prove equivalence.

Completion requires the frozen Qwen mean and its prespecified interval within20–75, at least5/25 grounded semantic recoveries under the new amendment, adequate converter validity/coverage, independent judge validation, and a reproducible evidence packet. Until then report a provisional version and the unmet gates. “Best” means best supported among tested procedures within the stated budget.

The subsequent transfer study crosses training on SOLVE/JUDGE/RECONSTRUCT with evaluation on all three, includes an untrained baseline, groups all task forms by source family, and matches model initialization and training budget. Task-specific metrics and transfer differences must be reported separately; the present calibration does not establish those transfer results.
