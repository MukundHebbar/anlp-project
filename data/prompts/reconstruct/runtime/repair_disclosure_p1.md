Revise a sparse-observation bank once after disclosure review. The student must reconstruct the essential mathematical question from the final answer and partial observations. You see the source and audit feedback; the student will see only the answer and public observations.

Check the feedback against the actual text. Preserve useful source-supported structure, but remove the demonstrated question or solution disclosure. Prefer an earlier structural observation to a decisive final simplification. Do not give a nearly complete proof with only routine arithmetic left. Do not merely rename variables, remove an asking verb, or pack the same information into fewer sentences. Withhold a substantive essential element while retaining enough distinctive evidence to motivate reconstruction. Quantities must retain understandable roles. Do not invent facts or change the source problem.

Return JSON only, using one to four distinct observations:
{"status":"OK","clues":[{"id":"c1","sentence":"...","fragment":"...","hidden_support":"..."}],"withheld":"The essential mathematical content absent from the combined answer and observations, and the inference still required"}
or {"status":"NOT_SUITABLE","reason":"..."}.

Each fragment must express the same proposition as its sentence. Hidden support must identify the basis in the checked solution. Do not pad with routine consequences of another observation. The supplied answer is intentional; it is not permission to reveal its entire derivation. If the feedback is mistaken, preserve the bank and explain that in withheld rather than inventing a defect. Do not make the task obscure solely to pass review.

Example of the distinction: for a rectangle problem with perimeter20, area24 and longer side6, observations about side sum10 and the area expression x(10-x) leave an essential area constraint absent. In contrast, displaying x(10-x)=24, the roots4 and6, and the instruction to select the longer side exposes the complete problem and solution. Repair by withholding mathematical content, not by deleting the word "find".

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION:
{{CHECKED_SOLUTION}}

ORIGINAL BANK:
{{ORIGINAL_BANK}}

PUBLIC DISCLOSURE REVIEW:
{{PUBLIC_REVIEW}}

SOURCE-AWARE DISCLOSURE REVIEW:
{{SOURCE_REVIEW}}
