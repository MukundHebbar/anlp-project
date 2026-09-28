# Judge development calibration

41/41 saved fixtures satisfy their predefined expected labels/ranges.

| Category | Agreement |
|---|---:|
| ill_posed | 1/1 |
| insufficient | 1/1 |
| minor_omission | 1/1 |
| shortcut | 1/1 |
| tautology | 10/10 |
| unrelated | 1/1 |
| unsupported_grounding | 1/1 |
| valid | 11/11 |
| valid_alternative | 1/1 |
| valid_incomplete_verification | 1/1 |
| violated_clue | 1/1 |
| wrong | 1/1 |
| wrong_answer | 10/10 |

This is development calibration, not held-out accuracy. Thirty cases are three edits of each of ten mathematical families; the other eleven are authored fixtures. Exact answer checks support the constructed arithmetic cases, but do not mechanically certify every judgment about clue grounding or proof sufficiency. Labels are assistant-authored with stated mathematical checks, not independent human review.

Do not use 41 as an independent sample size for a near-perfect-accuracy confidence claim. Repeated related edits, simple controls, and evaluator development limit generalization. Production-output adjudication and fresh independent family validation remain required.

Evidence: [raw judgments](gold-development.json), [fixture manifest](../../../data/manifests/reconstruct-judge-development-v2.json), and `scripts/build_reconstruct_gold.py`. Regenerate this report with `scripts/report_reconstruct_calibration.py`.
