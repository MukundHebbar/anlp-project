Audit this structured RECONSTRUCT clue bank against the checked source.

Return JSON only:
{"status":"ACCEPT|REJECT|NEEDS_REVIEW","checks":[{"id":"c1","supported":true,"self_contained":true,"format_equivalent":true,"direct_restatement":false,"role":"orientation|reasoning","reason":"..."}],"orientation_present":true,"orientation_leaks_question":false,"distinct_observations":true,"full_solution_exposed":false,"missing_structure":"...","reason":"..."}

ACCEPT only if there are exactly four supported, self-contained, distinct clues; sentence and fragment forms are equivalent; c1 is an orientation cue that makes the mathematical setting interpretable without restating the full premise and target; c2-c4 are reasoning observations; and the whole bank still leaves an indispensable premise, bridge, or computation to infer. Reject answer disclosure, a disguised question, invented facts, padding, or a complete proof. Use NEEDS_REVIEW only for genuine mathematical uncertainty.

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION:
{{CHECKED_SOLUTION}}
CLUE BANK:
{{CLUE_BANK}}
