# Amendment: grounded semantic recovery and strict disclosure

Status: required by the user after the next-session plan was drafted. These are prospective requirements; no new model results establish them yet. This amendment takes precedence over earlier descriptions of original-question recovery as merely diagnostic. It does not rewrite historical rubric scores.

## 1. Three joint requirements

1. Qwen mean normalized rubric score is20–75/100 under the existing aggregation and uncertainty protocol.
2. At least5 of25 preselected source families have a **grounded semantic recovery** in the primary single-draw evaluation.
3. The evaluated public inputs pass strict support and non-disclosure checks. A recovery from a leaking input cannot count toward requirement2.

For source i, let G_i be a mathematically grounded success (existing score>=3 plus well-posedness, correct answer, substantive use of every clue, sound verification, and no shortcut). Let S_i mean semantic equivalence to the original source question, and L_i mean the public input passes the support/disclosure gate. The counted event is G_i AND S_i AND L_i. Record the three components separately.

Valid alternative problems may retain high grounded rubric scores, but S_i=false means they do not count as recovered originals. This preserves the historical score meaning while requiring the stronger user objective.

## 2. What semantic equivalence means

Compare the mathematical task, not surface words, embeddings, answer equality, or a shared solution method. Require preservation of:

- requested quantity, proposition, or construction;
- mathematical objects and their relevant relationships;
- essential premises, domains, quantifiers, bounds, and parameters;
- the feasible cases and answer interpretation, up to an explicitly justified equivalent reformulation.

Renaming variables, changing narrative objects, reordering premises, and algebraically equivalent expressions are allowed. Nonessential wording can disappear. Changed essential parameters, a weaker special case, different quantifiers, or a different target do not count even when the final answer agrees. A mathematical reparameterization requires a recorded correspondence preserving the problem; do not accept arbitrary same-answer problems.

Examples:

| Source and candidate | Semantic label |
|---|---|
| Rectangle with perimeter20 and area24, find longer side; candidate uses sides x,y with x+y=10, xy=24, find max(x,y) | Same: equivalent premises and target |
| Same source; candidate asks for the positive root of x²=36 | Different: answer6 alone does not establish recovery |
| Count four ordered integers in[0,7] summing21; candidate asks coefficient of x²¹ in(1+x+…+x⁷)⁴ | Same with the generating-function correspondence verified |
| Same counting source; candidate asks for unordered quadruples | Different: essential counting convention changed |

Judge semantic equivalence separately with source access, blinded to Qwen identity, arm, and desired success count. Keep mathematical grounding evaluation source-blind. Use the existing source-recovery categories2=same,1=related,0=different, plus unresolved; only verified2 qualifies. A keyword match or the teacher's unexplained assertion is insufficient. Save the premise/target correspondence and counterexample when rejecting a purported equivalence. Independently review every counted success; ambiguous cases remain unresolved.

## 3. Denominator and statistical interpretation

Freeze25 original source families before conversion or Qwen generation. Use one predeclared primary decoding seed (seed0), one response per source, and no best-of-two selection. Seed1 is a separate robustness replicate; it cannot rescue a failed primary response or count the same source twice.

Keep all25 sources in the end-to-end denominator, including source defects, conversion rejection, leakage, and operational failures. Report reconstruction conditional on accepted inputs separately. Exclusions cannot be replaced after observing conversion or student outcomes. Unresolved outcomes do not count as confirmed successes; report lower/upper success bounds.

Existing C contains24 sources, so do not silently call it a25-source test. Before accessing confirmation contents, save an explicit C25 manifest containing unchanged C plus one untouched, semantically nonduplicate contingency source selected using metadata and a recorded seed. Keep R24 unchanged. If an independently suitable additional source cannot be allocated without contamination, obtain a fresh source before confirmation. No manifest or split was changed by this planning amendment.

At5/25, the observed success rate is20%, but a95% Wilson interval is approximately9%–39%. Therefore5/25 satisfies the user's finite-batch gate; it does not establish a population success rate of at least20% with95% confidence. Report the interval and seek fresh replication. If a population lower-bound claim is later desired, preregister a larger sample and its criterion before outcomes.

## 4. Strict checks on what DeepSeek exposes

DeepSeek conversion sees Q/A/W; Qwen receives only the final answer and selected observations. Audit the **exact combined public input**, including the answer, all clues, and any role labels. A safe sentence can become leaking in combination with another sentence or the answer.

