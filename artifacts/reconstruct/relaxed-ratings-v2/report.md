# More generous ratings: v2

Same frozen responses and quality scores; only the display thresholds change. This is an explicitly post-hoc policy choice, not a new model experiment.

| Rating | Old score range | New score range | Old count | New count |
|---|---|---|---:|---:|
| 1 | [0,20) | [0,20) | 4 | 4 |
| 2 | [20,40) | [20,40) | 11 | 11 |
| 3 | [40,60) | [40,50) | 29 | 7 |
| 4 | [60,80) | [50,70) | 3 | 23 |
| 5 | [80,100] | [70,100] | 0 | 2 |

Scored responses: 47; changed labels: 24; new model calls: 0.

A4 now denotes substantial partial reconstruction; a5 denotes strong aggregate reconstruction quality. Neither certifies semantic equivalence, a correct supplied answer, or a sufficient proof. Retain the source-equivalence and grounded-success flags alongside the rating. Missing scores remain missing, and known shortcuts remain score0/rating1.

The underlying mean remains44.41/100. The two reviewed semantic matches and zero fully grounded successes are unchanged. The new histogram is an observed consequence of this policy; no Gaussian or middle-mode guarantee is made.

- [Questions, answers and both ratings](questions-answers.csv)
- [Full annotated JSONL](questions-answers.jsonl)
- [Summary and input hash](summary.json)
