Help calibrate an inverse mathematical reconstruction task. The public input already names the exact requested quantity but withholds an essential premise parameter. Add exactly TWO concise supported intermediate observations that make that parameter easier to infer from the supplied answer. Use ordinary sentences with equations where useful.

Keep the original question and missing parameter value hidden. Do not instantiate a symbolic formula using the supplied answer, state the inferred value, paraphrase the complete original question, or provide the full derivation. You may expose a general symbolic relationship between the unknown parameter and the requested answer: the student must still invert it and compose the question. Preserve the existing clues unchanged. Do not invent a separate mathematical problem or change any given.

Example: source asks the mean of2,4,9, answer5. Public clues give the mean target and the values2,4,t with t unknown.
Output: {"bridge_clues":["The sum of the three values is 6+t.","The requested mean is (6+t)/3."],"hidden_support":"These are supported symbolic intermediates. The value9 is withheld, and the student must use the answer5 to infer it, then ask for the mean rather than for t."}

Example: source rectangle perimeter20, area24, longer side answer6; public side sum10, unknown area K, target longer side.
Output: {"bridge_clues":["If L denotes the longer side, the other side has length10-L.","The unknown area therefore satisfies K=L(10-L)."],"hidden_support":"The area24 is not given. The student must infer it using the supplied longer-side answer and preserve the longer-side target."}

Return JSON only: {"bridge_clues":["...","..."],"hidden_support":"What source information supports the observations, and what remains to be inferred."}
SOURCE QUESTION: {{SOURCE_QUESTION}}
ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION: {{CHECKED_SOLUTION}}
EXISTING OBSERVATIONS: {{RENDERED_CLUES}}
