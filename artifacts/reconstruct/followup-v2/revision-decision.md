# Two-call self-revision: development decision

Twenty-four baseline drafts were submitted to local Qwen for revision without teacher feedback or private source information. Twenty-three outputs were parseable and judged; one malformed output remains unresolved. No poor mathematical response was retried.

Resolved mean: 33.70/100. All-24 missing-score bounds: [32.291666666666664, 36.458333333333336]. Grounded successes: 2/23 resolved, versus 2/24 baseline.

On the eleven source families with both seeds resolved, paired score change is +2.27/100, with descriptive bootstrap interval [0, 6.818181818181818]. Grounded-success outcomes do not change on those families. A zero-width bootstrap interval for identical observed binary differences does not establish population equivalence.

Mean completion tokens across both calls for parseable revisions: 428.1, versus 198.4 for the single-call baseline. This excludes the unresolved revision from that mean and is not total experiment cost; its raw usage remains in revision-study.json. Prompt/input tokens and latency must also be considered for full compute accounting.

Decision: do not promote self-revision on this evidence. The extra call produces no demonstrated grounded-success gain. Some answers become numerically compatible while observations remain decorative: source 73 fixes a_0=2 but does not connect the power-tower observation; source 134 names eight powers but leaves the removal-process observations unexplained. Source 105 recovers the question but gives a false enumeration. These are distinct failures that a more generous answer-only metric would conceal.

Judge-field caveat: source 40 seed 0 is marked well_posed=false yet answer_correct=true because the judge imports the underlying quartic coefficient. The question as written does not determine that coefficient. The overall low score rejects it appropriately, but the isolated answer_correct diagnostic is unreliable here. Report well_posed AND answer_correct jointly and retain this disagreement for evaluator calibration.

Evidence: [analysis](revision-comparison.json), [raw outputs, failures, and judgments](revision-study.json). Adaptive development only; no confirmation or equal-compute superiority claim.
