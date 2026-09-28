# Auditor budget probe: completion improved, reliability not established

| Source | Cap8192 | Cap16384 | Tokens used at16384 |
|---|---|---|---:|
| 8 | REJECT | ACCEPT | 2315 |
| 136 | no_visible_output_length | ACCEPT | 1434 |

The source136 failure is verified budget exhaustion: finish_reason=length and all8192 completion tokens were reasoning. The larger-budget repeat returned an answer, but used only1434 tokens. The resolved control, source8, changed from REJECT to ACCEPT while using2315 tokens. Therefore this tiny selected probe does not establish that extra tokens caused completion or improved accuracy; repeat variability and the changed timeout are confounds.

The source8 decisions disagree specifically on whether expanding its displayed combined numerator into the displayed denominator is substantive missing reasoning or routine completion. That distinction is central to the task definition and requires calibration. The8192 response also has status REJECT but full_solution_exposed=false, despite its reason saying the solution is exposed; preserve the raw internal inconsistency rather than treating every diagnostic field as reliable.

Decision: retain original count-study settings and labels. Do not silently replace a rejection with the larger-budget acceptance. A larger cap may be an engineering response to measured truncation, but it is not evidence of near-perfect audit accuracy.

Evidence: [paired records](audit-budget-comparison.json), [larger-budget raw calls](audit-budget-probe.json), [original raw calls](run.json).
