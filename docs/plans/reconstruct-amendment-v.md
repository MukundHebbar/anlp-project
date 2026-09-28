# Amendment V: verified reconstruction demonstrations on fresh development sources

Prospective experiment, registered after U's fixed 20-case evaluator calibration passed and while the separately versioned production rescore is pending. No new student outcomes inform this design. This is a demonstration-package comparison, not an isolated estimate of example quality or example count.

## Hypothesis and intervention

S yielded zero Qwen original recoveries. T produced independently assistant-checked first-call original reconstructions on five of the same families, with another qualified equivalence. U distinguishes substantive inference from copied assertions. The next hypothesis is that concrete examples of inferring a missing expression, target operator, and target parameter help Qwen execute reconstruction better than the generic example alone.

Compare `student_p10_recover_original` with a candidate that preserves its instructions/output schema and replaces its one generic demonstration with the exact saved teacher examples from source8, source112, and source141. The selection was declared in U before opening new families. Preserve the demonstrated evidence, questions, and verification, including the explicit symmetry ambiguity for source141. Save hashes and provenance for every demonstration. No reference question or worked solution for an evaluated source enters either student prompt.

The package changes content, number of examples, and prompt length together. If promising, a later matched-count/length comparison is needed before attributing the benefit to example quality specifically. Do not claim that three examples are optimal from this experiment.

## Allocation and contamination control

Use only metadata from the frozen reserve-allocation manifest to allocate twelve new D4 source IDs, three per broad topic, with seed20260923. Before D4 allocation, reserve one seeded contingency ID as the proposed C25 extension, keeping existing C24 and R24 unchanged. Freeze IDs, source metadata, parent-manifest hash, rule, and prompt hashes before inspecting D4 question contents. This does not certify semantic-family independence: review D4 versus the three demonstrations and earlier development families before student generation, record overlaps, and exclude demonstrated near-duplicates without replacements. All twelve stay in allocation/coverage accounting. The C25 extension still requires independent semantic-family review before confirmation; no C/R content is to be opened in this experiment.

## Input preparation

Use the globally specified p4 conversion and the one audit-feedback repair policy from R. Verify source mathematics first. Audit source support and both public-only/source-aware disclosure of the exact combined answer and clues, then perform the copy challenge and independent review. Zero known direct leaks are admitted; disagreements remain pending. At most one repair responds to a corroborated input defect, never Qwen performance. Preserve all rejected banks and count them against conversion coverage. Keep complete accepted banks in the same recorded order and sentence format for both student arms.

Proceed to the small student screen only with at least eight reviewed eligible families. This exploratory minimum is not the production coverage gate of80%. If fewer than eight survive, diagnose conversion rather than silently replacing families or changing to a different exposure policy.

## Student and evaluation controls

Use the existing original Qwen3-4B Q4_K_M local nonthinking runtime, same build/context and sampling, 8192 output cap, seeds0/1, one response per arm/source/seed. Alternate arm order by source/seed to reduce order effects. At twelve eligible sources the maximum is48 student calls. No response retry for poor mathematics or malformed long output. Preserve missingness; technical transport retries follow the existing once-only rule.

Score with the provisionally calibrated evaluate_p3 and separately source_recovery_p2. Preserve p2 historical comparisons. Independently check every apparent grounded semantic success and all judge disagreements. New judged or malformed responses do not get post-hoc clue repairs. The exact rendered request, model/runtime settings, usage, and prompt/evidence hashes are required artifacts.

## Endpoints and decisions

Primary development contrast: source-paired difference in grounded semantic recovery using seed0, with all allocated families in the end-to-end denominator and accepted-input results separately. Seed1 is a robustness check and cannot rescue primary failures. Secondary contrasts: source-average score/100, general grounded validity, copy-only failures, semantic category, token use, and truncation rate. Report paired source bootstrap intervals for continuous effects and paired binary counts without treating the two seeds as independent families.

A directional improvement with at least two independently verified new primary recoveries is a promising development signal, not confirmation. Preserve a regression if the incumbent recovers families the candidate loses; report both discordant counts. If gains are uncertain or only generic alternatives improve, mark inconclusive and investigate rather than promote. If there is no substantive recovery improvement, reject the package for the next stage and inspect information sufficiency/capability. A mean in20–75 alone is never sufficient. Do not select the package merely because it crosses the desired score band.

At most two student arms and one input policy in this study. Reserve at most $.75 for preparation, conversion audits/repairs and judgments, within the remaining global$5 cap, at most four paid calls concurrently. Freeze exact call manifests per stage and check remaining global spend before submission. Preparation uncertainty may consume the budget and require a checkpoint; it does not justify reducing disclosure checks. No training, C25 confirmation, or replication claim follows from this development experiment.
