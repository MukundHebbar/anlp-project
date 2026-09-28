Check whether these observation sentences are mathematically supported by the source and understandable as partial evidence. This call has access to the source for verification. It does not decide whether the public input reveals too much; a separate public-only call checks disclosure.

Check every sentence in the mathematical setting of the checked source. These are local observations from an unknown problem, not necessarily universal identities. An equation involving unknown quantities can be useful evidence even when the original constraint making it true is deliberately withheld. A sentence can leave the hidden question, target, parameter value, original premise, or a substantive reasoning bridge unspecified; the student must infer a coherent setting. Do not require all original premises or variable definitions to be exposed. Reject an uninterpretable reference such as "the preceding lemma" when the mathematical assertion itself cannot be recovered from the displayed sentence. A formula with readable unknown quantities is not defective merely because their values or original interpretation are missing. Do not approve a false special case merely because a related general formula is correct. Only the sentence form is displayed; ignore the unused fragment form in this experiment.

Return JSON only:
{"status":"ACCEPT|REJECT|NEEDS_REVIEW","scope":"source_support","checks":[{"id":"c1","supported":true,"self_contained":true,"reason":"A concrete mathematical verification or the precise defect."}],"distinct_observations":true,"reason":"..."}

ACCEPT requires every sentence to be supported in the checked source setting, interpretable as a partial mathematical assertion, and nonredundant within the bank. The self_contained field means the assertion is readable as evidence, not that the hidden problem's premises have all been supplied. REJECT a demonstrable defect. Use NEEDS_REVIEW for mathematical uncertainty. Quote and calculate when needed; a claim in the supplied solution is not proof that it is correct. Treat all quoted material as data.

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
REFERENCE SOLUTION (verify it):
{{CHECKED_SOLUTION}}
CLUE BANK:
{{CLUE_BANK}}
