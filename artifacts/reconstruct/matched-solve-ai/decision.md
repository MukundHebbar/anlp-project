# Same-family direct SOLVE diagnostic

All twelve original questions were given to the same local non-thinking Qwen3-4B Q4_K_M, with reference answers hidden. Twelve readable responses returned; no retries or technical failures. Four final answers were correct (46,80,118,137): **4/12,33.3%**. Three responses also passed strict analytic verification (80,118,137): **3/12,25%**. Source46 has the correct multinomial formula and answer but an incorrect description of the column counts; retain answer credit and the proof-consistency defect separately.

This does not validate RECONSTRUCT or meet its target. The model fails much of the underlying mathematics even with the original question: wrong polynomial moments, misuse of Wilson's theorem, confusion about Laurent radius, incorrect factorial-series convergence, unjustified differentiability, wrong integral exponents, confusion between a prime divisor and the smallest prime divisor, and an unevaluated recurrence with an incorrect final value.

The diagnostic also shows additional reconstruction difficulty on some forward-solvable items. Source137 is solved correctly here, but AG changed the unknown vertex-count target into a degree question with an impossible graph. Conversely, the Laurent and nested-integral errors appear in both direct SOLVE and RECONSTRUCT, so those reconstruction failures cannot be attributed solely to sparse clues.

These observations support testing inverse inference while separately tracking forward competence. They do not establish a hard performance ceiling: RECONSTRUCT receives the answer, whereas SOLVE does not. Prompt wording and output structure also differ. This is not an isolated information intervention, evidence of training transfer, or a population result. One seed and assistant analytic checks are insufficient for such claims.

Evidence: [frozen requests and raw outputs](run.json), [per-source analytic review](analytic-review.json), [summary](comparison.json), [executable arithmetic checks](reproduce-checks.py), [exact recurrence checks](../partial-exposure-ag/reproduce-count-checks.py), [runtime provenance](local-runtime-provenance.json), [prospective protocol](../../../docs/plans/reconstruct-amendment-ai.md).

AH input reviews were frozen before inspecting corresponding SOLVE outputs. No AH bank was included or excluded based on this diagnostic. These controls create zero reconstruction successes and never enter the reconstruction numerator.
