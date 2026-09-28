# Validity audit before fresh confirmation

The historical pilot establishes that a local pipeline can generate, reconstruct, and score examples. It does not establish global prompt optimality or training transfer.

## Concrete failure mechanisms

- D2 source 30: the baseline asks for Log'(1), derives 1 correctly, but the supplied answer is 2. This is a target-selection failure, not lack of context capacity.
- D2 source 95: the baseline computes the integral as a nonconstant expression, then concludes 0 without putting a limiting operation into the question. Its assumptions try to repair a condition missing from the actual question.
- D2 source 105: coprimality appears in the observations and justification but not the question. It also confuses the value of an integer expression with a solution count.
- D2 source 11: the clue's k<4 is a bound on the divisor count, while the supplied answer 4 is the composite integer n. Treating every visible intermediate as the target produces a contradiction.
- D2 source 134: the judge marks answer_correct=true under a charitable interpretation of a vague maximum question even while grounding fails. This is a warning about judge generosity on secondary labels. Grounded success is more restrictive, but authored fixture accuracy alone does not establish reliability.

These observations motivate inverse-construction demonstrations and consistency checking. They do not predict guaranteed improvement.

Historical SOLVE stratification gives four explicitly verified-correct sources in D1 and four in D2. The remaining records include both demonstrated errors and unresolved verification, which must not be merged into one wrong category. Thus the available historical correctness labels alone do not explain the D1/D2 reconstruction gap. They also come from a different runtime and are not a matched local SOLVE baseline.

## Experimental defects repaired in the follow-up

1. Historical p1 and p2 scoring rubrics differ. New comparisons use only evaluate_p2.
2. One decoding seed cannot distinguish a robust change from sampling luck. Follow-up D2 uses two fixed seeds, with source as the independent unit.
3. An aggregate of all exploratory records combines different source sets and conditions. A new analysis script explicitly matches source, clue evidence, prompt, and seed.
4. A missing judgment or missing per-clue check must not disappear from the denominator. The analysis reports planned, generated, resolved, and success bounds.
5. Changing student JSON field order could change the judge's input order. The judge now always sees question, justification, assumptions in the same order.
6. A hoped-for medium accuracy band is not a reason to claim a task valid or invalid. Fresh confirmation evaluates the selected candidate even if its expected accuracy is low, provided the task and inputs are usable.

## Remaining limitations

The converter and judge share a teacher model, which creates correlated-error risk. Assistant mathematical review is not independent human annotation. The source pool was selected on teacher SOLVE success; it is not representative of all mathematical questions. Source solutions have verified final answers, not formal proof certificates. Audit flags for leakage and distinctness remain qualitative, and entire banks can be redundant even when every clue is individually true. Quantization and backend differ from historical Qwen SOLVE runs.

The new study is prompt/procedure development. Claims about distinct reasoning capabilities helping each other require the later SOLVE/JUDGE/RECONSTRUCT training-by-evaluation matrix, with comparable training budgets and source-disjoint evaluation.

## Runtime-default finding during execution

The live llama.cpp `/props` response reports default `min_p` approximately 0.05. Student requests override temperature, top-p, top-k, seed, and maximum tokens but omit min-p. Therefore the current matched follow-up inherits min-p 0.05, not an assumed zero. `artifacts/reconstruct/followup-v2/server-props.json` preserves the full response. Keep this configuration fixed for the current comparisons; a min-p change needs a new experimental condition. This is another reason not to pool the laptop results with historical vLLM scores.
