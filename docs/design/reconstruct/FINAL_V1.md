# RECONSTRUCT final operational version1

Frozen for the100-source run on2026-09-21. This is the chosen operational specification; its empirical results come from the linked run, not from assuming the design is optimal.

## Input and output

The student sees the final answer and exactly FOUR numbered observations written as ordinary sentences, with equations when useful. A single frozen few-shot converter generates six supported observations; only its first four form this version's public input. At least one essential premise, relation, parameter or exact target must remain to infer. No source question, source solution, private certificate or dataset metadata enters the student prompt.

The student returns one JSON object containing `assumptions`, a complete standalone reconstructed `question`, and a concise `justification`. Equivalent mathematical formulations count. Necessary inferred conditions must appear in the question. The final answer must solve that reconstructed question. A plausible alternative can earn partial credit without counting as original-question recovery.

## Generation and safeguards

Use one converter prompt globally. Validate the bank, audit the exact public four-clue input against the source/reference mathematics, and perform a separate public-only copying challenge. Supported partial evidence and answer-conditioned inference are allowed; a fully exposed question or complete solution is not. Only accepted inputs proceed to Qwen. Rejections and uncertainty remain in the100-source export and coverage denominator.

No per-example clue increases, prompt tuning, regeneration, best-of sampling or filtering by the resulting score. One Qwen/Qwen3-4B Q4_K_M nonthinking draw,8192-token cap, temperature0.7, top_p0.8, top_k20, seed0. DeepSeek V4.1 Flash reasoninglow handles conversion, gates and judging in separate calls.

## Scoring

PC-v4 judges assess P (premise fidelity), T (target fidelity), E (evidence integration) and M (mathematical verification), each0–4. Fidelity is source-aware; validity is source-blind. Certificates and consistency checks must pass before aggregation. Quote validation tolerates explicitly logged whitespace differences for mathematical claims; automatic-zero evidence still requires exact question substrings.

`score100 = 6.25 * (P + T + E + M)`.

Five display bands:1=[0,20),2=[20,40),3=[40,60),4=[60,80),5=[80,100]. A known answer-copy/no-question shortcut overrides the final total to0; retain raw dimensions. Missing or uncertain judgments remain missing. Invalid inputs are conversion/gating outcomes, not student zero scores.

Provisional grounded original recovery requires accepted input, semantic equivalence, P4/T4/E4/M>=3 and no shortcut. Apparent recoveries need case review before reporting verified successes. Grade5 alone does not imply a recovery.

##100-source deliverable

The seeded100-source allocation is drawn from the existing113-question checked-answer pool. It is reused development material. Each allocated source appears with its original question, answer, public clues when generated, validity status, Qwen output when eligible, scores and missingness. Accepted public tasks are exported separately from the private answer-key/research files.

- [Frozen experiment protocol](../../plans/reconstruct-final-100-v1.md)
- [Manifest with exact prompts, sources and configuration](../../../artifacts/reconstruct/final-100-v1/manifest.json)
- [Questions and answers](../../../artifacts/reconstruct/final-100-v1/questions-answers.md)
- [CSV export](../../../artifacts/reconstruct/final-100-v1/questions-answers.csv)
- [Machine-readable research export](../../../artifacts/reconstruct/final-100-v1/questions-answers.jsonl)
- [Accepted public tasks](../../../artifacts/reconstruct/final-100-v1/public-tasks.jsonl)
- [Current run summary](../../../artifacts/reconstruct/final-100-v1/summary.json)

The earlier3/4/6 exposure proposal is not a three-arm manipulation in this run. This final run uses four public clues throughout. A final operational version does not guarantee100 accepted conversions, a target histogram, or an error-free teacher.

## Completed run and decision

Current display policy: `RECONSTRUCT-RATING-v4` supersedes v3. Cutoffs are18.75,43.75,56.25,75; apply `balanced_rating_v4(score_100)` after aggregation. Only the2/3 cutoff increases from37.5 to43.75, moving six tied responses from3 to2. The47 scored responses now have counts3,12,18,12,2. This is a user-requested post-hoc development calibration; numerical scores, judgments, gates and success labels remain unchanged. Bands are no longer equally spaced. Historical versions remain available; the results below retain their original scale. Freeze before fresh evaluation and disclose the adaptation history rather than claiming Gaussian scores or improved performance. [Updated ratings and provenance](../../../artifacts/reconstruct/balanced-ratings-v4/report.md).

The100-source run is complete:52 automatically accepted inputs,40 rejected,8 unresolved;52 Qwen attempts yielded50 parsed responses and47 resolved scores. The mean is44.41/100, median50, sample standard deviation16.03. Ratings1–5 have counts4,11,29,3,0. The middle rating is most common, but the histogram is asymmetric and contains no rating5 examples; it is not evidence of a Gaussian distribution.

Two responses reconstruct the original question semantically (sources94 and65), but neither provides substantive mathematical verification. There are0 recoveries meeting the frozen grounded-success criterion. Thus the20–75 mean-score target is met, while the20–40% semantic/grounded-success target is not. Keep this version as a reproducible operational baseline; these results do not justify calling it the best or a validated final benchmark.

Review found false copying allegations and an invalid original source accepted by the source-aware audit. Automatic gates and scores remain unchanged; all disputes, raw responses and missing outputs are preserved. Gate-passed inputs are not independently certified leak-free. The next revision would need a source-correspondence check for copying claims and a separately registered clue-content comparison, followed by new confirmation data.

All159 software tests and provenance checks on452 recorded attempts passed. These verify implementation and data bindings, not universal mathematical or judge accuracy.

- [Results and diagnostics](../../../artifacts/reconstruct/final-100-v1/report.md)
- [Complete downloadable bundle](../../../artifacts/reconstruct/final-100-v1/reconstruct-final100-deliverables.zip)
