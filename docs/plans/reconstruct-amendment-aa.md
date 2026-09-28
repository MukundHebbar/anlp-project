# AA: richer exposure, prospective development screen

User requested equivalent mathematical reformulations count as correct and 20–40% correct reconstructions. Keep source_recovery_p2 unchanged: equivalence requires a correspondence preserving feasible cases, quantifiers and target, not literal wording. Keep mean rubric 20–75 separately. On a future frozen 25-family confirmation, target 5–10 grounded semantic recoveries. This development screen cannot establish that population rate.

Use all twelve previously allocated D4 families [0,13,46,62,63,80,87,96,118,120,129,137], including failures. No new source selection based on Qwen results. Preserve the same Qwen3-4B Q4_K_M nonthinking runtime, student_p10, seed0 primary, 8192-token cap and established sampling. No confirmation data opened.

DeepSeek convert_p6_rich generates one six-observation bank per family. Retain the target role and more distinctive source constraints, while withholding at least one essential question premise that must be inferred from the answer. The missing item cannot merely be a solution witness. Do not reveal the complete question, an equivalent premise-target bundle, or a complete derivation. Six clues are a tested setting, not a claimed optimum.

Three within-source arms, frozen before student calls:
- sparse3: first three observations (same bank prefix).
- rich6: all six observations.
- dense3: pair adjacent observations (1,2), (3,4), (5,6), concatenated verbatim into three displayed clues. Exactly the rich6 propositions in the same order, without model rewriting.

The generator puts useful object/target context in the first three and additional genuine constraints/observations in the last three. sparse3 vs rich6 measures the package of extra information and extra clues; rich6 vs dense3 measures packaging at equal information, not information gain. Raw sentence and word counts will be reported. This is a global conversion-policy experiment; no source-specific repairs after seeing student outputs.

One conversion attempt per source, no score-driven retry. Audit full bank with support_p1, public_p5, source_disclosure_p4, then source-blind copy challenge and assistant analytic review. These auditors remain provisional: X controls passed; Y source_p3 failed a missing-witness case; p4 passed the Y regression, but Z has one unresolved technical slot and a corrected authored reference. Do not claim near-perfect accuracy. Reject/uncertain/unsupported banks are excluded before Qwen and remain failures in the 12-source end-to-end denominator. Subsets/groupings get explicit public-input review; do not fabricate audit calls for derived inputs.

Run seed0 across all eligible families and all three arms, rotating arm order by source. Evaluate p3 grounding and p2 semantic recovery, source-blind grounding first. Independently inspect every claimed semantic success and any disagreements; count only correct answer, source equivalence, supported substantive inference and all clues used. Preserve semantic-only, grounded-only, joint, conditional and end-to-end rates separately. API errors remain missing and visible. No success claim based on one lucky seed or alternative same-answer question.

Budget: at most $0.75 additional recorded DeepInfra cost, within global $5 ceiling; at most four paid requests concurrently. No more than 12 conversions, 36 audits, 12 copy challenges, 36 Qwen draws and 72 judgments initially. Stop for report once terminal. If no arm reaches target, diagnose missing source constraints vs student math failure vs unavoidable ambiguity before registering a next global policy; do not relax leakage gates or tune on held-out data. Prefer simplest eligible arm if outcomes comparable. Historical W is contextual only because prompt/eligibility differ.

Evidence: immutable source and prompt hashes, exact raw requests/outputs, exclusion reasons, reviews with mathematical counterexamples/correspondences, per-source paired table, score distribution and uncertainty. Report best among tested policies, never universal best. Z2 is deferred to prioritize this user-requested exposure experiment; retain Z's reference correction.

Pre-student implementation correction: adjacent pairing replaces the initially written interleaving pairing. No Qwen calls or results existed at this correction. This holds proposition order fixed in rich6 vs dense3, isolating bullet grouping rather than changing grouping and order together. Each dense clue can contain two ordinary sentences; the treatment is displayed clue grouping, not grammatical sentence count.
