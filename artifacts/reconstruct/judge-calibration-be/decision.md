# Repaired partial-credit judging: tested boundaries pass

Use the PC-v4 fidelity/validity prompts and the current certificate validator for new development scoring. All19 registered cases pass the expected labels and structural checks after a transparent deterministic validator replay. All five saved-response regressions pass. This is development validation, not a claim that the judge is error-free on unseen problems.

## Full iteration history

| Stage | Model calls | Cases passing all registered checks | Remaining issue |
|---|---:|---:|---|
|BB / PC-v2|19|14/19|Five missing verification certificates; required fields absent from JSON example|
|BC / PC-v3|19|18/19|Tautology correctly flagged but given M4 for merely restating its premise|
|BD / PC-v4, strict quote validator|19|18/19|One mathematical quotation inserted a space; its labels matched|
|BE / same BD outputs, revised validator|0|19/19|None on the registered checks; one whitespace-only quote match logged|

BE is not another independent model trial. It reuses every BD output with unchanged labels, raw content and expected references. Its manifest records the original run/manifest hashes and revised validator hash. All prior failures remain available in their original run directories.

## What is fixed

- Equivalent at-least-one/exactly-one long-cycle questions receive P4/T4; the nearby threshold40 case is correctly rejected using two disjoint40-cycles as a counterexample.
- Missing/wrong parameters lower premise fidelity without automatically changing the requested target.
- The saved inverse hyperbola question no longer receives a false answer-copy zero. The judge derives N=2000 and identifies both exponent and arithmetic mistakes in the response.
- The saved underdetermined factorial question no longer receives a false answer-copy zero. The judge identifies differing allowed remainders and the circular justification.
- Actual tautological questions retain the hard-zero flag, with exact premise/request quotations; mere restatement earns M0.
- Wrong proofs with correct final numbers lose mathematical credit. Legitimate inverse inference, concise correct proofs, and the saved complex-circle and factorial-limit examples pass their registered checks.

## Mechanical safeguards

Validate score types/ranges, required certificates, all clue indices, Boolean/status consistency, full-fidelity equivalence and high-math verification flags. Mathematical claim quotes must match response text; whitespace-only matches are explicitly logged without altering the raw judgment. This text-matching allowance is not a semantic equivalence proof. Automatic-zero premise/request quotes must still match the question exactly and cannot be taken from the explanation.

The sole BE normalization note is in `valid_inverse_inference`: “has 2^m” versus source “has2^m”. Changed numbers/operators/text remain rejected. No judge scores were changed and no outcomes were resampled to pass the checks.

## Validation scope and limits

Six authored fidelity cases, eight authored validity cases and five known saved-response regressions. Expected labels were frozen before each call and never sent to DeepSeek. The controls were reused adaptively, with related examples in the prompts:19/19 is a regression/calibration result, not a held-out accuracy estimate. Not every subjective evidence-integration grade has an independent gold label; repeated-call stability and fresh-domain accuracy remain unmeasured.

The full local suite passes153 tests, including12 validator tests. A local preparation check confirms the saved-response scorer selects strict certificate validation and preserves equal weights and score bands. Old BA scores are unchanged; neither a new Qwen distribution nor converter accuracy is established here.

57 DeepSeek calls used an estimated$0.06651 in returned provider usage. BE adds no calls; replayed usage is deduplicated. The project ledger records$1.96644 total estimated usage with81 historical missing-usage records, so it is not a complete billing reconciliation.

## Evidence and use

- [Registered labels and per-case comparisons](report.json)
- [Original outputs, provenance and validation notes](run.json)
- [Frozen source hashes, prompts, cases and labels](manifest.json)
- [Full local tests](tests.log)
- [Operational judge specification and commands](../../../docs/design/reconstruct/JUDGE_VERIFICATION.md)
- [Fidelity prompt](../../../data/prompts/reconstruct/partial_credit_v4/judge_fidelity.md)
- [Validity prompt](../../../data/prompts/reconstruct/partial_credit_v4/judge_validity.md)

The saved-response scoring runner now defaults to PC-v4 in a new output directory and rejects invalid judgments instead of inventing a score. Keep the score weights/bands fixed. Fresh independent validation is still required before claiming near-perfect judging or using the desired histogram as a policy-selection criterion.
