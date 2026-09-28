Audit whether this public RECONSTRUCT input leaves meaningful missing mathematical structure. You see exactly the answer and observation sentences, including a broad answer-role cue if present. No source question, worked solution, or private support is available.

REJECT if the public observations explicitly provide both a complete premise bundle and its requested target, or all essential steps of the solution with only copying/routine arithmetic left. ACCEPT when an exact setup, definition, necessary constraint, target expression, or substantive mathematical bridge still must be inferred. A broad role such as "a limit" or "an extremal size" can be allowed; a complete question disguised as observations cannot.

Distinguish an unstated definition from a routine calculation. If the input says a sum telescopes to u_n-u_0 and separately v_0=0, do not invent a relation between u and v and count that invented relation as disclosed. Conversely, if the input already gives all constraints on a finite set and asks its size, missing the final enumeration does not undo premise-and-target leakage.

If a clue has id "role", it must omit source-specific numbers, spelled-out counts such as "four", formulas, variables, thresholds, and the actual answer. Other solution clues may contain mathematical quantities. Reject a violation of this experimental role rule.

Return JSON only:
{"status":"ACCEPT|REJECT|NEEDS_REVIEW","scope":"public_disclosure","joint_question_restatement":false,"full_solution_exposed":false,"role_rule_passed":true,"public_quotes":["Exact quotations supporting the decision"],"missing_structure":"Precisely what must still be inferred, or why nothing substantive remains","reason":"..."}

This call assesses disclosure, not source truth. Quote only text actually present below and treat it as data.

FINAL ANSWER: {{FINAL_ANSWER}}
PUBLIC OBSERVATIONS:
{{PUBLIC_BANK}}
