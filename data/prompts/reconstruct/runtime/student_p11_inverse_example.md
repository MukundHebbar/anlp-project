You receive a final mathematical answer and unordered observations from a worked solution. Reconstruct the original mathematical question that most plausibly produced this answer and these observations. Try to recover its essential objects, constraints, and requested target, rather than inventing a different question that happens to share the answer. The original question is hidden, so infer missing structure conservatively and state important missing details you chose. Return one self-contained question and a concise mathematical verification showing that every observation belongs substantively to one coherent solution. Several questions may fit; do not claim uniqueness. Do not copy the answer into a tautological question or attach clues to an unrelated problem.

Example:
Answer: 6. Observations: a rectangle's side lengths satisfy x+y=10; its area in terms of one side is x(10-x).
Output: {"question":"A rectangle has perimeter 20 and area 24. What is its longer side length?","justification":"The supplied answer 6 and side sum 10 suggest sides 6 and 4, so I inferred a missing area constraint of 24. Independently checking the completed question: perimeter 20 gives x+y=10, and area 24 gives x(10-x)=24. Thus (x-4)(x-6)=0 and the longer side is 6. Both observations are used.","assumptions":["I inferred that the missing area was 24 and the target was the longer side; other questions might fit."]}

Return JSON only:
{"question":"...","justification":"...","assumptions":["..."]}

FINAL ANSWER: {{FINAL_ANSWER}}
OBSERVATIONS:
{{RENDERED_CLUES}}
