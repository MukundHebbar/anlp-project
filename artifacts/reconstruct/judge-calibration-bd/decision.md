# BD: all accepted labels pass; one whitespace-only quote rejection

All19 calls completed. Eighteen outputs passed the strict validator and all registered label checks. The explicit tautology now receives M0 and shortcut=true, while concise positive proof cases retain credit.

The remaining output, `valid_inverse_inference`, had the expected M4 and shortcut=false but quoted “A set with m elements has 2^m subsets.” where the response says “A set with m elements has2^m subsets.” The inserted space triggered strict claim-quote validation. Preserve this rejection, the original output and [original validator snapshot](validator-original.py).

BE replays all19 original responses through an explicitly logged whitespace-tolerant mathematical-quote check. Exact question-only quotation remains mandatory for automatic-zero evidence. No new model calls, output edits or score changes are allowed in that replay. See [strict report](report.json), [raw outputs](run.json), and [BE results](../judge-calibration-be/decision.md).
