# Inverse-construction demonstration: amendment P

Same ordered evidence and sampling; only the example package changes. Two seeds per family are repeated measurements. Missing outputs remain in the planned denominator. These are development results, not the 25-family confirmation.

| Prompt | Scored / planned | Mean on resolved /100 | Grounded | Same original | Grounded semantic (provisional) |
|---|---:|---:|---:|---:|---:|
| student_p10_recover_original | 8/8 | 28.125 | 1 | 0 | 0 |
| student_p11_inverse_example | 7/8 | 32.142857142857146 | 0 | 0 | 0 |

Paired comparisons and missingness bounds:

```json
{
  "student_p11_inverse_example@convert_p3": {
    "versus": "student_p10_recover_original@convert_p3",
    "source_averaged": {
      "sources": 3,
      "mean_difference": -0.16666666666666666,
      "source_bootstrap_95_interval": [
        -0.5,
        0
      ]
    },
    "normalized_score_source_averaged": {
      "sources": 3,
      "mean_difference": 0,
      "source_bootstrap_95_interval": [
        0,
        0
      ]
    },
    "first_seed": {
      "paired_sources": 4,
      "wins": 0,
      "losses": 1,
      "exact_mcnemar_two_sided": 1.0
    }
  }
}
```

Any provisional success still requires independent mathematical, semantic, and disclosure review before counting toward release. A mean in range alone cannot establish usefulness. Full conversion coverage is a separate unmet gate.

Evidence: [raw responses, failures and judgments](prompt-diagnostic.json), [case-level analysis](inverse-example-analysis.json), [preregistration](../../../docs/plans/reconstruct-amendment-p.md).
