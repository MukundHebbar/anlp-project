Audit the proposed RECONSTRUCT evidence against its source. A broad cue about what the final answer represents is allowed. All exact defining conditions and the full target together must remain undisclosed. A role cue must not contain a source-specific number, variable, formula, threshold, or the actual answer. It may identify a generic mathematical quantity such as a limit, count, extremal size, admissible object, or singularity order.

If this is a combined bank, check all observations jointly: adding the role cue must still leave substantive missing premises, an exact expression, or a mathematical inference. Reject if the question is now directly restated or the full proof is supplied. Each observation must be true, intelligible, and have source support. A role cue is intentionally orientation rather than a derived formula; do not reject it merely for naming the type of target.


For leakage judgments, use only FINAL ANSWER and the public sentence/fragment fields. The private source and hidden_support establish truth, but their unexposed definitions are not available to the student. Do not silently supply those definitions and then declare a full proof exposed. Identify precisely which public sentences reveal the full premise-and-target bundle or all essential proof steps. A derivation that needs an absent source definition is not already fully disclosed.

Contrastive example: if the hidden solution defines u_i=3^{v_i}, but the public clues show only a telescoping sum u_n-u_0 and v_0=0, the relation between u and v is still missing. Do not assume the student saw u_i=3^{v_i} when auditing disclosure. Conversely, if every defining condition and the requested quantity appear in public sentences, an unfinished calculation does not rescue question leakage.

The new role cue itself must contain no source-specific numeric quantity, including spelled-out counts such as "four". This restriction applies to the role cue, not the pre-existing mathematical observations.

Return JSON only:
{"status":"ACCEPT|REJECT|NEEDS_REVIEW","role_cue_partial":true,"supported":true,"joint_question_restatement":false,"full_solution_exposed":false,"missing_structure":"What substantive information still must be inferred?","reason":"..."}

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION:
{{CHECKED_SOLUTION}}
CLUE BANK:
{{CLUE_BANK}}
