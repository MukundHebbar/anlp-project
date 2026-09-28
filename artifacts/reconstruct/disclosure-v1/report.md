# Public disclosure calibration

Development controls only; six production boundaries have no frozen binary reference and are excluded from agreement counts. Unresolved outputs remain in the planned denominator.

| Arm | Resolved inputs | Clear-control agreement | Failure records | Revalidated without calls |
|---|---:|---:|---:|---:|
| incumbent | 24/24 | 17/18 | 0 | 0 |
| candidate | 24/24 | 18/18 | 4 | 4 |
| source-aware | 24/24 | 16/18 | 0 | 0 |
| source-aware-p2 | 24/24 | 18/18 | 0 | 0 |

## Production boundaries

| Input | incumbent | candidate | source-aware | source-aware-p2 |
|---|---|---|---|---|
| production-123-k1 | REJECT | ACCEPT | REJECT | ACCEPT |
| production-141-k1 | ACCEPT | REJECT | REJECT | REJECT |
| production-8-k3 | REJECT | REJECT | REJECT | REJECT |
| production-33-k3 | ACCEPT | REJECT | REJECT | REJECT |
| production-112-k3 | ACCEPT | REJECT | REJECT | REJECT |
| production-86-k3 | ACCEPT | REJECT | REJECT | REJECT |

Counts alone do not authorize the D3 sweep. Inspect reasons, public quotes, source-aware exposure, and the direct-copy challenge before accepting exact inputs. A passing public auditor is not proof of non-leakage.

Evidence: [frozen cases](../../../data/manifests/reconstruct-disclosure-development-v1.json), [incumbent raw](incumbent.json), [candidate raw](candidate.json), [per-case comparison](comparison.json).
