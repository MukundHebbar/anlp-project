#100 completely scored, gate-passed RECONSTRUCT examples

The extension retains47 calibration rows and adds53 previously unevaluated source questions. Prompts, four-clue exposure, model configuration and v4 display thresholds stayed fixed. This is a complete-case dataset, not100 successful reconstructions or an independently certified leak-free benchmark.

Additional sources processed: 162; input dispositions: {'rejected': 71, 'accepted': 65, 'unresolved': 16, None: 10}; fully scored additions: 55; completed overflow: 2. Selection uses frozen source order, not rating or completion speed. All rejected/unresolved attempts remain in extension-attempts.jsonl.

| Cohort | n | Mean /100 | Median | Sample SD | Semantic matches | Provisional grounded |
|---|---:|---:|---:|---:|---:|---:|
| calibration | 47 | 44.41 | 50.00 | 16.03 | 1 | 0 |
| extension | 53 | 44.81 | 50.00 | 20.97 | 1 | 0 |
| combined | 100 | 44.62 | 50.00 | 18.72 | 2 | 0 |

| Rating | Calibration | Added | Combined |
|---|---:|---:|---:|
| 1 | 3 | 6 | 9 |
| 2 | 12 | 11 | 23 |
| 3 | 18 | 14 | 32 |
| 4 | 12 | 19 | 31 |
| 5 | 2 | 3 | 5 |

Recorded incremental cost estimate: $3.48635. Failed calls by stage: {'audit': 27, 'copy': 17, 'convert': 162, 'student': 13, 'judge_validity': 8, 'judge_fidelity': 1}. Missing provider usage is not a reconciled bill.

## Interpretation

The thresholds were calibrated on the original47 scored responses. The added53 were not used to retune them. However, they use a new DeepMath sampling frame and dataset reference solutions instead of the old prior-checked pool; no matched causal performance comparison is claimed. Completion/gating exclusions may be selective. The combined100 is not a held-out test set.

Semantic matching, validity of the supplied answer for the reconstructed question, and the quality of Qwen verification remain distinct. High partial credit is not full recovery. Apparent recoveries require mathematical case review, recorded separately; assistant review is not independent human annotation. Automatic gates and LLM judgments remain fallible.

## Files

- [100 question/answer CSV](questions-answers.csv)
- [Readable questions and Qwen answers](questions-answers.md)
- [Full selected JSONL](questions-answers.jsonl)
- [Public inputs only](public-tasks.jsonl)
- [All extension attempts](extension-attempts.jsonl)
- [Frozen manifest and source provenance](manifest.json)
- [Raw model calls and failures](run.json)
- [Verification](verification.json)
- [Manual case review](manual-review.json)
- [Complete bundle](reconstruct-valid100.zip)

## Transport recovery

The first phase stopped after a connection-failure burst. Successful outputs were reused unchanged. Transport-only retries were limited to two total attempts per stage; a circuit breaker pauses after three consecutive transport failures. Historical transport failures: 182. Unique sources with actual calls across both phases: 178. Returned provider usage estimate across phases: $1.01448; conservative cost including unknown reservations: $3.48635. The original phase and all failed attempts are preserved.

The conservative project self-limit was amended to$7.50; it was not a user-specified cap. This recovery is a documented protocol amendment, not a no-retry run.
