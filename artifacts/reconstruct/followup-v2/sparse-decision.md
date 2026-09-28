# Sparse evidence +/- answer role: completed development comparison

The two-observation condition passes disclosure audit on12/12 sources; adding the existing role cue passes on11/12. Source40 violates the no-number role rule. Both student conditions use exactly the same eleven common sources and two decoding seeds, fixed before inference. All44 responses now have judgments. Four technical judge failures were retried once without changing prompts or student outputs; original failures remain saved.

| Outcome | Two observations | Same observations plus role |
|---|---:|---:|
| Mean /100 | 29.55 | 26.14 |
| Source-bootstrap 95% interval | [25, 37.5] | [25, 28.40909090909091] |
| Grounded successes | 1/22 | 0/22 |
| Score bins0,1,2,3,4 | [0, 20, 1, 0, 1] | [0, 21, 1, 0, 0] |

Paired role-minus-no-role difference: -3.41/100, with interval [-11.363636363636363, 2.272727272727273]. There is no demonstrated benefit from adding the role cue. Do not promote that added complexity. The sparse no-role condition has one substantive success, independently checked in the [factorial case study](sparse-factorial-case-study.md), but this single family and seed do not establish a robust optimal clue count.

Both means meet the requested difficulty band, yet most responses remain mathematically wrong. Task validity, distribution, and meaningful reconstructions remain separate from the mean. Sparse versus historical full-bank results are not a clean count-only contrast: the sparse composition reshuffles its selected base observations, and audit eligibility differs. A fresh nested-count study must preserve ordering and common source eligibility.

Evidence: [analysis](sparse-comparison.json), [eligibility fixed before inference](sparse-eligibility.json), [raw run](sparse-role-study.json), [smoke checks](sparse-smoke-review.json). Adaptive D2 development only. No C outcomes were used.
