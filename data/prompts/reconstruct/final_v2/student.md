Reconstruct one plausible original mathematical question from its final answer and partial observations. Equivalent mathematical formulations are welcome. The observations may leave premises, relationships or the requested quantity uncertain.

Work out your reconstruction first; you may reason before the JSON. Keep that reasoning brief: settle on one question, check it once, and do not draft alternatives. Then output exactly one JSON object, at the end, with three fields:
- "assumptions": brief inferred premises and their support.
- "question": one complete, standalone question, and nothing else.
- "justification": a brief check that the question's answer is the supplied final answer and that it fits every observation.

Put necessary inferred values and conditions in the question itself. If several questions fit, choose one coherent version and mention your choices in "assumptions". Do not assume that the original is uniquely identified.

Preserve the requested quantity when the evidence specifies it. Do not ask for a missing premise instead. Do not change a given to force the answer, or invent an unrelated question sharing the same number.

The "question" field receives no credit if it:
- states its own answer, for example an "Answer: ..." line, a note giving the answer, or a premise that gives the value it asks for;
- only asks to repeat the final answer;
- contains reasoning, drafts, alternatives, self-corrections, notes or labels such as "Justification:" or "Observations:".
Write only the final question there.

Example:
Answer: 6. Observations: positive rectangle sides x, y sum to 10; the requested quantity is the larger side; for an unreported area K, x(10 - x) = K.
Output: {"assumptions":["The larger side 6 implies the other side 4, so I infer the missing area 24."],"question":"A rectangle has perimeter 20 and area 24. What is its longer side?","justification":"Its sides satisfy x + y = 10 and xy = 24, giving (x - 4)(x - 6) = 0. The longer side is 6, and the observations describe this setup."}

Example:
Answer: -5. Observations: a monic quadratic has real roots 2 and 3; its coefficients are related to these roots by factorization.
Output: {"assumptions":["I infer that the requested quantity is the coefficient of x; this is a plausible target, not a uniqueness claim."],"question":"A monic quadratic polynomial has roots 2 and 3. What is its coefficient of x?","justification":"The polynomial is (x - 2)(x - 3) = x² - 5x + 6, whose linear coefficient is -5."}

Not acceptable "question" values for the first example: "A rectangle has longer side 6. What is its longer side?" (states its answer); "What is 6?" (repeats the answer); "Maybe the area is 24? No. Find the longer side." (drafting).

Output format, as the last thing in your response:
{"assumptions":["..."],"question":"...","justification":"..."}

FINAL ANSWER: {{FINAL_ANSWER}}
OBSERVATIONS:
{{RENDERED_CLUES}}
