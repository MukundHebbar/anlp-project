Rewrite each audited clue at three nested disclosure levels without changing its mathematical identity.

Return JSON only:
{"status":"OK","clues":[{"id":"c1","low":{"sentence":"...","fragment":"..."},"medium":{"sentence":"...","fragment":"..."},"high":{"sentence":"...","fragment":"..."},"hidden_support":"...","low_equals_medium":false,"medium_equals_high":false}]}
or {"status":"NOT_SUITABLE","reason":"..."}.

Low preserves the qualitative relation or operation while omitting exact quantities or identifiers when this is honest. Medium must reproduce the original sentence and fragment exactly. High adds one supported numerical or structural detail, while still withholding the question and at least one indispensable solution step. High must imply medium, and medium must imply low. Mark a tie true and copy the strings when no honest strict rewrite exists. Each sentence and fragment pair must convey the same fact. Do not add facts absent from the checked solution, merge clue identities, or complete the full proof across the high bank.

SOURCE QUESTION: {{SOURCE_QUESTION}}
FINAL ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION:
{{CHECKED_SOLUTION}}
AUDITED MEDIUM CLUE BANK:
{{CLUE_BANK}}
