Reconstruct the original mathematical question from its final answer and partial observations. Return one fully specified question whose solution has that answer and substantively uses all observations. Equivalent mathematical formulations are welcome.

Use the answer as a constraint to infer missing premises, parameters, or the requested target. Put those inferred details into the question itself. Do not simply rephrase the observations while leaving an essential count, length, center, or condition unspecified. If several reconstructions fit, choose one plausible coherent version and state your assumptions; do not claim uniqueness. Do not insert the answer as an assumed premise or invent an unrelated question with the same answer. Infer the missing details before writing the question. The returned question must ask for the ORIGINAL requested quantity, whose answer is the supplied final answer; do not instead ask the reader to find your missing premise. State the concrete inferred premises briefly in assumptions first, then write the complete question, then verify it mathematically in a concise justification.

Example:
Final answer: 6.
Observations: A rectangle has side lengths summing to10. The requested quantity is the longer side. Area in terms of side x is x(10-x).
Output: {"assumptions":["The supplied longer side6 and side sum10 imply other side4 and missing area24."],"question":"A rectangle has perimeter20 and area24. What is its longer side length?","justification":"For this reconstructed question, x(10-x)=24 gives sides4 and6, so the longer side is6. All observations describe this setup. The requested answer is6; area24 is an inferred premise, not the question target."}

Return JSON only:
{"assumptions":["Concrete inferred premise(s), with brief support"],"question":"...","justification":"..."}

FINAL ANSWER: {{FINAL_ANSWER}}
OBSERVATIONS:
{{RENDERED_CLUES}}
