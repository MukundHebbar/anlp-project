Create partial mathematical observations for recovering the ORIGINAL question from its final answer. Preserve its requested quantity, domain, quantifiers and all but ONE essential premise. Replace that premise by a named unknown. Prefer a numerical premise that can be inferred by a short mathematical calculation using the supplied answer and retained constraints. Do not delete the target, several independent parameters, or the distinguishing structure merely to make clues sparse.

Return JSON only:
{"status":"OK","clues":[{"id":"c1","sentence":"...","fragment":"...","hidden_support":"..."}],"withheld":"State the one original premise withheld, then actually work the inverse inference from the PUBLIC answer and clues. Identify any ambiguity honestly."}
or {"status":"NOT_SUITABLE","reason":"Why no such partial, non-leaking conversion was found."}.

Use3–5 ordinary sentence observations, each with a distinct purpose. The fragment has exactly the sentence's meaning; hidden_support privately establishes source support. Observations may describe setup and an incomplete intermediate relation, but must not display the whole source premise-target bundle or a complete/nearly complete worked solution. Do not reveal the missing value through an arithmetic expression that evaluates to it without using the final answer. Missing a solution witness alone does not hide a question premise. Never invent source constraints to force uniqueness. The private inverse calculation is a certificate for review, NOT an extra public clue. If the certificate cannot be completed, return NOT_SUITABLE. A certificate is not proof until independently checked.

Example1:
Source: Find the arithmetic mean of2,4,6,8,10. Answer6.
Output: {"status":"OK","clues":[{"id":"c1","sentence":"The requested quantity is the arithmetic mean of five numbers.","fragment":"mean of5 numbers","hidden_support":"The source asks for the mean of its five entries."},{"id":"c2","sentence":"Four of the entries are2,4,6 and8; the remaining entry is an unreported real number u.","fragment":"entries2,4,6,8,u","hidden_support":"The withheld source entry is10; all other entries are retained."},{"id":"c3","sentence":"The four reported entries contribute20 to the total sum.","fragment":"known subtotal20","hidden_support":"2+4+6+8=20."}],"withheld":"Only the fifth entry10 is hidden. Using public mean6 and count5 gives total30, hence u=30-20=10. Reconstructed mean is(20+10)/5=6. The public observations omit both the missing entry and the completed mean calculation."}

Example2:
Source: How many binary strings of length6 contain exactly two1s? Answer15.
Output: {"status":"OK","clues":[{"id":"c1","sentence":"The target is the number of binary strings of an unreported integer length n, with n at least2, containing exactly two1s.","fragment":"count length-n binary strings with two1s; integer n>=2","hidden_support":"The source asks this count at length6."},{"id":"c2","sentence":"Choosing the two positions containing1 determines every remaining digit as0.","fragment":"two chosen positions determine string","hidden_support":"Exactly two1s and binary alphabet force the other positions to0."},{"id":"c3","sentence":"Exchanging the names of the two chosen positions does not give a different string.","fragment":"chosen positions form unordered pair","hidden_support":"The two1s are indistinguishable."}],"withheld":"Only n=6 is hidden. Distinct ordered positions number n(n-1); each unordered pair appears twice. The answer15 implies n(n-1)/2=15, so (n-6)(n+5)=0 and n>=2 gives6. Substituting6 gives15. The formula and its inversion appear only here, not in public clues."}

Reject a proposed conversion if it merely rephrases the entire original question, exposes the withheld value via a simple arithmetic encoding, or publishes the complete calculation. Preserve useful information; do not pad a bank with repeated descriptions. An elementary answer-conditioned inverse inference is allowed and must not itself be called leakage.

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION:
{{CHECKED_SOLUTION}}
