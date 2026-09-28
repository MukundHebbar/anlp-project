# AR: elementary task-understanding diagnostics

All three direct arithmetic problems were solved correctly. With the same model and fixed p13 reconstruction prompt, missing-premise reconstruction succeeded1/3 and missing-target reconstruction2/3. These deliberately elementary authored controls are not generated benchmark cases; they do not enter the desired20–40% recovery range, five-level histogram, or25-family confirmation.

| Family | DirectSOLVE | Missing premise | Missing target |
|---|---|---|---|
|Constant-speed distance|Correct|Correct duration4 and original distance question|Correct distance question|
|Urn probability|Correct|Wrong5 red balls; claims5/9=3/5|Correct red-probability question|
|Single discount|Correct|Correct latent original price80, but reversed target and malformed duplicated JSON|Wrong reduction-amount target; changes25percent to75percent; token-cap repetition|

The discount failures show that advanced mathematics alone does not explain the reconstruction failures. Qwen can solve the direct problem, yet commits to the wrong question and then rationalizes the supplied answer by altering a clue. The urn failure is actual inverse-arithmetic error. Distance demonstrates that the model can perform the intended reconstruction in at least one simple family. These are specific observations, not a population-level claim that one condition is easier.

Both missing-premise discount and missing-target discount remain failed planned draws; no output repair or best-of sampling was used. Missing-target discount reached8192 tokens. Source and candidate questions, exact prompts, raw outputs and failed contents are in [run.json](run.json); all nine judgments and exact arithmetic are in [analytic-review.json](analytic-review.json). [Protocol](../../../docs/plans/reconstruct-amendment-ar.md) was frozen before calls. No paid provider requests were made.
