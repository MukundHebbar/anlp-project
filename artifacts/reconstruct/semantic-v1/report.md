# Semantic calibration: development controls

| Prompt | Resolved | Three-way agreement | Same/not-same agreement |
|---|---:|---:|---:|
| incumbent | 24/24 | 24/24 | 24/24 |
| candidate | 24/24 | 23/24 | 24/24 |

These are24 authored cases from8 families, not24 independent validation families. The candidate disagrees only on graph-1: it labels the change from labelled spanning trees to unlabelled trees as different(0), while the reference calls it related(1). Both correctly reject semantic equivalence. Preserve the disagreement; do not alter the reference to improve agreement.

Assistant inspection of all eight candidate equivalence correspondences found the stated mappings valid: polynomial factorization, ordered dice outcomes, tangent slope, congruence/divisibility, definite integral/signed area, labelled trees, geometric recurrence, and algebraic rewriting of a universal inequality. This is assistant review, not human adjudication or independent final gold.

Decision: the added schema is usable for development because it makes semantic checks inspectable. No accuracy gain is established; the incumbent has higher three-way agreement on these controls. Before promotion, test production-derived boundary cases and independent families. The5/25 Qwen recovery gate has not been evaluated by this calibration.

Evidence: [frozen references](../../../data/manifests/reconstruct-semantic-development-v1.json), [incumbent raw](incumbent.json), [candidate raw](candidate.json), [counts](comparison.json).
