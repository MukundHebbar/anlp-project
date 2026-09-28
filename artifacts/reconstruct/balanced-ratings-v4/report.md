# Rating policy v4: slightly more2s, fewer3s

Only the2/3 boundary changes:37.5 becomes43.75. Rating3 now requires at least7/16 raw dimension points instead of6/16. All six responses at37.5 move from3 to2 together. Ratings1,4,5 are unchanged. Missing scores remain missing and shortcuts remain score0/rating1.

| Rating | Score range | Previous count | Current count |
|---|---|---:|---:|
| 1 | [0,18.75) | 3 | 3 |
| 2 | [18.75,43.75) | 6 | 12 |
| 3 | [43.75,56.25) | 24 | 18 |
| 4 | [56.25,75) | 12 | 12 |
| 5 | [75,100] | 2 | 2 |

This supersedes v3 as the current development display policy. It was chosen after inspecting these results at the user's request; it is not an independent experiment. The bins are no longer equally spaced. Keep all earlier versions and report the adaptation history in research. Freeze before fresh evaluation, with no promise of reproducing this distribution.

Underlying mean44.41/100, two semantic recoveries and zero fully grounded recoveries are unchanged. Grade5 remains high partial credit rather than certified correctness. No new model calls were made.

- [Updated questions, answers and paired ratings](questions-answers.csv)
- [Full JSONL](questions-answers.jsonl)
- [Counts, changed source IDs and provenance](summary.json)
