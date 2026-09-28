Reconstruct the original mathematical question from its final answer and partial observations. Return one fully specified question whose solution has that answer and substantively uses all observations. Equivalent mathematical formulations are welcome.

Use the answer as a constraint to infer missing premises, parameters, or the requested target. Put those inferred details into the question itself. Do not simply rephrase the observations while leaving an essential count, length, center, or condition unspecified. If several reconstructions fit, choose one plausible coherent version and state your assumptions; do not claim uniqueness. Do not insert the answer as an assumed premise or invent an unrelated question with the same answer. Verify your proposed question mathematically in a concise justification.

Preserve the requested quantity whenever the observations specify it. The inferred missing value belongs in the premises of your question, replacing its unknown placeholder; it must not become the quantity your question asks for. In the rectangle example, ask for the longer side after inferring area24; asking for the area given longer side6 reverses the task and is not a reconstruction.

Example:
Final answer: 6.
Observations: A rectangle has side lengths summing to10. The requested quantity is the longer side. Area in terms of side x is x(10-x).
Output: {"question":"A rectangle has perimeter20 and area24. What is its longer side length?","justification":"The supplied longer-side answer6 and side sum10 imply the other side4, so the missing area is24. For the reconstructed question, x(10-x)=24 has roots4 and6; the longer side is6. All three observations describe this setup.","assumptions":["I inferred the missing area constraint24 using the answer, rather than leaving the rectangle's area unspecified."]}

Return JSON only:
{"question":"...","justification":"...","assumptions":["..."]}

FINAL ANSWER: {{FINAL_ANSWER}}
OBSERVATIONS:
{{RENDERED_CLUES}}
