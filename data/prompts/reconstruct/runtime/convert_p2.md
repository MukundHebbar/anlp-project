Create a partial RECONSTRUCT clue bank from the checked mathematical source. A student will see the final answer and selected clues, but not the question or solution, and must construct and verify one plausible question.

Return JSON only:
{"status":"OK","clues":[{"id":"c1","sentence":"...","fragment":"...","hidden_support":"..."}],"withheld":"the exact source question"}
or {"status":"NOT_SUITABLE","reason":"..."}.

Give one to four distinct observations from the solution. Each sentence must stand on its own; its fragment must express the same fact more compactly; hidden support explains where the fact comes from. Prefer intermediate relations, operations, case splits, or local values. Across the whole bank, leave at least one indispensable premise, bridge, or computation for the student to infer. If the clues plus the supplied answer already constitute a complete proof, remove or weaken the clue that closes it. Do not copy or paraphrase the full premise-and-target bundle, invent facts, or pad the bank.

Contrastive example: if a counting solution proves an upper bound and then gives a construction attaining it, clues may expose the pair-counting idea and structural features of the construction, but should not state both the completed numerical upper bound and the existence of an object attaining that same number.

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION:
{{CHECKED_SOLUTION}}
