# Same-input stronger-model feasibility

Source-blind feasibility on the same nine p1 inputs; different model/reasoning/compute, not a Qwen release result

Planned9 families; 8 parsed responses. Teacher judges count6 grounded source recoveries. Assistant mathematical review verifies5 clear witnesses, with a sixth shear/domain formulation kept qualified. All five clear witnesses came from their first generation call. Qwen primary seed0 recovered0 originals on these same9 inputs.

| Source | Raw score | Raw semantic label | Independent assistant review |
|---|---:|---:|---|
| 8 | 4 | 2 | verified_original |
| 27 | 4 | 2 | verified_equivalent_formulation |
| 33 | 4 | 1 | different_question |
| 77 | 4 | 2 | equivalence_requires_domain_review |
| 86 | 3 | 2 | verified_original_with_minor_proof_omission |
| 112 | 4 | 2 | verified_original |
| 136 | 1 | 0 | wrong_answer_and_different_question |
| 141 | 4 | 2 | verified_original |

Source143 produced no visible response on either permitted attempt. Source136 is a wrong maximum claim: an exact incidence-divisibility obstruction refutes attainability. Source33 is a different lemma, not original recovery, and its direct copying raises a separate scoring-contract concern.

This establishes concrete feasibility for several inputs, not general learnability, an isolated thinking effect, near-perfect teacher accuracy, or the required Qwen5/25 result. Model size, reasoning and effective compute differ; the source-disjoint confirmation set remains untouched.

Evidence: [raw requests and results](stronger-feasibility.json), [case-level analysis](stronger-feasibility-analysis.json), [mathematical review](stronger-math-review.json), [set-bound obstruction](stronger-set-bound-counterexample.json), [radical equivalence and reference](stronger-radical-equivalence.md), [preregistration](../../../docs/plans/reconstruct-amendment-t.md).
