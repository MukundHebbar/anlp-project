# AH/AJ: one-premise reconstruction and output-order comparison

Neither version meets the requested correctness target. The three eligible families were0,46,96; all public evidence was exactly matched across the two conditions and frozen before either generated an answer.

| Condition | Scheduled | Readable | Valid rubric scores | Mean on scored /100 | Semantic recovery | Grounded semantic recovery |
|---|---:|---:|---:|---:|---:|---:|
| AH: question first, p13 |3|3|2|0|0/3|0/3|
| AJ: verification first, same decoded example values |3|2|2|0|0/3|0/3|

AH's source0 rubric response violated its schema (needs_review with a numeric score); retain it as a missing score. AJ source46 reached8192 tokens without a readable final response; retain it as a scheduled failure. Both planned-score means have bounds0–33.33, not a fabricated zero for the missing score. Raw semantic judges returned related-problem scores rather than full equivalence for all five readable responses. Independent mathematics checks rejected all five readable responses. Manual reviews agree. All12-source end-to-end grounded yield is0/12 for both policies; this is not a population estimate with meaningful precision.

The common failure was leaving the hidden parameter in the question instead of recovering and stating its original value. For the polynomial, k must be3; for the columns, the arrangement must be3,3,2; for the nested integral, the derivative must be1. The output-order change did not repair these errors and introduced one cap-hit failure. It changes generation order, not the available mathematical information.

## Conversion and eligibility

Twelve fixed D4 families: eleven converter outputs, one no-visible-output failure129. Three outputs were NOT_SUITABLE (13,63,120); eight were OK. All eight support audits accepted, but analytic review found a Laurent-annulus ambiguity/error in62, retained in support-disagreement-62.json. Public disclosure rejected87;118 returned a malformed REJECT without a reason. Source disclosure returned five acceptances and a quote-validation failure62. All five copy checks returned no_direct_reconstruction. Frozen manual review additionally excluded80/137 for near-complete-method uncertainty, leaving0/46/96 eligible.

The exclusions of80/137 are conservative operational decisions, not established direct-question leaks. Both passed all automated checks; their review disagreement must remain visible. Source118's private certificate also omitted the negative triangular index, although the missing-denominator conclusion can be independently justified. The converter and judges are not established as near-perfect.

## Interpretation and next decision

AH/AJ reused a heavily developed cohort and do not establish generalization or an optimal task version. The matched direct SOLVE control got4/12 answers correct and3/12 strictly verified explanations. This shows underlying mathematical weaknesses, alongside extra reconstruction failures on some forward-solvable questions; it is not a hard reconstruction ceiling or a training-transfer result.

Do not promote either version. Retain p13 as the simpler incumbent for the prospective fresh-cohort test: neither ordering produced a recovery, while p13 returned all three responses. Stop further wording changes on D4 in this development cycle. The new contingency cohort was selected by its existing allocation, without inspecting historical SOLVE outcomes, and excludes reserved C25/R data.

Evidence: [AH metrics](comparison.json), [AJ metrics](../output-order-aj/comparison.json), [AH exact requests/outputs](student.json), [AJ exact requests/outputs](../output-order-aj/student.json), [AH analytic review](response-math-review.json), [AJ analytic review](../output-order-aj/response-math-review.json), [AH independent math checks](math-verification.json), [AJ independent math checks](../output-order-aj/math-verification.json), [prompt equivalence check](../output-order-aj/prompt-equivalence-check.json), [converter/auditor records](run.json), [input decisions](input-review.json), [certificate checks](certificate-checks.json), [support disagreement](support-disagreement-62.json), [matched SOLVE report](../matched-solve-ai/decision.md).

No confirmation set was opened, no failed response was replaced, and no reconstructed question was marked correct merely because its answer matched. Equivalent mathematical formulations remain accepted. These are development findings, not proof of a best version.
