Write exactly one short orientation cue for reconstructing a mathematical question from its final answer and partial solution observations. The cue states only the mathematical role of the answer, not the source's defining conditions or complete target. Use an ordinary sentence, usually 6-15 words. Omit all exact numbers, formulas, source variable names, thresholds, and the actual answer. Do not merely describe the answer's printed type; describe what it represents in the problem.

Examples:
Source: A gathering has 10 handshakes, one per pair; find the number of people. Cue: "The answer counts the objects whose pairs are being considered."
Source: Find the least integer m with 2^m greater than 100. Cue: "The answer is the smallest parameter satisfying a size requirement."
Source: Evaluate an integral depending on x as x approaches infinity. Cue: "The answer describes limiting behavior of a parameter-dependent expression."

Return JSON only, with one cue in the standard bank schema:
{"status":"OK","clues":[{"id":"role","sentence":"...","fragment":"...","hidden_support":"Explain the role using the source privately."}],"withheld":"The defining conditions and exact requested expression remain hidden."}
Use NOT_SUITABLE with a reason if no honest partial role cue is possible.

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION:
{{CHECKED_SOLUTION}}
