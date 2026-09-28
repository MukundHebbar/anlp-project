Reconstruct the original mathematical question from its final answer and partial observations. Return one fully specified question whose solution has that answer and substantively uses all observations. Equivalent mathematical formulations are welcome.

Use the answer only to work out, in your own reasoning, what the missing premises, parameters, or requested target must have been. Put those *inferred* details into the question as ordinary problem data (numbers, conditions, a named target quantity) — never write the final answer's value itself into the question text, and never phrase the question as a hypothesis or given ("if X equals ANSWER, what is...", "given that the answer is ANSWER, ..."). The question you output must read exactly like an original problem statement that does not yet know its own answer: a reader seeing only your question, with no access to the final answer, should have to solve it, not read the answer off an embedded premise. If your draft question contains the literal final-answer value anywhere outside of describing an inferred, answer-independent premise, delete that draft and infer a different premise that does not require repeating the answer.

Do not simply rephrase the observations while leaving an essential count, length, center, or condition unspecified. If several reconstructions fit, choose one plausible coherent version and state your assumptions; do not claim uniqueness. Do not invent an unrelated question with the same answer. Verify your proposed question mathematically in a concise justification — the justification is where you may write the final answer and show the derivation; the question itself must not contain it.

Correct example:
Final answer: 6.
Observations: A rectangle has side lengths summing to10. The requested quantity is the longer side. Area in terms of side x is x(10-x).
Output: {"question":"A rectangle has perimeter20 and area24. What is its longer side length?","justification":"The supplied longer-side answer6 and side sum10 imply the other side4, so the missing area is24. For the reconstructed question, x(10-x)=24 has roots4 and6; the longer side is6. All three observations describe this setup.","assumptions":["I inferred the missing area constraint24 using the answer, rather than leaving the rectangle's area unspecified."]}

Forbidden pattern (answer leaked into the question, do not do this):
Final answer: 11.
Observations: The problem concerns trailing zeros of N! in base p. For prime p, trailing zeros equal v_p(N!). Legendre's formula gives v_p(N!). The desired prime is the least p with v_p(N!) < p.
Wrong output (rejected): {"question":"Find the smallest prime p such that the number of trailing zeros of N! in base p is less than p, given that the answer is 11.","justification":"...","assumptions":[...]}
Why it is wrong: the question states the answer (11) as a given fact, so it no longer needs to be solved. The correct question is identical but stops after "...is less than p." — it must not mention 11 at all.

Another forbidden pattern (answer used as a fabricated hypothesis variable):
Wrong output (rejected): {"question":"...If k=5, what is the value of the expression?","justification":"...","assumptions":[...]}
Why it is wrong: 5 is the supplied final answer, smuggled in as a premise ("if k=5") instead of being the thing the question asks the solver to find.

Return JSON only:
{"question":"...","justification":"...","assumptions":["..."]}

FINAL ANSWER: {{FINAL_ANSWER}}
OBSERVATIONS:
{{RENDERED_CLUES}}
