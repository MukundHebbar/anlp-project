# D3 converter comparison under matched audit versions

Development data only. The intervention changes the converter prompt package; it does not isolate example count, clue count, or any one wording change. Source20 remains in the12-source coverage denominator.

| Policy | Accepted/original | Accepted/eligible | Eligible with unresolved audits | Coverage upper bound |
|---|---:|---:|---:|---:|
| convert_p2 | 3/12 | 3/11 | 2 | 33.3% |
| convert_p3 | 6/12 | 6/11 | 1 | 58.3% |

| Source | Old clues | New clues | Old support/public/source | New support/public/source |
|---|---:|---:|---|---|
| 8 | 4 | 2 | ACCEPT/REJECT/REJECT | ACCEPT/ACCEPT/ACCEPT |
| 20 | 0 | 0 | unresolved/unresolved/unresolved | unresolved/unresolved/unresolved |
| 27 | 4 | 3 | ACCEPT/REJECT/unresolved | ACCEPT/ACCEPT/ACCEPT |
| 33 | 4 | 2 | ACCEPT/REJECT/REJECT | ACCEPT/ACCEPT/ACCEPT |
| 77 | 4 | 3 | ACCEPT/ACCEPT/ACCEPT | ACCEPT/ACCEPT/ACCEPT |
| 86 | 4 | 3 | ACCEPT/REJECT/REJECT | ACCEPT/REJECT/REJECT |
| 112 | 4 | 2 | ACCEPT/ACCEPT/ACCEPT | ACCEPT/ACCEPT/ACCEPT |
| 122 | 4 | 3 | ACCEPT/REJECT/ACCEPT | ACCEPT/unresolved/ACCEPT |
| 123 | 3 | 2 | ACCEPT/ACCEPT/REJECT | ACCEPT/REJECT/REJECT |
| 136 | 4 | 3 | ACCEPT/ACCEPT/ACCEPT | ACCEPT/ACCEPT/REJECT |
| 141 | 4 | 3 | ACCEPT/REJECT/REJECT | ACCEPT/REJECT/ACCEPT |
| 143 | 4 | 3 | ACCEPT/unresolved/ACCEPT | ACCEPT/ACCEPT/ACCEPT |

These are teacher audit decisions, not independently certified validity. A released bank must also pass the restricted-copy challenge and review. No D3 Qwen recovery score is inferred from converter coverage.

Evidence: [candidate raw](run.json), [incumbent under the same auditors](incumbent-audits.json), [per-source reasons and withheld content](converter-comparison.json), [preregistered intervention](../../../docs/plans/reconstruct-amendment-m.md).
