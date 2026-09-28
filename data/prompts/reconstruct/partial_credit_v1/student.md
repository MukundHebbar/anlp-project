Reconstruct one plausible original mathematical question from its final answer and partial observations. Equivalent mathematical formulations are welcome. The observations may leave premises, relationships or the requested quantity uncertain.

First state brief inferred premises, then write a complete standalone question, then briefly verify it against every observation and the supplied answer. Put necessary inferred values and conditions in the question itself. If several questions fit, choose one coherent version and acknowledge your choices. Do not assume that the original is uniquely identified.

Preserve the requested quantity when the evidence specifies it. Do not ask for a missing premise instead. Do not make the requested answer a premise of your question. Do not change a given to force the answer, or invent an unrelated question sharing the same number.

Example:
Answer6. Observations: positive rectangle sides x,y sum to10; the requested quantity is the larger side; for an unreported area K, x(10-x)=K.
Output: {"assumptions":["The larger side6 implies the other side4, so I infer the missing area24."],"question":"A rectangle has perimeter20 and area24. What is its longer side?","justification":"Its sides satisfy x+y=10 and xy=24, giving (x-4)(x-6)=0. The longer side is6, and the observations describe this setup."}

Example:
Answer-5. Observations: a monic quadratic has real roots2 and3; its coefficients are related to these roots by factorization.
Output: {"assumptions":["I infer that the requested quantity is the coefficient of x; this is a plausible target, not a uniqueness claim."],"question":"A monic quadratic polynomial has roots2 and3. What is its coefficient of x?","justification":"The polynomial is (x-2)(x-3)=x²-5x+6, whose linear coefficient is-5."}

Return JSON only:
{"assumptions":["Brief inferred premises and support"],"question":"...","justification":"..."}

FINAL ANSWER: {{FINAL_ANSWER}}
OBSERVATIONS:
{{RENDERED_CLUES}}
