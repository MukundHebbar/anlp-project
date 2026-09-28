# AT: scope clarification helps, but does not validate the judge

All24 declared calls are terminal. The old p3 judge returned12/12 scores; the clarified p4 returned11/12, with one connection failure on the median-versus-mean contrast. No retry was made. See [the paired table](comparison.md) and [raw calls](run.json).

Against the frozen references, each prompt matches9 cases. A discovered reference defect changes the copy-only rectangle contrast from1 to0 under the existing copy-first rule; both judges correctly returned0. The frozen label remains intact, and the output-prompted [adjudication](reference-adjudication.md) is disclosed. Against that corrected development reference, p3 matches10/12 and p4 matches10/11 returned cases, with one missing planned case. Neither number estimates independent population accuracy.

The exact scope contrast is informative: p3 gives4 to “Is the function uniformly continuous on R?” with hypotheses only in public context; p4 gives1 under the explicit standalone contract. Both accept the fully stated counterpart. Thus the clarification fixes this particular scope error without rejecting its paired valid question.

Both prompts still give4 to a justification that calls a Lipschitz inequality the definition of uniform continuity. Both silently replace that false definitional claim with the true implication Lipschitz implies uniformly continuous. This violates the intended claim-checking standard. Both reject the more obvious false arithmetic in the rectangle proof. The remaining issue is therefore not simply inability to detect every erroneous proof; subtle false claims can be overlooked when the conclusion is familiar and true.

No production evaluator is promoted. P4 is a useful candidate scope clarification, but independent mathematical checking remains necessary and its own failure modes remain documented. These twelve authored controls contain related families, do not cover all five score levels, and cannot establish near-perfect reliability. The calibration does not change any Qwen score, success label or benchmark eligibility.

Next measurement work: independently adjudicate reference controls across all score levels and validate the source-blind rubric, mathematical check and semantic judge as a combined decision procedure on fresh cases. Freeze this before selecting a generator. More prompt variants or favorable seeds would not resolve the current validity problem.

Reproduce this report without API calls:

```bash
.venv/bin/python scripts/report_reconstruct_scope_calibration.py
```
