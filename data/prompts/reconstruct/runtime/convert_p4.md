Create sparse supported observations for reconstructing the essential mathematical question from its final answer. The student sees the answer and observations, never the source question or checked solution. Preserve useful indirect evidence about the original structure while withholding a meaningful part of the question. Valid inference is required; copying an equivalent formulation must not suffice.

Return JSON only:
{"status":"OK","clues":[{"id":"c1","sentence":"...","fragment":"...","hidden_support":"..."}],"withheld":"Name the essential source premise, target, or relation absent from the whole public bank and what inference connects it to the clues"}
or {"status":"NOT_SUITABLE","reason":"..."}.

Produce one to four distinct intermediate observations, only as many as are honest and useful. Each sentence is readable on its own as a local fact about an unknown setup; each fragment expresses exactly the same proposition; hidden_support identifies its verified source basis. All quantities and observations must be supported by the checked solution. Do not pad, invent clues, or use a different rule for each topic.

Audit the whole bank together with the answer before returning it. Do not display the fully specified requested coefficient, integral, equation-solving problem, optimization domain and target, or any other equivalent premise-target bundle as a clue. Removing the verb "find" does not prevent leakage. Do not give nearly all proof steps with just arithmetic left. Withhold mathematical content, not merely wording. A source fact can be withheld from the public bank while documented privately in hidden_support and withheld. The final answer itself is intentionally supplied and is not a complete derivation.

Preserve what the intermediate quantities refer to and prefer observations distinctive of this source over generic lemmas that apply to many unrelated questions. Where supported, retain the role of the requested quantity (for example, a count, an extremum, or a truth claim) while withholding an essential mathematical premise or relation needed to specify the original task. Do not strip both the target role and all distinctive constraints merely to pass disclosure checks. Quantity-role wording must remain source-supported, and must not expose the complete premise-target bundle or leave only routine assembly of the question. If informative observations cannot satisfy these restrictions, return NOT_SUITABLE.

Positive example:
Source: A rectangle has perimeter20 and area24. Find its longer side. Answer6. Checked solution: x+y=10, xy=24; x(10-x)=24 gives sides4,6.
Output: {"status":"OK","clues":[{"id":"c1","sentence":"The two side lengths x and y satisfy x+y=10.","fragment":"x+y=10 for the two sides","hidden_support":"Perimeter20 gives2(x+y)=20."},{"id":"c2","sentence":"Expressing area in terms of one side x gives x(10-x).","fragment":"Area=x(10-x)","hidden_support":"Substitute y=10-x in area xy."}],"withheld":"The area24 and longer-side target are not stated. The student must recover a compatible missing area constraint and target from the answer and the side/area relations."}

Negative example:
Source: Find the larger root of x²-10x+21=0. Answer7.
Bad bank: "The roots sum to10", "The roots multiply to21", "Select the larger root". This is the complete source question in equivalent form, even without copying its polynomial. Do not return this bank; retain a genuinely partial supported observation or return NOT_SUITABLE if no useful sparse bank is available. A clue containing the complete polynomial and root target is equally bad.

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION:
{{CHECKED_SOLUTION}}
