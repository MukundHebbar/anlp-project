# W: exact inverse-inference and ambiguity checks

These are pre-student development diagnostics, not observed reconstruction successes. All are computed by `scripts/check_reconstruct_w_identifiability.py`.

- Source46: exhaustive enumeration of the five positive height partitions of8 into3 columns identifies2,3,3 from count560. This is a concrete recoverable missing parameter under a public finite constraint.
- Source129: length12 gives total5408; length35 gives total7366096384. Both leave remainder1392 modulo2008. The converter’s uniqueness claim is false. No length cap may be added after seeing this result.
- Source120: both7 and13 have multiplicative order6 for base10. Either being a repunit divisor forces divisibility by3, so both yield No to the least-prime-divisor question. The missing prime is ambiguous.
- Source137: the six-vertex octahedral graph has all degrees4 and satisfies sum(degrees)=4n. It does not have the original degree3/4/5 groups. Aggregate statistics do not recover those premises even if maximal-planarity is inferred.
- Source0: sign symmetry can preserve the target through reparameterization. Do not confuse nonunique notation with a different essential problem.

The implications differ: some clues support a constrained inverse calculation; others leave multiple essential premises open. These certificates motivate measuring semantic recovery separately from grounded alternative validity. They do not prove that a particular model cannot guess the original.
