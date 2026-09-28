# Final100-source run: results

Frozen version: four sentence clues plus the final answer; local Qwen3-4B nonthinking; PC-v4 judges. This is reused development data, not untouched confirmation.

- Allocated sources:100; accepted inputs:52.
- Input dispositions:{'accepted': 52, 'rejected': 40, 'unresolved': 8}.
- Qwen attempts:52; parsed responses:50; scored:47.
- Mean:44.41/100; median:50.00; sample standard deviation:16.03; sample variance:256.85.
- Automatic semantic recoveries:2; provisional grounded recoveries:0; reviewed verified grounded recoveries:0.

| Rating | Count |
|---|---:|
|1|4|
|2|11|
|3|29|
|4|3|
|5|0|

These rating counts cover accepted inputs with resolved scores. Rejected inputs and missing judgments are not imputed as zero. Grade5 is not automatically a strict recovery. Raw scores are not rewritten after manual review.

| Topic | Allocated | Accepted | Scored |
|---|---:|---:|---:|
|Algebra|27|14|13|
|Calculus|24|13|11|
|Discrete Mathematics|23|11|10|
|Number Theory|26|14|13|

## Diagnostics

- Failures by stage: {'copy': 7, 'audit': 4, 'student': 2, 'judge_validity': 3}.
- Resolved validity judgments: 47; supplied answer judged correct: 3; verification judged sound: 1; shortcut flags: 3.
- Desired average20–75/100 met: True.
- Rating3 strictly most frequent: True.
- Semantic recoveries / accepted inputs: 2/52. Reviewed grounded recoveries / accepted inputs: 0/52. These are separate from the mean partial-credit score.

These diagnostics are model judgments with explicit missingness, not independently established error rates. The100-source denominator includes gate exclusions; the scored denominator is selected by successful gates and resolved output validation. No score-distribution target was enforced by changing grades or replacing sources.

Paid calls:400; returned usage estimates:$0.52021; missing-usage paid calls:2. Local inference is separate. These are recorded estimates, not a billing reconciliation.

## Interpretation and review

This run freezes a procedure and measures its yield; it does not establish an optimal clue count, a Gaussian distribution, universal judge accuracy, or training transfer. Rejected/uncertain conversions remain in the100-source denominator. Gate disputes and verified counterexamples are in [manual review](manual-review.json). The original dataset labels include invalid sources; use the status-bearing research export or accepted task subset.

## Downloads

- [Full100-source CSV](questions-answers.csv)
- [Full100-source JSONL with ratings and review](questions-answers.jsonl)
- [Readable questions and answers](questions-answers.md)
- [Accepted reconstruction question/answer pairs](reconstruct-qa.jsonl)
- [Accepted public tasks](public-tasks.jsonl)
- [Export guide](EXPORTS.md)
- [Frozen manifest](manifest.json)
- [Raw calls and failures](run.json)

## Concrete findings

- Source28: a valid alternative function supports partial credit, but is not a reformulation of the original function.
- Sources94 and65: the original mathematical question is recovered, but Qwen merely asserts the supplied answer instead of verifying it. Source65 also has an unresolved validity judgment due to a non-verbatim claim quotation.
- Source123: Qwen reverses the required non-perfect-power condition, making the claimed existence false.
- Source78: Qwen changes a constant term into a linear term inside an oscillatory phase, changing the limit from-1 to-sqrt(2)/2.
- Sources49,39,5 and12: copying candidates leave an essential bound unspecified or invent a parameter/target. These are documented weaknesses of the copying gate; their frozen exclusions remain visible.
- Source1: the source itself leaves a2 unconstrained. Two exact rational constructions give different final answers despite the source-aware audit accepting it. It remains excluded.

The automatic input subset is therefore gate-passed research material, not a certified leak-free or universally valid dataset. Assistant case reviews are separate from independent human annotation.