Required per-item record:

```text
source_support: supported / unsupported / unresolved
verbatim_or_paraphrase_copy: absent / present / unresolved
premise_target_bundle_exposed: absent / present / unresolved
complete_or_nearly_complete_solution: absent / present / unresolved
missing_essential_element: description + private source reference
nontrivial_inference_required: explanation tied to actual public text
direct_copy_attack: proposed question + transformation description
decision: accept / reject / review
```

Hard rules:

1. **Zero tolerated known direct leaks in the released set.** Reject direct question copies/paraphrases, a complete premise-and-target bundle, or a complete/nearly complete solution. Missing only a question mark, task verb, routine arithmetic, variable renaming, or grammatical assembly does not make an input sparse.
2. **At least one essential element must be withheld explicitly.** Record the source target, constraint, relation, or domain not directly supplied. Recovering it must require substantive inference from the evidence and answer. Merely omitting a detail already stated equivalently elsewhere fails. This is a necessary check, not a sufficient numerical measure of disclosure.
3. **Check both views independently.** A source-aware disclosure reviewer compares original premises/target to exact public spans. It must cite public text for every alleged exposure, avoiding prior hallucinations of hidden premises. A source-blind reviewer tests whether the displayed material already describes a complete task/proof. Disagreement means review, not acceptance by whichever judge is more permissive.
4. **Run a direct-copy challenge.** Ask a blinded checker to form a question using only copying, paraphrasing, renaming, and grammatical rearrangement of the public input. If it recovers the source's essential problem with no substantive inference, reject the input. If it produces another fully specified problem, inspect whether the clues expose its entire solution. Failure of this attack does not prove non-leakage.
5. **Screen overlap without pretending it measures semantics.** Normalized phrase/equation overlap flags cases for review; essential formulas may legitimately overlap. Do not impose an unvalidated word-overlap percentage as a safety guarantee. Semantic checks can reject a paraphrase with zero long copied spans.
6. **Apply subset consistency.** Adding unchanged clues cannot remove an existing premise/target disclosure or complete-proof defect. Flag contradictory audit decisions and resolve the actual defect before inference. Do not enforce monotonicity on unrelated properties such as readability.
7. **No Qwen-based item repair or selection.** A rejected input can motivate a globally revised converter or exposure rule. Do not give extra source-specific hints until Qwen happens to recover the original. Register regeneration policies and include all failed attempts in coverage/cost reports.

The population leakage target remains<=2% with uncertainty reported, but this is not permission to knowingly release leaking items. Accepted-bank quality remains a separate independently validated claim; a teacher self-audit cannot guarantee it. Unique answers that identify the original problem even without clues must be reported as an answer-only identifiability stratum, not mistaken for clue benefit.

## 5. Recoverability without direct disclosure

Retain observations that constrain the original structure indirectly: relationships among intermediate quantities, case constraints, or a distinctive mathematical operation. Withhold a meaningful premise/target connection. Do not demand total obscurity: the goal is inferable missing structure, not making the original impossible to recover.

Use matched answer-only and sparse-input controls to assess incremental recovery from clues. Inspect successful reconstructions for the actual inference linking clues to missing structure. A source-blind stronger-model probe is a feasibility diagnostic only. No automatic retry until the teacher or Qwen finds the source.

If grounded alternatives increase but semantic recovery remains low, the task may be too underdetermined for the new objective. Compare a globally more informative, still non-leaking observation policy on development data. If semantic recovery increases together with direct-copy success, reject the apparent gain as disclosure. If neither setting satisfies both goals, report the trade-off instead of lowering the standards.

## 6. Changes to the execution plan

- Stage A now calibrates both strict disclosure decisions and semantic-equivalence labels with matched positive/negative examples. Keep these roles separate from the source-blind grounding rubric.
- Stage B count curves must report grounded semantic recovery as well as mean score, generic grounded success, direct-copy flags, coverage, and uncertainty. Existing D3 is development and has too few families to satisfy5/25.
- Candidate selection requires meaningful semantic recovery on development; repeated groundings of a different question no longer establish the recovery objective.
- Final confirmation uses the prospective C25 procedure and freezes the semantic judge as well as all other prompts before calls. C25 must not become an iterative target.
- Preserve historical evidence: earlier “grounded success” counts are not semantic-recovery counts unless separately verified. Do not retroactively claim the new gate passed.

