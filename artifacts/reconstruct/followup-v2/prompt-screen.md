# Matched prompt screen: completed development result

Twelve D2 sources, two decoding seeds per source, identical full-bank sentence evidence, local non-thinking Qwen3-4B Q4_K_M, fixed evaluate_p2. All 96 outputs have judgments. One malformed JSON output was recovered from saved raw text without new generation.

Subsequent validity review rejected source131 for exposing essentially the full solution. Both baseline successes came from that source. Preserve this historical comparison, but consult [the validity sensitivity analysis](baseline-validity-sensitivity.md) before making a task-quality claim.

| Arm | Mean /100 | Source-bootstrap 95% interval | Grounded successes | Mean completion tokens |
|---|---:|---|---:|---:|
| Compact one-shot baseline | 31.25 | [25.00, 42.71] | 2/24 | 198.4 |
| Verification-first field order | 32.29 | [25.00, 40.62] | 2/24 | 215.0 |
| Order plus explicit consistency instruction | 29.17 | [22.92, 36.46] | 1/24 | 256.2 |
| Two inverse-construction examples | 27.08 | [16.67, 38.54] | 2/24 | 201.4 |

Two samples of one source are not independent sources; intervals resample 12 source means. All four development means satisfy the requested 20–75 band. This does not make all four useful or equally good.

| Candidate versus baseline | Paired mean difference /100 | Source-bootstrap 95% interval |
|---|---:|---|
| Verification-first field order | +1.04 | [-6.25, 8.33] |
| Order plus explicit consistency instruction | -2.08 | [-10.42, 5.21] |
| Two inverse-construction examples | -4.17 | [-11.46, 3.12] |

## Decision

Retain student_p1 as the provisional single-call incumbent. None of the three prompt-only changes demonstrates a reliable gain. This is a simplicity decision under uncertainty, not proof that student_p1 is superior or that the alternatives are equivalent. The intervals remain wide and the same sources motivated some adaptations. Fresh confirmation is still required.

The supplied answer is often ignored even after the response derives a conflicting result. For source 30, the baseline asks for Log'(1), derives 1, and fails to match the supplied answer 2. For source 95, it computes a parameter-dependent integral but omits the limiting operation needed for the supplied zero. These cases motivate testing additional orientation and explicit self-revision, but do not establish that those interventions work.

## Reproducibility and limits

- Analysis: [prompt-comparison.json](prompt-comparison.json). Raw records: [run.json](run.json). Full case export: [cases.md](cases.md).
- Regenerate with `scripts/analyze_reconstruct_followup.py --run artifacts/reconstruct/followup-v2/run.json --output artifacts/reconstruct/followup-v2/prompt-comparison.json --arms student_p1 student_p5 student_p6 student_p7`, then this report script.
- Runtime defaults: [server-props.json](server-props.json), [runtime-notes.json](runtime-notes.json). Requests omit min-p and inherit approximately 0.05. Do not pool with historical vLLM results.
- Labels are DeepSeek evaluate_p2 judgments. Independent gold calibration and mathematical adjudication are separate, incomplete validation steps; no near-perfect accuracy claim follows from this table.
- C is untouched. No training-transfer result has been measured.
- Bootstrap intervals are descriptive development estimates; adaptive search and small source count limit inference. No global optimality or exact equivalence is claimed.
