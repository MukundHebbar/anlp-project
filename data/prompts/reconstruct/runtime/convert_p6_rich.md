Create informative but genuinely incomplete observations for reconstructing the original mathematical question from its final answer. The student sees only the answer and observations. Make recovery feasible: preserve the requested quantity's role, the mathematical objects, and distinctive constraints. Withhold one essential question premise or relation that must be inferred using the answer; do not withhold most of the structure.

Return JSON only:
{"status":"OK","clues":[{"id":"c1","sentence":"...","fragment":"...","hidden_support":"..."}],"withheld":"Exactly which essential QUESTION premise is absent, why it is not already stated equivalently, and how answer-conditioned inference can recover it"}
or {"status":"NOT_SUITABLE","reason":"..."}.

Produce exactly six distinct, supported observations in ordinary sentences. Each fragment expresses the same proposition and hidden_support gives its checked basis. First three: useful object/target context and partial constraints. Last three: additional distinctive constraints or intermediate observations. Do not pad with redundant restatements. A clue may reveal source facts directly; the WHOLE bank must still leave a real question premise absent. Prefer retaining structure over generic hints. Do not encode the missing premise as an arithmetic expression with all inputs present. Never expose the whole equivalent question or a complete/nearly complete derivation. A missing witness to an existence question is not a missing question premise. If six useful observations cannot satisfy this, return NOT_SUITABLE.

Example of legitimate inverse inference:
Source: A rectangle has perimeter20 and area24. Find its longer side. Answer6.
A partial bank can retain rectangle, x+y=10, and longer-side target while withholding area24. The answer6 and sum10 let the student infer other side4 and missing area24. Do not give xy=24 too: that would expose the full question. This small example does not justify padding it to six observations.

Example with richer structure:
Source: A bag contains six red and four blue balls. Two are drawn without replacement. Find the probability both are red. Answer1/3.
Allowed six observations: (1) A bag contains only red and blue balls. (2) Two balls are drawn without replacement. (3) The requested quantity is the probability that both draws are red. (4) The bag contains four blue balls. (5) If r is the initial red count, after drawing one red there are r-1 red balls left. (6) Unordered pairs can be counted using binomial coefficients.
Privately: withhold initial red count6. Infer r from C(r,2)/C(r+4,2)=1/3, whose positive integer solution is6. Do not supply that entire equation as an extra clue or the red count in disguised arithmetic. All six observations hold, but the source question still lacks a required count.

Negative example: clues giving the roots' sum10, product21, and selecting the larger root already expose "find the larger root of x²-10x+21". Reject even without copying words. Likewise saying an integer square ending in6 exists discloses that existence question even if witness16 is omitted.

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION:
{{CHECKED_SOLUTION}}