Every counted final success should be inspectable as: source question, exact public input, missing-element audit, Qwen question, concise verification, independent mathematical check, and explicit semantic correspondence. Keep private/source fields out of Qwen request logs.

### Implementation status

`src/anlp_project/reconstruct_gates.py::confirmation_recovery_count` now checks the finite-batch endpoint using exactly 25 distinct manifest IDs, at most one primary row per family, seed 0, complete per-item gates, and recomputed response/judgment/source bindings. Missing rows stay in the denominator. Duplicate rows and outside-manifest sources are rejected. A caller-supplied binding-pass flag cannot override a stale response hash. Its output explicitly does not authorize overall release: mean-score, converter/judge reliability, independent review provenance, and prospective manifest freezing remain separate requirements. This is a tested component, not a completed confirmation run or a fully integrated release controller.

Regression checks cover five valid records, a fifth record that is only a valid alternative, a secondary seed, failed disclosure, stale bindings, duplicate families, and incomplete manifests. These synthetic software fixtures test accounting behavior; they are not empirical reconstruction successes or evidence of semantic independence between real families.

Current research evidence remains short of the requirement: the reviewed repaired-input Qwen screen has zero primary semantic recoveries across nine eligible development families (twelve original allocated families). Its historical p2 parsed-output mean is30.88/100. [Amendment U](reconstruct-amendment-u.md) passed16/16 authored controls and4/4 production diagnostics, but its subsequent production rescore exposed one independently demonstrated score error and one unresolved stronger-model judgment. Qwen's raw p3 mean is16.18/100, or17.65 in a sensitivity analysis correcting the one known label; original recovery remains zero. The evaluator is provisional, not near-perfectly validated. [V](reconstruct-amendment-v.md) subsequently completed32 local draws on eight reviewed D4 inputs, with zero original recoveries in either arm. Its verified-example prompt produced one family of valid alternatives, not the original target; two grounding judgments remain unresolved. [W](reconstruct-amendment-w.md) now tests a target-retaining converter example on the same development cohort with the incumbent student prompt fixed. Do not open C25 merely because a development mean falls in range.

## 7. Final acceptance worksheet

Create one row for each of the 25 frozen source families, including failed conversions. Record primary seed-0 response, score/100, grounding verdict, semantic verdict, support verdict, disclosure verdict, direct-copy result, independent review provenance, and paths/hashes binding all judgments to the actual public input and response. No missing field counts as a pass. Additional seeds occupy separate robustness rows.

The final counted event is:

```text
counted_success = primary_seed_0
                  AND supported_exact_public_input
                  AND disclosure_review_passed
                  AND no_direct_source_recovery_by_copy_attack
                  AND mathematically_grounded_success
                  AND verified_semantic_equivalence_to_original
                  AND independent_review_complete
                  AND artifact_bindings_valid
```

The copy attack is one necessary diagnostic; a failed attack cannot override a positive leakage finding. Inspect the complete rendered student request, including demonstrations, headers, and answer, for accidental source-specific exposure. Generic demonstrations must come from separate source families. Any rendering or clue edit invalidates the old input-bound disclosure approval and requires a fresh review.

Accept only if at least 5 rows pass, the mean-score criterion and its prespecified uncertainty rule pass, and the separately registered converter/judge quality gates pass. Report rejected inputs and operational failures in the end-to-end denominator; report the rubric mean on scored outputs with missingness bounds separately rather than inventing scores for missing outputs. A grounded semantic success requires recovering the essential mathematical question, not the original prose.

Do not increase hints on individual failed examples or select the best decoding seed to reach five. If fewer than five pass, retain that result. Any subsequent revision uses development data and requires new untouched confirmation families. An eight-hour checkpoint can finish with unmet gates; it cannot certify them by repeated testing of the same 25 questions.

## Latest user steering: richer evidence and 20–40% recovery

Mathematically equivalent question formulations count as correct; source_recovery_p2 already implements this. Wording, notation, or surface story need not match. A correspondence must preserve essential feasible cases, quantifiers, constraints, and target. Merely sharing an answer is insufficient.

The new desired correct-reconstruction range is 20–40%, separate from the average rubric target20–75/100. A future25-family evaluation therefore seeks5–10 grounded semantic successes. Report both success among actually presented eligible tasks and end-to-end success among all preallocated source families; conversion rejection must not be used to manufacture a target rate. AA first tests richer exposure on the existing development cohort. No held-out success or final policy selection is claimed from it.
