# D3 converter comparison under matched audit versions

Development data only. The intervention changes the converter prompt package; it does not isolate example count, clue count, or any one wording change. Source20 remains in the12-source coverage denominator.

| Policy | Accepted/original | Accepted/eligible | Eligible with unresolved audits | Coverage upper bound |
|---|---:|---:|---:|---:|
| convert_p3 | 6/12 | 6/11 | 1 | 58.3% |
| convert_p4 | 7/12 | 7/11 | 0 | 58.3% |

| Source | Old clues | New clues | Old support/public/source | New support/public/source |
|---|---:|---:|---|---|
| 8 | 2 | 2 | ACCEPT/ACCEPT/ACCEPT | ACCEPT/REJECT/REJECT |
| 20 | 0 | 0 | unresolved/unresolved/unresolved | unresolved/unresolved/unresolved |
| 27 | 3 | 3 | ACCEPT/ACCEPT/ACCEPT | ACCEPT/ACCEPT/ACCEPT |
| 33 | 2 | 2 | ACCEPT/ACCEPT/ACCEPT | ACCEPT/ACCEPT/ACCEPT |
| 77 | 3 | 4 | ACCEPT/ACCEPT/ACCEPT | ACCEPT/ACCEPT/ACCEPT |
| 86 | 3 | 3 | ACCEPT/REJECT/REJECT | ACCEPT/REJECT/REJECT |
| 112 | 2 | 2 | ACCEPT/ACCEPT/ACCEPT | ACCEPT/ACCEPT/ACCEPT |
| 122 | 3 | 3 | ACCEPT/unresolved/ACCEPT | ACCEPT/REJECT/ACCEPT |
| 123 | 2 | 3 | ACCEPT/REJECT/REJECT | ACCEPT/REJECT/REJECT |
| 136 | 3 | 3 | ACCEPT/ACCEPT/REJECT | ACCEPT/ACCEPT/ACCEPT |
| 141 | 3 | 3 | ACCEPT/REJECT/ACCEPT | ACCEPT/ACCEPT/ACCEPT |
| 143 | 3 | 3 | ACCEPT/ACCEPT/ACCEPT | ACCEPT/ACCEPT/ACCEPT |

These are teacher audit decisions, not independently certified validity. A released bank must also pass the restricted-copy challenge and review. No D3 Qwen recovery score is inferred from converter coverage.

Evidence: [candidate raw](run.json), [incumbent under the same auditors](run.json), [per-source reasons and withheld content](converter-p4-comparison.json), [preregistered intervention](../../../docs/plans/reconstruct-amendment-q.md).
