#!/usr/bin/env python3
"""Exact development diagnostics for W; no model calls or source-specific repairs."""
import json
from math import factorial
from pathlib import Path

ROOT = Path('artifacts/reconstruct/target-example-w')


def main():
    partitions = [(a, b, 8-a-b) for a in range(1,7)
                  for b in range(a,8-a) if b <= 8-a-b]
    counts = [{'heights': h, 'legal_orders': factorial(8)//
               (factorial(h[0])*factorial(h[1])*factorial(h[2]))}
              for h in partitions]
    assert [r['heights'] for r in counts if r['legal_orders']==560] == [(2,3,3)]
    vector = [1]*7
    totals = {}
    for n in range(1,36):
        if n in (12,35):
            totals[str(n)] = {'total':sum(vector), 'remainder_mod_2008':sum(vector)%2008}
        vector = [(vector[d-1] if d else 0)+(vector[d+1] if d<6 else 0)
                  for d in range(7)]
    assert totals['12']['total']==5408
    assert all(t['remainder_mod_2008']==1392 for t in totals.values())
    orders={str(p):next(k for k in range(1,p) if pow(10,k,p)==1) for p in (7,13)}
    assert set(orders.values())=={6}
    edges=[(u,v) for u in range(6) for v in range(u+1,6) if u//2!=v//2]
    degrees=[sum(u in edge for edge in edges) for u in range(6)]
    assert degrees==[4]*6 and len(edges)==12
    result={
      'scope':'Pre-student W development diagnostics; no claims about population identifiability or Qwen outcomes',
      'source46':{'candidate_domain':'Three positive unordered integer heights summing8; all five partitions enumerated',
                  'enumeration':counts,'unique_matching_height_multiset':[2,3,3],
                  'meaning':'Answer560 and public structural constraints identify missing heights within this explicit finite domain. This does not by itself establish non-disclosure.'},
      'source129':{'recurrence':'v1=(1,1,1,1,1,1,1); next[d]=v[d-1]+v[d+1], zero outside0..6',
                   'exact_totals':totals,'meaning':'Both distinct lengths satisfy public recurrence, initial counts and final remainder. Converter uniqueness claim is false; no unregistered length bound is permitted.'},
      'source120':{'orders_of_10':orders,'proof':'For p=7 or13, p divides R_n iff10^n=1 modp since9 is invertible modp. Thus6 dividesn, so3 divides R_n. Neither prime can be the least divisor. Both primes exceed3 and satisfy the same public clues and No answer.',
                   'meaning':'Prime identity is not fixed by the observations. A valid reconstruction using13 would not preserve the essential source parameter7.'},
      'source137':{'witness':'Octahedral graph K_(2,2,2), with opposite pairs(0,1),(2,3),(4,5)',
                   'edges':edges,'degrees':degrees,'n':6,'e':12,
                   'meaning':'The graph is planar and triangulated, has degree sum4n and handshaking, but lacks equal-sized degree3/4/5 groups. Even adding maximal-planarity does not make aggregate degree data equivalent to the original degree premises.'},
      'source0_caution':'Opposite first-moment signs alone are not proof of semantic inequivalence: simultaneous sign reversal preserves squared difference. Evaluate any actual reconstruction by an explicit premise/target correspondence.',
      'decision_constraint':'These diagnostics explain ambiguity and constrain claims; they do not authorize editing individual clues or count as student successes.'}
    (ROOT/'identifiability-certificates.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# W: exact inverse-inference and ambiguity checks','',
       'These are pre-student development diagnostics, not observed reconstruction successes. All are computed by `scripts/check_reconstruct_w_identifiability.py`.','',
       '- Source46: exhaustive enumeration of the five positive height partitions of8 into3 columns identifies2,3,3 from count560. This is a concrete recoverable missing parameter under a public finite constraint.',
       f"- Source129: length12 gives total{totals['12']['total']}; length35 gives total{totals['35']['total']}. Both leave remainder1392 modulo2008. The converter’s uniqueness claim is false. No length cap may be added after seeing this result.",
       '- Source120: both7 and13 have multiplicative order6 for base10. Either being a repunit divisor forces divisibility by3, so both yield No to the least-prime-divisor question. The missing prime is ambiguous.',
       '- Source137: the six-vertex octahedral graph has all degrees4 and satisfies sum(degrees)=4n. It does not have the original degree3/4/5 groups. Aggregate statistics do not recover those premises even if maximal-planarity is inferred.',
       '- Source0: sign symmetry can preserve the target through reparameterization. Do not confuse nonunique notation with a different essential problem.','',
       'The implications differ: some clues support a constrained inverse calculation; others leave multiple essential premises open. These certificates motivate measuring semantic recovery separately from grounded alternative validity. They do not prove that a particular model cannot guess the original.']
    (ROOT/'identifiability-certificates.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'height_candidates':len(counts),'word_length_counterexample':totals,'prime_orders':orders,'octahedron_degrees':degrees}))


if __name__=='__main__':main()
