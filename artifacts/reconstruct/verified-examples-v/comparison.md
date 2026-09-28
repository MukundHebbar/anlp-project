# V: verified demonstrations versus the incumbent prompt

Independent mathematical review: no confirmed original recoveries for either arm. The candidate has one primary valid alternative, replicated at seed1; it changes the source target. This is not the required semantic recovery.

| Prompt | Scored / planned | Raw mean /100 | Primary checked original recoveries /8 | Primary checked valid reconstructions /8 | Mean completion tokens |
|---|---:|---:|---:|---:|---:|
| student_p10_recover_original | 16/16 | 18.75 | 0 | 0 | 206.1 |
| student_p12_verified_examples | 14/16 | 28.57 | 0 | 1 | 268.6 |

End-to-end primary original recovery is0/12 allocated families for both arms. Reviewed input coverage is8/12, below the80% release threshold.
Paired score difference (candidate minus incumbent): 10.714285714285714;95% source-bootstrap interval: [-10.714285714285714, 42.857142857142854]; complete paired families: 7.
Semantic judgments: 32/32 returned, 32 resolved. Mathematical references: response-math-review.json.

Decision: no independently verified original-recovery improvement; do not promote the demonstration package.

Limitations:
- Eight accepted development families, selected by input validity rather than student success; four exclusions remain in end-to-end denominator.
- Two draws are repeated measurements within a source, not independent source families.
- Package changes demonstration count, content and input tokens together.
- p3 remains provisional; assistant analytic references are not independent human gold.
- Incomplete teacher judgments remain explicit; complete-source intervals exclude unresolved families and are not final if judgments remain pending.
