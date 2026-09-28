# RECONSTRUCT: evidence and unresolved release criteria

Latest update: [AU–AZ richer-information search](../../../artifacts/reconstruct/bridge-composition-ax/decision.md) reaches2 verified recoveries out of6 scheduled families, with one documented mathematical adjudication. Mean raw quality66.67/100; histogram[2,0,0,0,4]. The immediate recovery goal is achieved; broader teacher/distribution/confirmation goals remain open. [Exact completion audit](../../../artifacts/reconstruct/bridge-composition-ax/completion-audit.json). The earlier findings below remain historical evidence.


The latest three-clue procedure reaches the requested mean-score range, but it does not reach the semantic-recovery or middle-heavy-distribution objectives. Repeating its inputs at other seeds does not fix that. A final benchmark version is therefore not selected.

| Comparison | Observed result | What it supports |
|---|---|---|
| [AL: reduced disclosure gate](../../../artifacts/reconstruct/constructive-gate-al/decision.md) |6/16 eligible; mean10 on5 scored;0/6 semantic/grounded |Removing a veto improves coverage but does not establish useful reconstruction |
| [AM: explicit target-preservation instruction](../../../artifacts/reconstruct/target-preservation-am/decision.md) |0/6 semantic/grounded; four primary connection failures |No demonstrated benefit from that wording change |
| [AN/AO: missing-target full bank, changed demonstration](../../../artifacts/reconstruct/missing-target-an/decision.md) |2/16 eligible; each arm mean12.5,0/2 semantic/grounded |Neither full-bank version qualifies |
| [AP: first3 unchanged clues](../../../artifacts/reconstruct/target-prefix-ap/decision.md) |7/16 eligible; mean28.57; histogram[2,4,0,0,1];0/7 standalone semantic |Coverage and average score improve; correctness and desired shape do not |
| [AQ: matched original SOLVE](../../../artifacts/reconstruct/matched-solve-aq/decision.md) |7/15 correct answers;3/15 strictly reviewed explanations |Forward mathematics is also a limitation; no hard ceiling or transfer claim |
| [AR: elementary controls](../../../artifacts/reconstruct/elementary-controls-ar/decision.md) |Direct3/3; missing-premise1/3; missing-target2/3 |Specific reconstruction failures persist even on directly solvable problems |
| [AS: identical inputs, seeds0/1/2](../../../artifacts/reconstruct/student-variance-as/decision.md) |18/21 scores; source-balanced mean28.57; within-source observed variance0 |The coarse score pattern repeats; no evidence that reseeding solves the problem |
| [AT: explicit standalone judge scope](../../../artifacts/reconstruct/judge-scope-at/decision.md) |Scope contrast fixed; false-definition full-credit error remains in both judges |A useful clarification, insufficient for judge promotion |

Comparisons use different eligible subsets unless explicitly matched. AP and AN share only one fully eligible student family, so their aggregate mean difference is not a clean causal clue-count effect. AR's authored controls are not benchmark successes. AS contains seven independent families, not21. All development reuse is disclosed; no held-out confirmation or training-transfer result is available.

## What each model gets wrong

Qwen often identifies some useful algebra but returns the wrong question: an inferred parameter instead of the original requested quantity, an angle instead of its optimized squared tangent, or the largest avoiding hand instead of the smallest guaranteeing hand. Other responses contradict the given quantities to force the supplied answer, omit necessary premises, or make false mathematical claims. The source16 latent-parameter success and the discount control are retained as partial abilities, not semantic recovery.

DeepSeek sometimes grades the question using premises supplied only in its justification or public context, while its source-aware judge requires a standalone question. It has awarded full credit to proofs containing false statements and returned score/shortcut combinations rejected by the declared schema. The separate math verifier has also accepted an answer to the wrong inverse question, and occasionally fails exact-quote validation. These are measured failure modes; conversion and judging are not established as nearly perfect.

The assistant-authored reference process is also fallible. AT's original rectangle-scope contrast label overlooked copy-first priority; its frozen label and output-prompted correction are both retained. Corrected development agreement must not be presented as independent validation.

## Variance and distribution

AS pooled within-source rating variance is0 over11 degrees of freedom, conditional on returned judgments. Across all18 available ratings, sample variance is1088.64 points squared (SD approximately32.99); this reflects large between-source score differences. The all-draw available mean31.94 is inflated relative to the equal-source mean28.57 by missing low-scoring cases. Planned-score bounds are27.38–41.67. These descriptive ordinal-score statistics do not isolate judge repeatability.

Both complete seed histograms are[2,4,0,0,1] for displayed ratings1–5. There are no ratings3 or4. The mean target alone therefore conceals the actual pattern. Forcing a Gaussian fit, changing rating thresholds, dropping failures or selecting favorable seeds would not establish the requested task quality.

## Claim status

- Supported: a fixed, inspectable pipeline and controlled development comparisons exist; actual errors, negative results and mathematical counterexamples are saved.
- Supported on these examples: shorter exposure increases eligibility; repeated seeds preserve the same coarse scores; direct solving and reconstruction have distinguishable failure modes.
- Not established: optimal clue count, superiority of sentence format,20–40% semantic recovery,5/25 grounded confirmation, a middle-heavy population distribution, near-perfect conversion/judging, or training transfer.

Use [CURRENT_PROTOCOL.md](../../design/reconstruct/CURRENT_PROTOCOL.md) for the operational definitions. Historical pilot selections remain historical. The next study must resolve measurement and input validity before claiming a final version or opening confirmation.

All AS and AT calls are terminal. The reconstruction regression suite passes71 tests. The corrected cost ledger records approximately$1.794 across saved cost-bearing requests, including$0.354 imported pilot costs;78 records lack usage, so this is not a complete billing total. Calibration `records/raw` calls are now included and deduplicated alongside normal pipeline records.

Reproduce the latest reports without paid calls:

```bash
.venv/bin/python scripts/report_reconstruct_student_variance.py
.venv/bin/python scripts/report_reconstruct_scope_calibration.py
.venv/bin/python scripts/reconstruct_cost_ledger.py
.venv/bin/python -m unittest discover -s tests -p 'test_reconstruct*.py' -q
```
