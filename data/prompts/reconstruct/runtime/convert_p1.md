Create a RECONSTRUCT clue bank from the checked mathematical source below. A student will see only the final answer and some clues, then construct one plausible question and verify it.

Return JSON only:
{"status":"OK","clues":[{"id":"c1","sentence":"...","fragment":"...","hidden_support":"..."}],"withheld":"..."}
or {"status":"NOT_SUITABLE","reason":"..."}.

Produce one to four distinct, useful observations actually supported by the solution. Prefer four when honest. Each sentence must be understandable without the hidden question; its fragment must state exactly the same fact more compactly. Hidden support cites why it is true. Keep useful intermediate relations, operations, case splits, or values. Leave meaningful structure to infer. Do not paraphrase the whole question, expose its premise-and-target bundle, give the entire solution, invent facts, split one fact artificially, or pad weak solutions. Non-uniqueness is allowed.

Example: from a factorial/base solution, useful clues might say that one prime exponent has contributions 6,3,1; another has 4,1; and one exponent is halved before a minimum. They should not say “find trailing zeros of 12! in base 12.”

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION:
{{CHECKED_SOLUTION}}
