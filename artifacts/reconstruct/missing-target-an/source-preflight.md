# AK source validity review

All sixteen preallocated sources remain in coverage accounting. Fifteen proceed to conversion; source1 is quarantined without replacement. No Qwen outcome was inspected to make these decisions.

Source1 is underdetermined as written: its recurrence applies for k>1, leaving a2 unspecified. With a1=2^2009, choosing a2=2^2009 gives a2011=1, while choosing a2=2^2010 gives a2011=4/3. The checked solution assumes an unstated k=1 recurrence. The source was not silently repaired.

Option labels17 and59 were resolved to their unique explicit answer text, retaining unchanged questions and original-answer provenance. Source67 is interpreted under the inverse-existence presupposition in its wording; source132 asks for the worst-case guarantee from the stated incidence data. These interpretation limits are recorded, not hidden.

| Source | Decision | Analytic basis |
|---|---|---|
| 1 | quarantine | Quarantine: recurrence applies only for k>1 and leaves a2 unspecified. Given a1=2^2009, a2011=[2^2008*(2^-2009+1/a2)]^-1. Choosing a2=2^2009 gives1, but a2=2^2010 gives4/3. The supplied solution silently assumes the missing k1 step. |
| 5 | accept | Disjoint long-cycle cases k51..100; choose cycle members, cyclic order and arbitrary remainder to obtain100!/k per case. Sum gives stated harmonic expression. |
| 10 | accept | Wilson reduction51!*9!=1 mod61; exact factorial remainder27 verified. |
| 16 | accept | Integer coordinate bijection x=a+b,y=b-a with ab=10^6. Ordered signed factor pairs give2*(6+1)^2=98. |
| 17 | accept | For color sizes m_j, each factor(x+m_j)^m_j has linear coefficient equal to its constant coefficient. Product therefore has a1=k*a0. Explicit B answer normalized to its equation; original question and label preserved. |
| 21 | accept | Prime modulus multiplicative group cyclic of order2^m; number of generators phi(2^m)=2^(m-1). |
| 29 | accept | Composite561 is squarefree3*11*17; each prime predecessor divides560. Fermat and CRT verify all integer n, including nonunits. |
| 35 | accept | Bounded derivative and the mean value theorem imply a global Lipschitz bound, hence uniform continuity. |
| 41 | accept | Two differentiated geometric-series identities yield x(1+x)/(1-x)^3 at x1/3, namely3/2. Termwise differentiation is valid inside radius1. |
| 54 | accept | u=(omega-z)/z lies on circle /u+1/=1/10. Tangency/discriminant gives maximum slope squared1/99 and is attainable. |
| 59 | accept | Two distinct nonzero real denominator roots have modulus>1, so numerator is nonzero there and both are simple poles. At0 multiplication by analytic nonzero reciprocal denominator preserves the essential singularity. Explicit D normalized to its option text. |
| 67 | accept | Use the inverse explicitly presupposed by the question. Ae1=ones implies ones^T*A^-1*ones=1. This assumes T inverse exists as stated by its use; T(v1)=sum alone would not establish invertibility. Preserve wording, do not silently add a premise. |
| 68 | accept | Exhaustive enumeration of81 entry matrices leaves two with A^2=-I, both determinant1. Event determinant-1 is impossible under any distribution on eligible matrices, so missing uniformity does not affect zero answer. |
| 113 | accept | Factorial difference telescopes to n!, then integral bounds for log(n!) give nth-root/n limit1/e. |
| 114 | accept | 1<=tau(n^50)<=2*n^25 implies nth-root limit1, hence radius1. |
| 132 | accept | Worst-case guarantee over arrangements satisfying the stated counts: undrawn cards cover24 triples with4 incidences each, requiring at least6 omitted cards for a combination-free hand. Supplied construction certifies tightness at12. This is a universal guarantee from available data, not a claim every individual arrangement has identical minimum. |

[Exact reviewed records](source-preflight.json), [executable preparation/checks](../../../scripts/prepare_reconstruct_fresh_ak.py), [arithmetic certificates](source-checks.json), [frozen allocation](allocation.json), [protocol](../../../docs/plans/reconstruct-amendment-ak.md).

These are assistant analytic checks, not independent human gold. All48 earlier development questions and current demonstrations were compared; no parameter-renamed duplicate was identified, but shared mathematical techniques remain. Conversion suitability and model performance are separate, still unmeasured stages.
