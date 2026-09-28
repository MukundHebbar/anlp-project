# Fresh-cohort reconstruction and disclosure-policy comparison

The requested operating point is not met. On six independently reviewed eligible inputs, original nonthinking Qwen3-4B produced zero semantic recoveries and zero grounded semantic recoveries. Five readable responses received a mean rubric score of10/100; the sixth exhausted8192 tokens with unparseable repeated text. The original three-auditor policy admitted two of these inputs, also with zero successes and mean0. Common inputs reuse exact responses and judgments: this is six student draws, not eight independent trials.

| Policy | Eligible / allocated | Readable / planned | Mean on returned scores | Semantic / planned | Grounded semantic / planned | Grounded / allocated |
|---|---:|---:|---:|---:|---:|---:|
| AK: support + public + source + copy + manual |2/16|2/2|0|0/2|0/2|0/16|
| AL: support + source + copy + same manual |6/16|5/6|10|0/6|0/6|0/16|

The AL mean is conditional on five scored outputs. Across all six planned draws, assigning the missing score any value in[0,100] gives a mean in[8.33,25]. A missing score is not a successful reconstruction. A descriptive95% Wilson interval for0/6 is[0,39.0%]; this small adaptive development screen does not prove the population success rate is zero or establish the target20–40% band. No25-family confirmation has occurred.

## Why compare these policies?

[AL was registered](../../../docs/plans/reconstruct-amendment-al.md) before any AK/AL student outputs. The public auditor rejected source5 because the withheld threshold could be recovered from the answer, and source10 because the requested remainder was supplied. Those reasons conflict with the task definition: the final answer is deliberately supplied to support inverse inference. Source-aware auditing accepted both. We preserved the original policy and verdicts, then applied the same global gate removal to all16 allocated sources. No clues, model settings, student examples, or manual exclusions changed between policies.

Removing this veto increased eligibility, not successful recovery. It is not ready for production promotion: the reduced gate still needs known-leak regression controls, and source-aware auditing also made a disputed rejection on source21. Public-auditor acceptance on source54 contained an independently demonstrated mathematical error (R squared99 instead of100). These records do not support near-perfect converter or judge accuracy. The independent math verifier also marked source16 valid while acknowledging that its question asks for N2000, not the supplied answer98. Its derivation is correct, but this exposes a missed supplied-answer consistency check; the separate semantic/manual gate retains the failure. See [exact disagreement](math-verifier-disagreement.json).

## What Qwen actually did

| Source | Observed result | Why it is not equivalent recovery |
|---|---|---|
|5|Invented threshold75|Correct threshold51; its question has answer100! times(H100-H74).|
|10|Assumed n! congruent27 and asked for its remainder|Embeds the answer; does not recover n51.|
|16|Correctly derived k3 and N2000 in justification|Asked for N given count98, instead of asking for the count given N2000.|
|54|Left modulus R unspecified|Maximum depends on R; finite answer1/99 requires R10.|
|67|Left scalar c unspecified|Sum of inverse entries is1/c; original premise requires c1.|
|113|Repeated incomplete explanation to token cap|Visible question leaves root multiplier alpha unspecified; no readable completed response.|

Source16 is useful partial evidence: the inverse calculation worked, while the final question changed the requested unknown. We record successful latent parameter inference separately. Equivalent algebra, wording and reformulations are accepted when they preserve the premises and requested quantity. Swapping given and unknown quantities is a different problem; awarding it full recovery would change the metric after seeing results.

## Allocation, leakage and reproducibility

All16 contingency sources were allocated before content inspection; source1 was quarantined for an underdetermined recurrence, four conversions abstained, one conversion had a transport failure, and ten returned clue banks. Frozen manual review excluded29/41/59. AL source-aware review rejected21;29 had an empty audit completion and was already manually excluded. Six exact banks passed required source-support/source-disclosure checks, restricted copying challenge and manual review. All allocated cases remain in the end-to-end denominator. These are once-generated development examples; no held-out confirmation data were opened.

The six displayed banks contain4–5 ordinary-sentence clues and58–121 whitespace-delimited words. They expose the target and substantial setup/method information while withholding one essential premise. Clue count and information content are not matched to older cohorts, so this is not a clean causal comparison of clue quantity.

Student settings remain the original Qwen/Qwen3-4B Q4_K_M model, explicit nonthinking mode, temperature0.7, top_p0.8, top_k20, seed0 and8192 output-token cap. Teacher remains DeepSeek-V4.1-Flash, reasoninglow, temperature0. These are controlled settings, not empirically optimal hyperparameters. AK changes the cohort and prospective manual interpretation relative to older D4 studies; historical differences do not isolate the effect of more clues. AL versus AK isolates the gate-policy change on identical banks, with nested eligible sets and exact common-draw reuse.

The six inputs show that revealing a target and method while withholding one essential premise can retain inverse work, but these particular prompts do not reliably elicit it from this student. Next development should distinguish failure to infer from failure to state the recovered problem. Any new prompt must run on all frozen eligible cases, including failures, and be followed by fresh confirmation; do not select the one favorable latent calculation as a success benchmark.

## Evidence

- [Exact public evidence, original questions and readable outputs](readable-cases.json)
- [Frozen input decisions](input-review.json), [paired freeze checks](paired-freeze-check.json)
- [Primary and semantic judgments with raw responses](student.json), [manual mathematical review](response-math-review.json)
- [Summary metrics](comparison.json), [original-policy metrics](../fresh-development-ak/comparison.json), [draw reuse](../fresh-development-ak/draw-reuse.json)
- [Auditor contradictions](../fresh-development-ak/public-auditor-disagreements.json), [inverse certificates](analytic-inverse-certificates.json), [executable-check outputs](inverse-checks.json)
- [Orchestration incident and recovery](orchestration-incident.json): judging began before the final local request completed. Five exact judgments were snapshotted and restored without new calls; source113 client elapsed includes the pause and is excluded from latency comparisons. A regression test now forbids judging an attempted-but-in-flight request.

Independent source-blind mathematical verification is terminal:3 invalid verdicts,1 valid verdict and1 verifier validation failure on the5 readable responses. The valid verdict is the source16 supplied-answer mismatch discussed above, not a recovery success. Source67 returned a mathematically sound invalidity counterexample but failed exact-quote validation; preserve it as a verifier failure, not an accepted verdict. All exact outcomes are retained in [math-verification.json](math-verification.json). Assistant review is not independent human gold. Neither mathematical review nor a correct score on authored controls establishes general judge accuracy or SOLVE/JUDGE/RECONSTRUCT training transfer.
