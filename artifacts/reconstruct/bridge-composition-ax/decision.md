# AX: richer partial equations plus premises-first reconstruction

The information search achieved **two verified recoveries out of six scheduled development examples**: complex geometry54 and factorial-root limit113. Both preserve the original mathematical question, pass the exact-input disclosure audit and the public-only copying challenge, and have mathematical certificates. DeepSeek's source-equivalence judge gives2/2 to both. The [completion audit](completion-audit.json) binds every claim to its exact input and response.

There are four raw semantic matches (5,54,67,113), three on source-disclosure-accepted inputs, and two after the additional copying gate. Source5's input is source-disclosure-rejected. Source67's actual reconstruction is correct, but its public cS=1 clue permits the trivial alternative “What is cS?”, so the stricter input gate excludes it. No rejection is overridden to obtain the desired rate.

The geometry verification passes automatically. The factorial-root verification initially fails because the verifier says that1/e “only occurs when alpha=1” while denying that1/e implies alpha1. The exact raw rejection remains in math-verification.json. The [once-only independent implication check](alpha-adjudication.json), with true and false controls frozen beforehand, correctly resolves all4 implications and agrees with the analytic Stirling proof. Thus there is **one fully automatic success and two after disclosed mathematical adjudication**, not two error-free automatic decisions.

The scheduled-family success rate is2/6=33.3%; among the three inputs surviving disclosure and copying, it is2/3=66.7%. These are different quantities. This reused six-family development cohort does not establish the broader20–40% student success rate or a25-family confirmation result. Raw quality mean is66.67/100, and displayed rating counts1–5 are[2,0,0,0,4], so the desired middle-heavy distribution is not met.

## What changed

The fixed AL converter already retains the requested quantity and withholds a premise parameter. The AW converter appends two supported symbolic observations to every input, using the same two examples and prompt. It does not substitute the supplied answer or reveal the missing parameter. The p14 student prompt asks for inferred premises before the complete question and verification. The original Qwen3-4B Q4_K_M model, nonthinking mode, seed0, temperature0.7, top_p0.8, top_k20 and8192-token limit stay fixed. This is still one Qwen call per example; no repair pass or best-of selection.

| Successful family | Extra information that helped | What Qwen still had to infer |
|---|---|---|
| Complex-number maximum | Circle equation and general maximum1/(R²−1) |Use supplied1/99 to inferR=10, put modulus10 in the question and retain the maximumtan² target |
| Inverse-matrix entry sum |S=onesᵀA⁻¹ones andcS=1 |Use suppliedS=1 to inferc=1, then ask forS rather than for c |
| Factorial-root limit |General normalized-root expression and its logarithmic asymptotics |Use a finite nonzero1/e limit to inferalpha1, then state the original nth-root sequence |

For the accepted cases, the mathematical relation is exposed, but the original numerical premise and completed reconstruction are not. The matrix row illustrates a rejected-input shortcut and is not part of the two counted successes. This is a high-information, one-gap inverse task. It should not be described as extremely sparse or as a test of independently discovering the forward theorem.

## Matched information search

[The paired table](bracket-comparison.md) verifies the exact same six source families and nested public observations. Under the same p14 prompt, zero, one and two added observations give2/6,1/6 and4/6 meaningful semantic matches respectively. After source disclosure and analytic grounding, three remain; the public-only copying check excludes the matrix input, leaving two verified cases. The zero-bridge matches have weak verification; the midpoint recovers the geometry question with its final optimization omitted. Additional information is not monotonically beneficial, so this is an adaptive bracket search, not a guaranteed binary-search algorithm.

The p13 prompt on the same two-bridge inputs recovers only1/6 (source5, whose input is disclosure-rejected), while p14 recovers4/6 before disclosure. P14 changes instruction emphasis, the demonstration and output order together. The data support this prompt package on richer information, not a causal claim about output order alone. Do not select a different exposure or prompt separately for each source.

## Limits and next use

The final bound-record audit confirms the immediate two-recovery objective, including the disclosed mathematical adjudication. It does not establish the broader20–40% population rate, desired middle-heavy rating distribution, independent teacher accuracy,5/25 confirmation or training transfer. The selected condition is a candidate for fresh validation, not a globally optimal task version. Audit disagreement remains: the strict source-aware judge rejects the full symbolic formulas for5/16 while accepting the inverse formulas for54/67/113. All input rejections are retained. The single math-verifier correction is explicitly documented and independently checked; it does not change a student response.

Reproduce the paired analysis without API calls:

```bash
.venv/bin/python scripts/report_reconstruct_information_bracket.py
```

Protocols: [AW](../../../docs/plans/reconstruct-amendment-aw.md), [AX](../../../docs/plans/reconstruct-amendment-ax.md), [AY](../../../docs/plans/reconstruct-amendment-ay.md), [AZ](../../../docs/plans/reconstruct-amendment-az.md). Earlier AU/AV findings remain separate because they use a different seven-family cohort.
