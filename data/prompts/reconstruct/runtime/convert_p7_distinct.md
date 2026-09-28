Convert a mathematical question and checked solution into informative partial observations for reconstructing the original question from its final answer. Keep its objects, target role and distinctive structural constraints. Withhold an essential question premise, parameter or relation that the student must infer; do not hide most of the structure.

Return JSON only:
{"status":"OK","clues":[{"id":"c1","sentence":"...","fragment":"...","hidden_support":"..."}],"withheld":"The essential missing question content and the mathematical inference connecting it to the answer/observations"}
or {"status":"NOT_SUITABLE","reason":"..."}.

Use3–6 useful observations in ordinary sentences, without padding. Each clue should contribute a distinct constraint or incomplete intermediate calculation. Retain source-supported counts, symmetries, domain restrictions and relationships rather than replacing them with generic descriptions. A quantity's definition repeated in new words is not extra information. Include a useful partial intermediate relation where available, but stop before a complete solution. If a withheld numerical premise has a role in that relation, name it with a symbol and say what it represents; omit its value. Each fragment means exactly its sentence; hidden_support privately identifies its verified source basis.

Audit the entire bank together. Reject full equivalent premise-target bundles and complete/nearly complete derivations, even without verbatim copying. Do not encode the missing value as an arithmetic expression with all operands disclosed. A missing existence witness is solution information, not a missing question premise. The final answer itself is intentionally public. Answer-conditioned inverse inference is legitimate even when elementary. Some ambiguity is permitted; do not falsely claim the original is uniquely identified or replace it with a different same-answer task.

Example:
Source: A rectangle has perimeter20 and area24. Find its longer side. Answer6.
Clues: The rectangle's sides sum to10. The target is its longer side. If A denotes its unreported area, a side x obeys x(10-x)=A.
Privately: missing area24; answer6 and sum10 imply the other side4 and area24. Keep A symbolic; do not expose xy=24 too, which would give the complete question.

Example:
Source: A bag contains six red and four blue balls. Two are drawn without replacement. Find the probability both are red. Answer1/3.
Clues: Two balls are drawn without replacement from a bag containing only red and blue balls. There are four blue balls and an unreported positive integer number r of red balls. The target is the probability both draws are red. The first draw is red with probability r/(r+4); after that red draw, r-1 red balls remain.
Privately: r=6 is missing. The student must construct the second conditional probability and infer r using the supplied answer. Do not provide the full probability equation, its solution r=6, or a numerical first-draw probability that directly encodes r.

Negative: roots sum10, product21, and selecting the larger root already expose the full question x²-10x+21=0. Also reject an existence question disguised as a description of its requested witness. Rephrasing is not withholding mathematical information.

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION:
{{CHECKED_SOLUTION}}
