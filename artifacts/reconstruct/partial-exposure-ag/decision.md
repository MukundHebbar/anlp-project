# Richer versus partial clue exposure: AF/AG development results

The requested20–40% correct reconstruction rate is not achieved. Equivalent mathematical representations are explicitly accepted by source_recovery_p2; none of these new outputs preserves the original essential problem. All results are on reused development families, not held-out confirmation.

| Policy | Fixed source families | Eligible inputs | Scheduled Qwen draws | Parsed/scored | Mean score on scored /100 | Semantic recoveries | Grounded semantic recoveries |
|---|---:|---:|---:|---:|---:|---:|---:|
| AF:3–6 distinct observations |12|1|1|1|25|0/1|0/1|
| AG: exact first3 observations |12|5|5|4|18.75|0/5|0/5|

A failed/unparseable scheduled draw counts as unsuccessful reconstruction, but no rubric score is invented for it. AG's planned-draw mean is bounded by15–35 depending on its missing score. These small adaptive samples do not establish a population rate or statistically rule out20–40%; they provide no observed support for meeting that target. Both end-to-end recovery yields are0/12.

The same Qwen3-4B Q4_K_M, explicit non-thinking setting, p13 few-shot prompt, seed0, temperature0.7/top_p0.8/top_k20 and8192 output cap were retained. Prefixes preserve exact sentences and were independently audited before student generation. All twelve families remain in conversion accounting. The private bank's rejection does not automatically disqualify a safe displayed subset.

## What happened

- AF129: invented word length10; exact recurrence gives remainder1584, not1392. Original length12 gives1392.
- AG0: invented an impossible integral condition for every polynomial; f=0 is an immediate counterexample.
- AG13: reached8192 output tokens with repeated attempts and invalid JSON. Its initial candidate uses3! and computes5, conflicting with supplied answer1. No replacement sample was taken.
- AG96: left the derivative parameter a unspecified. The correct limit is a/12, so the required a=1 premise was not recovered; its integration was also incorrect.
- AG129: changed length12/remainder-modulo2008 into a six-digit count. Independent exhaustive enumeration and dynamic programming give136 words, or126 numbers without leading zero, not1392.
- AG137: invented n=9 and changed the target to an unknown degree; its own calculation gives7 instead of supplied answer6. Moreover three degree7 vertices among nine force a K3,3 subgraph, contradicting planarity. The primary judge incorrectly called this candidate well-posed; the exact certificate is retained.

## What can and cannot be concluded

Adding observations did not yield a correct recovery in the richer arm. Only source129 is eligible in both arms; both responses fail and both receive25/100. There is no adequately sized paired comparison from which to infer a causal benefit or harm of clue count. Count and informational content change together, and audit failures differ.

AG had six first-pass audit failures: support transports63/80; public no-visible87, transport120, malformed reason118; source no-visible46. Source62 was rejected; the remaining five passed all gates and frozen manual review. Failures were preserved, not converted into negative semantic labels or repeatedly retried until acceptance. AF includes its documented bounded technical retry and exact schema normalization, so raw service-completion rates are not directly comparable.

The observed issue is failure to infer and verify a missing essential parameter or target. Merely hitting a mean-score band is insufficient: AF scores25 while recovering zero questions. Converter coverage, semantic recovery, mathematical grounding, direct disclosure, and technical missingness must remain separate metrics.

Do not promote either policy or claim it is the best version. The next useful experiment must first ensure that the supplied clues permit a short, verifiable inverse inference while withholding at least one essential original condition. Prefix truncation can remove the very constraint needed for that inference. Use a globally specified conversion rule, source-disjoint few-shot examples, prospective selection, and independent checks; do not repair individual clues after observing Qwen failures. Only a viable development policy should advance to the untouched25-family confirmation set.

## Inspectable evidence

- [AG metrics](comparison.json), [AF decision](../distinct-information-af/decision.md), [AF metrics](../distinct-information-af/comparison.json).
- [Exact AG responses and raw judgments](student.json), [frozen requests](student-requests.json), [input reviews](input-review.json), [all converter/auditor results](run.json).
- [Manual response review](response-math-review.json), [analytic certificates](analytic-checks.json), [executable count checks](reproduce-count-checks.py).
- [AF protocol](../../../docs/plans/reconstruct-amendment-af.md), [AG protocol](../../../docs/plans/reconstruct-amendment-ag.md). [Independent AG mathematical verification](math-verification.json) is terminal: three invalid verdicts and one no-visible-output failure (source137). The latter remains missing; the analytic graph certificate is separate evidence, not an invented teacher label.

Human reference labeling and independent held-out confirmation are still absent. No near-perfect DeepSeek accuracy claim is supported.

Validation: 65 reconstruction regression tests passed; exact count checks and report links passed. No paid experiment remains running. The research objective remains unmet, and neither policy is promoted.
