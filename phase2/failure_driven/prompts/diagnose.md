You are checking a student's failed attempt at a mathematics problem. You are given the problem, its correct final answer, a trusted correct solution, and the student's attempt, which reached a wrong final answer.

Find the FIRST place where the attempt goes wrong mathematically: a false claim, a wrong calculation, a misapplied rule, a dropped or misread condition, or a wrong choice of what to compute. Ignore presentation, wording and verbosity. Compare against the trusted solution, but credit a different valid route if the student took one.

Rules:
- `first_wrong_quote` must be copied character for character from the student's attempt: one sentence, equation or short passage (at most 300 characters) that contains the first mathematical error. Do not paraphrase or correct it.
- `mistake` says what is wrong there, in one or two sentences, with the specific values or expressions involved.
- `correct_version` says what that step should be instead.
- `misconception` states the general rule, condition or idea the student mishandled, in one sentence, without referring to this problem's specific numbers (for example "applies d(ab) = d(a)d(b) without checking that a and b are coprime").
- `error_type` is a short snake_case label (for example sign_error, dropped_condition, wrong_formula, misread_target, arithmetic_error).
- Use status "uncertain" if you cannot point to one place: for example the attempt is mostly unrelated to the problem, gives no derivation, or the error cannot be located with confidence. Then the other fields may be empty strings.

Return JSON only:
{"status":"diagnosed","first_wrong_quote":"...","mistake":"...","correct_version":"...","misconception":"...","error_type":"..."}
or {"status":"uncertain","first_wrong_quote":"","mistake":"","correct_version":"","misconception":"","error_type":"","reason":"..."}

PROBLEM:
{{PROBLEM}}

CORRECT FINAL ANSWER: {{CORRECT_ANSWER}}

TRUSTED SOLUTION:
{{TRUSTED_SOLUTION}}

STUDENT'S FINAL ANSWER: {{STUDENT_ANSWER}}

STUDENT'S ATTEMPT:
{{STUDENT_ATTEMPT}}
