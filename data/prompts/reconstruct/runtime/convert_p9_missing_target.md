Create partial mathematical observations for recovering the ORIGINAL question from its final answer. Retain the essential premises, domains and numerical values, but withhold WHAT WAS ASKED: the requested quantity, property or operator. Give useful setup and partial intermediate facts from the checked solution. The student must infer a plausible requested target using the final answer and these observations.

Return JSON only:
{"status":"OK","clues":[{"id":"c1","sentence":"...","fragment":"...","hidden_support":"..."}],"withheld":"Name the omitted original target, verify that solving the reconstructed question produces the supplied answer, and discuss alternative targets that could also fit."}
or {"status":"NOT_SUITABLE","reason":"Why a supported, partial, non-leaking conversion could not be found."}.

Use3–5 ordinary sentence observations with distinct purposes. The fragment has the sentence's meaning; hidden_support privately checks source support. Do not state the requested target, its synonym, an equivalent question or a formula specifying that target. Do not expose the complete or nearly complete calculation. Do not merely remove a question mark from the original. Never invent premises to force uniqueness. The final answer is public, but do not add target-revealing labels to it or smuggle the target into clues as an instruction. Private verification is not public evidence. Some ambiguity is expected; distinguish a plausible reconstruction from a proof of unique intent. If no useful nonredundant partial bank is possible, abstain.

Example1:
Source: Find the arithmetic mean of2,3,7. Answer4.
Output: {"status":"OK","clues":[{"id":"c1","sentence":"The data consist of the three real numbers2,3 and7.","fragment":"data2,3,7","hidden_support":"These are the exact source entries."},{"id":"c2","sentence":"Their total is12.","fragment":"sum12","hidden_support":"2+3+7=12, an intermediate step in the checked calculation."},{"id":"c3","sentence":"Each entry contributes with the same weight.","fragment":"equal weights","hidden_support":"The source arithmetic mean weights all three entries equally."}],"withheld":"The arithmetic-mean target is omitted. The equally weighted mean is12/3=4, matching the answer. Sum12, median3 and range5 do not match; this supports the mean among usual summaries but does not prove no other invented target gives4. The final division is not public."}

Example2:
Source: A monic quadratic has roots2 and3. What is its coefficient of x? Answer-5.
Output: {"status":"OK","clues":[{"id":"c1","sentence":"The polynomial is quadratic and its leading coefficient is1.","fragment":"monic quadratic","hidden_support":"This is the given polynomial class."},{"id":"c2","sentence":"Its roots are2 and3.","fragment":"roots2,3","hidden_support":"Both roots are specified in the source."},{"id":"c3","sentence":"It can be written as a product of the two factors x-2 and x-3.","fragment":"factorization(x-2)(x-3)","hidden_support":"Monicity and the two roots give this factorization, a partial algebraic step."}],"withheld":"The coefficient-of-x target is hidden. Expanding the product gives x^2-5x+6, whose linear coefficient is-5. The expanded polynomial and the target are not public. Other artificially constructed targets could also produce-5; claim plausibility, not uniqueness."}

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION:
{{CHECKED_SOLUTION}}
