# Reviewed one-repair policy: local Qwen screen

Amendment S developmental screen; input coverage9/12 fails release; historical common-family outputs reused

| Arm | Scored / planned | Resolved mean /100 | Grounded | Same original | Provisional grounded semantic |
|---|---:|---:|---:|---:|---:|
| student_p1@policy_r | 17/18 | 30.88235294117647 | 2 | 0 | 0 |

Semantic judgments unresolved must not be read as confirmed failures. All provisional successes require mathematical and semantic case review. Seed0 is primary; seed1 cannot rescue it. Reported full analysis includes missingness bounds and paired source-bootstrap uncertainty.

This compares evidence-policy packages, not isolated clue counts or repair effects. New inputs are fixed before student output; no poor-answer replacement. Neither this conditional nine-family screen nor its four-family historical comparison satisfies the5/25 gate.

Evidence: [analysis and cases](repaired-student-analysis.json), [raw outputs and judgments](repaired-student.json), [exact public inputs](repaired-student-inputs.json), [preregistration](../../../docs/plans/reconstruct-amendment-s.md).

All local attempts, including the coefficient truncation: `{"attempts_including_failed_outputs": 18, "parseable_outputs": 17, "failed_outputs": 1, "attempts_with_recorded_usage": 18, "total_known_completion_tokens": 12391, "mean_known_completion_tokens_per_attempt": 688.3888888888889, "length_stops_including_failed_outputs": 1, "summed_request_elapsed_seconds": 312.548, "note": "Arm-level means from the shared analyzer describe parsed responses; this separate accounting includes failed raw completions."}`.
