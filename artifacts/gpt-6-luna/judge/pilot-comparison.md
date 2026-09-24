# GPT-Luna Judge prompt smoke test

These are exploratory GPT-Luna agent generations and independent agent reviews. The review is not a human audit, and four sources are too few to establish a prompt quality rate.

| Candidate | Reviewed/generated | Label match | First-error match | Prior steps valid | Method preserved |
| --- | ---: | ---: | ---: | ---: | ---: |
| `pilot-v1_rubric-4sources` | 8/8 | 8 | 8 | 8 | 8 |
| `pilot-v2_examples-4sources` | 8/8 | 8 | 8 | 8 | 8 |
| `pilot-v3_mutate-4sources` | 8/8 | 8 | 8 | 7 | 8 |
| `pilot-v4_self_check-4sources` | 7/7 | 7 | 7 | 7 | 7 |

## Disagreements

- None in completed reviews.

Human review, the full 60-source comparison, and Qwen3-8B confirmation remain required before freezing a generator.
