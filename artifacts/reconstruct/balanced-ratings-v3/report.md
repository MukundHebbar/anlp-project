# Balanced rating policy v3

This supersedes the generous v2 display policy. It is a development-calibrated scale, selected after inspecting the same47 resolved scores, not a new model experiment or independently validated rubric.

| Rating | Score range | Dimension sum, when fully scored | Original count | v2 count | v3 count |
|---|---|---|---:|---:|---:|
| 1 | [0,18.75) | 0–2 | 4 | 4 | 3 |
| 2 | [18.75,37.5) | 3–5 | 11 | 11 | 6 |
| 3 | [37.5,56.25) | 6–8 | 29 | 7 | 24 |
| 4 | [56.25,75) | 9–11 | 3 | 23 | 12 |
| 5 | [75,100] | 12–16 | 0 | 2 | 2 |

The four cutoffs are equally spaced by18.75 score points (three raw dimension points). Rating3 captures moderate partial reconstruction;4 requires at least9/16 raw points;5 requires12/16. Scores are bounded, so the uppermost band includes the ceiling. A known shortcut remains score0/rating1 regardless of its raw dimensions.

Selection rationale: v2 put too many moderate50-point responses in4. This policy puts50 in3,56.25 in4, and75 in5, using one global set of fixed thresholds. This calibration was informed by the current outcomes and must be described that way in a paper. It is not evidence of better model performance.

Freeze these cutoffs for subsequent evaluation. Do not keep shifting them to preserve a desired histogram; report any future skew. Do not use ranks, quotas, item replacement or modified mathematical judgments to manufacture a Gaussian distribution. The current histogram is middle-peaked with sparse tails, not exactly symmetric or a demonstrated normal distribution.

Numerical mean44.41/100, semantic recoveries2, and fully grounded recoveries0 remain unchanged. Grade5 remains high partial credit, not certified correctness. The original outputs, missingness and gate exclusions remain intact.

- [Questions, answers and all three rating versions](questions-answers.csv)
- [Annotated JSONL](questions-answers.jsonl)
- [Policy provenance and counts](summary.json)
