# Richer-clue reconstruction: completed development screen

Do not declare the grounded target or final task validated. Richer evidence alone did not improve recovery. The inverse-example prompt improved semantic recovery on one of three selected development tasks, but its verification was wrong and the evaluator over-scored it.

Fifteen local Qwen draws were scheduled across AA, AB and AC; fourteen parsed and one sparse3 draw hit the8192-token cap and failed parsing. The same Qwen3-4B Q4_K_M checkpoint, explicit nonthinking mode, seed0, temperature0.7, top_p0.8 and top_k20 were held fixed.

## Results

| Condition | DeepSeek mean /100 | Semantically equivalent question /3 | Verified grounded recovery /3 |
|---|---:|---:|---:|
| AA: sparse3 | 12.50 (2/3 scored) | 0/3 | 0/3 |
| AA: rich6 | 0.00 | 0/3 | 0/3 |
| AA: dense3 | 0.00 | 0/3 | 0/3 |
| AB: rich6 + inverse example | 41.67 | 1/3 | 0/3 |
| AC: rich6 + premises first | 16.67 | 1/3 | 0/3 |

Equivalent formulations count as correct for backtracing. AB and AC each reach1/3=33.3% semantic recovery on these three development inputs, inside the requested20–40% range. This is not a validated population rate: the approximate95% Wilson interval for1/3 is6.1–79.2%, and these are adaptively reused tasks. Grounded recovery remains0/3. Across all12 allocated sources, semantic recovery is1/12=8.3% for each follow-up; grounded recovery is0/12. The required5/25 confirmation has not been run or satisfied.

## What changed and what the comparison establishes

AA generated six supported observations, retained useful target/context information, and withheld an essential question premise. sparse3 uses the first three; rich6 uses all six; dense3 groups adjacent pairs into three entries without changing a word or proposition order. Thus rich6 versus dense3 tests grouping at equal information, while sparse3 versus rich6 changes both information and displayed count. None recovered the source. This is evidence against promoting this particular richer-clue policy with the incumbent prompt, not evidence that more information can never help.

AB kept the exact rich6 evidence and replaced the student instruction/example package with a short demonstration of answer-conditioned missing-premise inference. AC additionally emphasized retaining the original target and emitting inferred premises before the question. Both recovered the same Laurent-series question. AC offered no semantic improvement over the simpler AB on this screen; neither is ready for release.

## Why raw scores would give the wrong conclusion

AB source62 asks for the correct original Laurent expansion around pi, so its question is a semantic success. Its explanation wrongly calls sin(z)/(z-pi)^2 a double pole. Writing w=z-pi gives sin(pi+w)=-w+O(w^3), hence the quotient is -1/w+O(w), a simple pole. Its nearest-singularity-distance argument is also inconsistent. DeepSeek nevertheless awarded4/4. The41.67/100 average and33.3% raw joint success would meet the numerical targets while hiding a grounding error. AC additionally calls the singularity essential, also false. Raw judgments are preserved; manual mathematical findings are not silently substituted into raw scores.

Other failures are concrete: the target-order question omits column heights ([3,3,2] gives560 but[6,1,1] gives56); the digit-word question omits length12, or substitutes length6 whose actual count is136. Summing all lengths1..19 gives1115 modulo2008, not1392. The alternative prompt once asked for the missing heights given560, changing the requested target instead of reconstructing the original count question.

## Conversion and leakage accounting

All12 preallocated D4 source families remained in the denominator. Conversion returned8 six-clue banks,2 NOT_SUITABLE and2 no-visible-output failures. The three accepted families were46,62,129. Both disclosure audits, support review, source-blind copy challenge and assistant review were required before local calls. Audit uncertainty/disagreement was not overridden to improve student results. No held-out sources were opened.

The stricter audits have real errors. The public auditor rejected96 despite withholding derivative gprime(0)=1, which is inferred from limit=a/12; it also rejected137 despite withholding the precise degree triple. A saved12-vertex sphere-triangulation certificate satisfies the latter public constraints with degrees4,5,6, proving those constraints do not already specify the original degrees3,4,5. The source-aware auditor accepted118 despite an almost complete witness/verification being visible; the public auditor caught it. Against pre-student assistant references, public/source disclosure agreement was6/8 and7/8 respectively, not independent gold accuracy.

## Next decision

Keep AB as a provisional concise prompt candidate for further development, not a final best version. Before a larger confirmation, calibrate the grounding judge on correct-question/incorrect-verification controls and resolve disclosure false positives using independent mathematical checks. Improve conversion coverage prospectively; do not select only the families whose Qwen outputs happen to succeed. Then compare a small preregistered set of information levels on a broader frozen development cohort and use the untouched25-family confirmation only after selection. No more prompt variants are added to this three-family screen.

## Inspectable evidence

- [AA protocol](../../../docs/plans/reconstruct-amendment-aa.md), [AB protocol](../../../docs/plans/reconstruct-amendment-ab.md), [AC protocol](../../../docs/plans/reconstruct-amendment-ac.md).
- [All conversion/audit/copy outputs](run.json), [exact local requests](student-requests.json), [AA local responses and judge outputs](student.json), [AA mathematical review](response-math-review.json).
- [AB responses/judgments](../missing-premise-ab/student.json), [AB mathematical review](../missing-premise-ab/response-math-review.json), [AC responses/judgments](../premises-first-ac/student.json), [AC mathematical review](../premises-first-ac/response-math-review.json).
- [Exact inverse checks](analytic-checks.json), [graph alternative certificate](source137-alternative-certificate.json), [audit disagreements](audit-disagreements.json), [combined machine-readable results](screen-summary.json).
- [Live runtime provenance](local-runtime-provenance.json), [63 passing reconstruction tests](tests.log).

Limitations: one seed, three surviving development families, adaptive prompt selection, poor conversion coverage, fallible teacher and assistant reviewers. These findings support specific failure diagnoses and future experimental choices; they do not establish a globally best task or near-perfect DeepSeek judging.
