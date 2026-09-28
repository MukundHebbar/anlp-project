# X: inverse inference versus direct disclosure

| Auditor | Returned /16 | Reference matches /16 | Hard negatives rejected /12 | Missing-premise inversions accepted /4 |
|---|---:|---:|---:|---:|
| audit_public_p4 | 16 | 13 | 12 | 1 |
| audit_source_disclosure_p2 | 16 | 15 | 12 | 3 |
| audit_public_p5 | 16 | 16 | 12 | 4 |
| audit_source_disclosure_p3 | 16 | 16 | 12 | 4 |

| Family / condition | audit_public_p4 | audit_source_disclosure_p2 | audit_public_p5 | audit_source_disclosure_p3 |
|---|---|---|---|---|
| rectangle / full | REJECT | REJECT | REJECT | REJECT |
| rectangle / cosmetic | REJECT | REJECT | REJECT | REJECT |
| rectangle / inverse | ACCEPT | ACCEPT | ACCEPT | ACCEPT |
| rectangle / proof | REJECT | REJECT | REJECT | REJECT |
| linear / full | REJECT | REJECT | REJECT | REJECT |
| linear / cosmetic | REJECT | REJECT | REJECT | REJECT |
| linear / inverse | REJECT | ACCEPT | ACCEPT | ACCEPT |
| linear / proof | REJECT | REJECT | REJECT | REJECT |
| urn / full | REJECT | REJECT | REJECT | REJECT |
| urn / cosmetic | REJECT | REJECT | REJECT | REJECT |
| urn / inverse | REJECT | ACCEPT | ACCEPT | ACCEPT |
| urn / proof | REJECT | REJECT | REJECT | REJECT |
| motion / full | REJECT | REJECT | REJECT | REJECT |
| motion / cosmetic | REJECT | REJECT | REJECT | REJECT |
| motion / inverse | REJECT | REJECT | ACCEPT | ACCEPT |
| motion / proof | REJECT | REJECT | REJECT | REJECT |

No production adoption is authorized by this control report. Inspect exact reasons and validate separate production boundaries before considering a candidate.

- Four authored mathematical families; transformations within a family are correlated.
- Rectangle intentionally overlaps an existing prompt demonstration, testing consistency rather than held-out generalization.
- Agreement is with a proposed operational definition, not independently measured near-perfect accuracy.
- No Qwen score or original-recovery result is produced by this diagnostic.
- Candidate acceptance of inversions cannot override a full-question or full-proof false acceptance.
- Historical W labels and results remain unchanged; these are separate development controls.
