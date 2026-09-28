# Production-derived evaluator boundary checks

Four adaptive development fixtures from two source families; unchanged evaluate_p2. This is a diagnostic extension, not held-out accuracy validation.

| Fixture | Score | Expected score | Agreement |
|---|---:|---|---|
| production_divisor_wording_clarified | 4 | [4] | True |
| production_logistic_sign_change_valid | 4 | [4] | True |
| production_logistic_no_sign_change | 1 | [1] | True |

Three fixtures resolve and match their references. The original divisor wording produces no visible output on both allowed attempts. Its existing information-control score1 is preserved; this follow-up does not adjudicate that linguistic disagreement. The explicitly stated three-divisor question receives4, the false logistic sign-change construction receives1, and its valid counterpart receives4.

Do not quote3/3 as overall100% accuracy: one of four attempted fixtures remains unresolved, the pairs are correlated, and the original wording has an interpretation-dependent reference. The failed logistic request timed out once and succeeded on its single technical retry. No further retries of the original wording are authorized by this round.

A runtime fix now preserves usage and finish reason when a future provider response has no visible content; historical missing metadata cannot be recovered. The old empty responses therefore do not prove that their token cap, rather than another provider condition, caused failure.

Evidence: [raw records and failures](gold-production-development.json), [reference fixtures](../../../data/manifests/reconstruct-judge-production-development-v3.json), [original control judgments](information-controls.json).
