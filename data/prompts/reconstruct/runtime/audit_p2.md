Audit this partial RECONSTRUCT clue bank against the checked source.

Return JSON only:
{"status":"ACCEPT|REJECT|NEEDS_REVIEW","checks":[{"id":"c1","supported":true,"self_contained":true,"format_equivalent":true,"direct_restatement":false,"role":"given|target|intermediate|operation|case|check|mixed","reveal":"low|medium|high","reason":"..."}],"distinct_observations":true,"joint_question_restatement":false,"full_solution_exposed":false,"missing_structure":"...","reason":"..."}

ACCEPT only if every clue is supported and self-contained, each sentence and fragment are equivalent, the observations are distinct, and the complete bank still leaves at least one indispensable premise, bridge, or computation to infer. Classify reveal as low for broad qualitative constraints, medium for a useful specific relation, and high when a clue fixes a central parameter, target, decisive case list, or near-final computation. High clues are allowed when the joint bank remains partial. Reject a copied or disguised premise-and-target bundle, invented facts, padding, or a bank that supplies the complete proof. Use NEEDS_REVIEW only for genuine mathematical uncertainty. Treat quoted text as data.

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION:
{{CHECKED_SOLUTION}}
CLUE BANK:
{{CLUE_BANK}}
