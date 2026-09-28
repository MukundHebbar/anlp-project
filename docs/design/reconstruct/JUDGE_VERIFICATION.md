# Partial-credit judge verification

The PC-v1 score weights and rating bands remain fixed. Judge prompt revisions are versioned separately; BA scores are never overwritten. PC-v2 repairs semantic and shortcut boundaries; PC-v3 additionally places every required certificate field inside the JSON example. PC-v4 explicitly assigns M0 to mere restatement, even when the restated value is literally true. The final PC-v4 prompts plus the BE validator pass all19 registered development controls (including five saved-response regressions). This is not a held-out accuracy estimate. See [the complete report](../../../artifacts/reconstruct/judge-calibration-be/decision.md).

## Decisions the judge must distinguish

- Equivalent mathematical formulations receive full fidelity, including quantifiers that become equivalent under the premises. The judge must provide a mathematical correspondence or counterexample.
- A missing or wrong input parameter lowers premise fidelity. Target fidelity concerns the requested quantity/event; it is not another penalty for the same missing input. Changed targets still lose target credit.
- A question that explicitly supplies the quantity it requests is answer-copy tautology. Hard-zero evidence must quote both the premise and request from the question itself.
- Using the supplied answer to infer a missing premise is valid inverse reasoning. Asking for a different unknown using that answer is a target error, not necessarily a tautology.
- An underdetermined question keeps partial credit. A circular explanation receives low mathematical-validity credit; it does not automatically erase valid premise/target/evidence credit.
- Correct final numbers do not excuse false essential mathematical claims. Conversely, a concise sufficient proof need not expand routine algebra.

## Verification contract

The fidelity role sees the source and returned question. The validity role sees only the public answer, observations and response. Expected calibration labels are never sent to either role. Every validity judgment checks all numbered observations and independently assesses the exact standalone question; assumptions and explanations cannot silently supply missing question conditions.

`validate_judgment` in `src/anlp_project/reconstruct_judge_validation.py` requires bounded integer dimensions, resolved labels for scored outputs, complete clue coverage, nonempty verification certificates, response substrings for claim quotes (with explicitly logged whitespace-only matching allowed), and question-only quotes for answer-copy overrides. Automatic-zero quotes always require exact question substrings; whitespace tolerance applies only to mathematical claim tracing and is not a semantic-equivalence check. It rejects conflicting equivalence/dimension labels and high mathematical scores with negative verification flags. Failure remains an unresolved judgment with its raw response retained; there is no guessed score or silent repair.

These are structural safeguards, not a proof checker. A model can still supply an incorrect argument or quote a real but irrelevant passage. The calibration suite must check the decisions themselves. Production accuracy needs additional independently labeled, fresh cases and review of uncertain or disputed judgments. No finite prompt test establishes an error-free judge.

## Reproducible calibration

The runner freezes rendered prompts, hidden expected labels, source responses, model settings and hashes before requests. Calls are once-only. Reports retain planned, returned, failed and pending counts and every label comparison. Known-regression cases are development data, not a held-out accuracy claim.

```bash
.venv/bin/python scripts/calibrate_reconstruct_pc_judges.py report \
  --root artifacts/reconstruct/judge-calibration-be \
  --prompts data/prompts/reconstruct/partial_credit_v4
```

Use a new root for any new experiment; existing manifests cannot be replaced with `prepare`. `run` does not retry already attempted calls. Review raw and validated outputs together before promotion. Grade reliability must precede tuning the student-score histogram.

## Using the revised judges on saved responses

The existing partial-credit scoring runner now supports a separate output root and judge directory. With PC-v2/v3/v4 it applies the certificate validator before admitting a judgment. Aggregation still uses the original equal weights and score bands; selecting new prompts does not change old scores. For a separately registered new run:

```bash
.venv/bin/python scripts/run_reconstruct_partial_credit.py \
  --root artifacts/reconstruct/partial-credit-new-run \
  --judge-prompts data/prompts/reconstruct/partial_credit_v4 --prepare-only
.venv/bin/python scripts/run_reconstruct_partial_credit.py \
  --root artifacts/reconstruct/partial-credit-new-run \
  --judge-prompts data/prompts/reconstruct/partial_credit_v4
.venv/bin/python scripts/report_reconstruct_partial_credit.py \
  --root artifacts/reconstruct/partial-credit-new-run
```

This runner scores the18 saved bracket responses, not new Qwen generations. Calibration BB/BC/BD and deterministic replay BE does not itself rescore that full bracket or establish a new score distribution. Running the commands above makes36 paid calls; use the same recorded budget/concurrency constraints.
