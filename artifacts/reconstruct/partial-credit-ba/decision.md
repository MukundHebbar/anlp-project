# BA decision: expected score shape not established

The new PC-v1 rubric does not produce the requested middle-heavy distribution on these saved responses. Means fall within20–75/100, but that does not establish a useful distribution or judge reliability. No policy is promoted on this evidence.

| Added bridge clues | Scored / scheduled | Mean /100 | Counts at ratings1,2,3,4,5 | Sample variance (score points squared) |
|---|---:|---:|---|---:|
|0|5/6|32.50|3,0,0,1,1|2000.00|
|1|6/6|30.21|3,0,2,0,1|1240.89|
|2|6/6|64.58|2,0,0,0,4|2510.42|

These diagnostic rows include rejected/unresolved inputs. Restricting to accepted inputs gives histograms[3,0,0,1,1] on5/6 scored,[2,0,1,0,1] on4/4 and[1,0,0,0,2] on3/3. Thus filtering does not reveal the desired shape. The low arm has one missing fidelity judgment, not an imputed zero; its six-case mean is bounded by30.21–38.54. The middle arm has two unresolved input audits. The rich arm has three rejected inputs.

Rating3 is not the mode in any observed arm. The middle arm does contain meaningful partial cases: an unspecified cycle threshold scores43.75, and a wrong hyperbola parameter scores56.25 (the latter input audit remains unresolved). The rich arm remains polarized. A fifth-band score does not itself establish a grounded semantic success.

The targeted [analytic review](review.json) documents an equivalence error and two overbroad shortcut overrides. One apparent partial score is caused by a false distinction between exactly one and at least one long cycle; other partial work is erased by automatic zero overrides. Raw scores remain unchanged. Histogram-driven corrections would not validate the measurement.

Scope:18 saved p14 responses from six repeated source families, graded under newly frozen PC-v1 prompts. These are not student outputs from the proposed new PC-v1 converter/student prompts. No claim about a Gaussian population, optimal clue count, or validated new task distribution follows. No independent ratings were repeated, so the reported variance is across responses, not judge-repeatability variance.

All36 judge calls terminated:35 returned schema-valid outputs and one connection failure. Six midpoint copy checks terminated with five returns and one connection failure; no retries. The full local unittest suite passed141 tests; this checks software behavior, not judge accuracy.

Next: follow [the calibration controls](next-calibration.md), validate the shortcut/equivalence boundaries, then test the fixed PC-v1 conversion policy on fresh source families. Keep thresholds and weights fixed; publish the resulting histogram even if it remains polarized.

See [full distribution](distribution.md), [machine-readable scores and bounds](distribution.json), [frozen manifest](manifest.json), [raw judgments](run.json), and [registered protocol](../../../docs/plans/reconstruct-amendment-ba.md).
