# Amendment T: source-blind stronger-model feasibility on the same inputs

Registered after S's primary grading and manual review of all17 parseable Qwen outputs. Primary seed0 has zero semantically recovered originals; generic high scores concern another theorem. Secondary grading has completed except one bounded technical evaluator retry. Independent counterexamples identify wrong values, missing constraints and changed targets. Before another prompt change, test whether a stronger model can construct valid, preferably source-equivalent questions from the same public evidence.

Use exactly S's nine frozen inputs and student_p1 instruction/example. DeepSeek V4.1 Flash acts as a student in fresh stateless calls, seeing only final answer and rendered sentence clues. No original Q, checked solution, hidden support, audits, copying candidates, source ID or Qwen outputs enter the prompt. Archive the actual rendered prompt and hashes. Private references may remain in the artifact solely for subsequent evaluation.

One teacher completion per family, temperature0, reasoning low,8192 cap,180s timeout. There is no provider decoding seed in teacher_call; record seed=null and draw_index=0, not a fictional seeded replicate. At most one same-settings technical retry; no retry of a poor mathematical question. Freeze all nine requests before any call. Use three concurrent calls so this may overlap the one remaining S evaluator retry without exceeding four paid calls globally.

Evaluate with the same source-blind evaluate_p2 and separate source_recovery_p2. Independently verify every claimed grounded semantic success, and inspect alternatives and failures. Teacher judging its own output is not independent validation. A concrete checked reconstruction proves feasibility for that item, not general learnability or population accuracy. The comparison changes model, reasoning mode and effective compute together; it cannot isolate a causal benefit of thinking or establish the later SOLVE/JUDGE/RECONSTRUCT transfer claim.

Interpretation:

- Verified original recoveries here, with Qwen failing, support a capability/inference gap under this fixed evidence/prompt. Test a globally specified few-shot intervention next; do not selectively add clues to the successful teacher items.
- Only valid alternatives show feasibility of grounded construction but do not meet original recovery. Because p1 permits alternatives, this alone does not prove source recovery impossible; an explicit source-recovery instruction is a distinct subsequent intervention.
- Both models failing calls for review of information sufficiency and task definition. A finite unsuccessful search is not an impossibility proof.
- Any claimed clue benefit should subsequently be checked against a matched answer-only control; this experiment alone does not rule out answer-based memorization.

Budget: nine new teacher generations and up to18 judgments, $.20 reserved under the existing$5 cap. No Qwen checkpoint change, no C/R access, no expansion of the source set, and no final confirmation. Preserve S's failed coverage and recovery results regardless of this probe.
