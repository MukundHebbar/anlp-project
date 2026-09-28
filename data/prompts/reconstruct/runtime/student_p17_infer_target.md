Reconstruct the original mathematical question from its final answer and partial observations. Return one fully specified question whose solution has that answer and substantively uses all observations. Equivalent mathematical formulations are welcome.

Use the answer as a constraint to infer missing premises, parameters, or the requested target. Put those inferred details into the question itself. Do not simply rephrase the observations while leaving an essential count, length, center, or condition unspecified. If several reconstructions fit, choose one plausible coherent version and state your assumptions; do not claim uniqueness. Do not insert the answer as an assumed premise or invent an unrelated question with the same answer. Verify your proposed question mathematically in a concise justification.

Example:
Final answer: 4.
Observations: The data are2,3 and7. Their sum is12. Each entry has equal weight.
Output: {"question":"What is the arithmetic mean of2,3 and7?","justification":"The target is missing. The sum12 divided by the three equally weighted entries gives4, matching the supplied answer; the sum itself is12 and the median is3. Thus the arithmetic mean is a plausible target. The reconstructed question has answer(2+3+7)/3=4 and uses the observations.","assumptions":["I inferred the arithmetic-mean target from the answer and equal-weight observations; I do not claim it is the only conceivable question."]}

Return JSON only:
{"question":"...","justification":"...","assumptions":["..."]}

FINAL ANSWER: {{FINAL_ANSWER}}
OBSERVATIONS:
{{RENDERED_CLUES}}
