# BB: semantic repairs work on returned controls; output contract fails

All19 calls completed. Fourteen judgments passed certificate validation and all their registered label checks. Five fidelity outputs omitted the requested verification_certificate and were rejected; they are not silently admitted even when their other fields appear correct. No transport retries or label repairs were used.

The missing certificate was requested in prose but absent from the example JSON. BC therefore changes the explicit output schema while keeping the grading rules, expected control labels, weights and score bands fixed. It reruns all19 controls, not only favorable/failed cases.

The repaired validity role distinguished the known false-zero cases from actual tautological questions and supplied mathematical checks. The hyperbola inverse question asks for N, not its supplied point count; the judge derived N=2000, found the student's exponent and arithmetic mistakes, and retained M1 with shortcut=false. The factorial question leaves n undetermined; the judge gave differing admissible remainders, M0 for circular verification, and shortcut=false. Valid complex-circle and factorial-limit reconstructions passed their registered math checks.

These are authored development controls and known regressions. They do not establish general judge accuracy, repeated-call stability, or a new student-score distribution. See [report](report.json), [raw calls including rejected outputs](run.json), and [frozen prompts/cases](manifest.json).
