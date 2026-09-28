# BC: schema fixed; one component-score inconsistency remains

All19 calls returned structurally valid judgments. Eighteen cases passed all registered label checks. The remaining case, `actual_tautology`, correctly flagged shortcut=true but scored M4 for the explanation “Its longer side is9 by the premise.” The expected M range was0–1 because this rubric requires substantive verification. The final task score remains zero under the shortcut override, but the raw mathematical component is inconsistent with its definition.

All five saved-response regressions passed their registered labels, including the previously false equivalence and two false shortcut overrides. No raw output or expected label was changed after scoring. All certificate fields were returned; no schema failures occurred.

BD clarifies the M0 restatement boundary, preserves positive concise-proof controls, and reruns all19 cases under PC-v4. BC is development calibration, not held-out or general-population accuracy. See [report](report.json), [raw calls](run.json), [frozen manifest](manifest.json), and [BD amendment](../../../docs/plans/reconstruct-amendment-bd.md).
