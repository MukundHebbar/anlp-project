# Judge generator prompt comparison

This report contains structural generation metrics only. Mathematical validity, first-error correctness, and method preservation require a blinded human audit.

| Candidate | Items | Completed | Valid schema | Correct targets | Incorrect targets | Prompt mean tokens | Completion mean tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `judge_generator_v1_rubric-dev-60` | 120 | 0 | 0 | 60 | 60 | - | - |
| `judge_generator_v2_examples-dev-60` | 120 | 0 | 0 | 60 | 60 | - | - |
| `judge_generator_v3_mutate-dev-60` | 120 | 0 | 0 | 60 | 60 | - | - |
| `judge_generator_v4_self_check-dev-60` | 120 | 0 | 0 | 60 | 60 | - | - |

## Audit requirements

- Confirm every correct proposal is mathematically valid.
- Confirm every incorrect proposal has the requested first error and that all earlier steps are valid.
- Confirm method preservation, error comprehensibility, and absence of label/length shortcuts.
- Record disagreements and adjudications separately from raw generation artifacts.
