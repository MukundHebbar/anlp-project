Create partial mathematical observations for reconstructing an original question from its final answer. The student should infer missing question structure and check a plausible reconstruction, not merely copy a question or a complete calculation.

Return an ordered bank of six supported, concise, ordinary-sentence observations, or NOT_SUITABLE. The first four must be a coherent core; the last two add useful information. Prefixes of3,4,6 will be independently audited. Do not pad with redundant sentences. Equations inside sentences are welcome.

Preserve useful distinguishing structure. Withhold at least one essential premise, parameter, relation or exact target even at the richest exposure. The exact target need not always be supplied, and the missing element need not always be numerical. Do not hide so much that the observations lose a coherent mathematical interpretation. Do not publish the full question, a disguised known value, a complete solution, or routinely a complete parameter-to-answer formula. An answer-conditioned inference can be elementary without being leakage.

Few-shot pattern1:
Source: rectangle perimeter20, area24; find its longer side. Answer6.
Core observations: sides x,y are positive; x+y=10; the requested result is the larger side; writing the unreported area K gives x(10-x)=K.
Optional observations: the two roots represent interchangeable sides; the side lengths cannot both exceed5.
Private certificate: infer the other side4 from the answer6, then K24; recover the original question. K is not publicly supplied. This demonstrates missing-premise reconstruction.

Few-shot pattern2:
Source: a monic quadratic has roots2 and3; find its coefficient of x. Answer-5.
Core observations: the polynomial is monic and quadratic; both roots are real; its roots are2 and3; root-factor expansion relates its coefficients to the roots.
Optional observations: the constant coefficient equals the product of the roots; the root sum is5.
Private certificate: infer the linear-coefficient target from the supplied-5 and expansion (x-2)(x-3)=x²-5x+6. The exact target and full expansion are not public. Other artificial targets remain possible; do not claim uniqueness. This demonstrates missing-target reconstruction.

Return JSON only:
{"status":"OK","clues":[{"id":"c1","sentence":"...","hidden_support":"Source support; private"}],"withheld":"Essential question information omitted at each prefix","private_certificate":"Check that the original fits; show reconstruction inference and acknowledge alternatives"}
or {"status":"NOT_SUITABLE","reason":"..."}.
An OK bank must have exactly six clue objects. The examples explain the policy; do not copy their mathematical content into unrelated sources. Do not grade likely student success or request a desired score distribution.

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION: {{CHECKED_SOLUTION}}
