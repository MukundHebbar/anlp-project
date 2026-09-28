# Original-recovery instruction: four-family diagnostic

Same fixed p3 evidence, local non-thinking Qwen3-4B Q4_K_M, seeds0/1, and8192 cap. Only the instruction paragraph differs; the example and schema are identical. These16 outputs are eight per prompt, not16 independent source families.

| Prompt | Judged | Mean /100 | Grounded rubric successes | Same source questions | Grounded semantic successes |
|---|---:|---:|---:|---:|---:|
| student_p1 | 8/8 | 31.25 | 0/8 | 0/8 | 0/8 |
| student_p10_recover_original | 8/8 | 28.12 | 1/8 | 0/8 | 0/8 |

Paired normalized-score comparison: `{"sources": 4, "mean_difference": -3.125, "source_bootstrap_95_interval": [-9.375, 0]}`. The bootstrap resamples source means; four families give limited precision.

The new instruction does not produce original recovery on this set. Any generic grounded success must not be counted toward the5/25 requirement when its question differs from the source. A numerical mean inside20–75 is insufficient.

Common failures: treating observed denominators as numerators; asking for a radical sum whose value is not60; turning continuity observations into a different theorem question; and specifying an invalid shift boundary or leaving the cubic/area target underdetermined. Preserve all outputs and source-recovery categories, including related-but-not-equivalent questions.

Decision: no support for promoting the wording change as a recovery improvement. A subsequent hypothesis should distinguish teaching inverse construction with a worked example from merely requesting original recovery. It must be registered before new draws. Full conversion coverage remains a separate failed gate.

Evidence: [raw responses and both judgments](prompt-diagnostic.json), [paired analysis and every case](prompt-alignment-analysis.json), [fixed inputs](prompt-diagnostic-inputs.json), [input review](prompt-input-review.json), [copy review](prompt-copy-review.json), [preregistered comparison](../../../docs/plans/reconstruct-amendment-o.md).
