#!/usr/bin/env python3
"""Record D4 source checks before conversion/student calls; C/R remain unused."""
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project.reconstruct import stable_hash


def main():
    root=Path('artifacts/reconstruct/verified-examples-v')
    if (root/'source-preflight.json').exists():
        raise SystemExit('Preflight exists; refusing overwrite')
    allocation=json.loads(Path('data/manifests/reconstruct-d4-allocation-v1.json').read_text())
    frozen=json.loads((root/'freeze.json').read_text())
    assert stable_hash(allocation)==frozen['manifest_hash']
    original=json.loads(Path('artifacts/reconstruct/followup-v2/run.json').read_text())
    sources={str(i):original['sources'][str(i)] for i in allocation['partitions']['D4']}
    reviews={
        0:'Testing 1,x,x² gives 2=2, alpha+beta=2 and alpha²+beta²=8/3. Hence 3(alpha-beta)²=3(16/3-4)=4. Real nodes 1±1/sqrt(3) exist and linearity gives the required identity for all degree<=2 polynomials.',
        13:'Units modulo24 are 1,5,7,11,13,17,19,23. Every unit has square1 modulo24; pair a with24-a, obtaining four products -1. The total is1 modulo24; finite enumeration below independently verifies it.',
        46:'Targets are distinct by position. Each legal order interleaves three fixed chains of lengths3,3,2. Choosing positions gives 8!/(3!3!2!)=560. Both equal-height columns remain distinct.',
        62:'With w=z-pi, the Laurent series is -sin(w)/w²=-1/w+w/6-w³/120+... . Its regular part is entire and its only singular term is -1/w. Convergence annulus is0<|w|<infinity. The supplied infinity is the outer radius; do not assert convergence at the center or confuse with a Taylor radius.',
        63:'For0<r<1 the consecutive absolute term ratio is2*r^(n*n!), tending0. At r>=1 terms do not tend0; at0 all terms vanish. Therefore radius1. The coincident n=0 and n=1 powers change only a finite coefficient.',
        80:'P_y=Q_x=1, so Green integrand is0 and either circle orientation gives0. Equivalently the vector field has potential x²/2+xy-y²/2, so its integral around a closed curve is0.',
        87:'The saved spike counterexample has f(1/n)=1/n³ and is0 elsewhere. Its ratio f(x)/x² is either0 or1/n, tending0. Each1/n is isolated in the spike set, so f is discontinuous there. Every neighborhood of0 contains a spike; no such neighborhood has differentiability everywhere. No claim about f(0) is needed for this counterexample.',
        96:'Differentiability at0 gives g(s²)=s²+o(s²). Integrating yields H(t)=t³/3+o(t³), uniformly bounded by epsilon|t|³ near0. Integrating from x³ to x² gives (x^8-x^12)/12+o(x^8), including negative x by absolute remainder bounds. Sine preserves the leading term, giving1/12.',
        118:'The source asks for an odd integer witness, not all witnesses or a unique one. k=5 gives3=T2, a prime. k=-5 also works. The saved solution restricts its triangular-index proof to nonnegative n and overstates uniqueness of n=2 over all integers. Do not propagate that uniqueness claim; retain the valid explicit witness and record the correction.',
        120:'The order of10 modulo7 is6. Thus7|R_n implies6|n and hence3|n. Since R_n congruent n modulo3, every such repunit has smaller prime factor3. Answer No, in the usual decimal repunit convention.',
        129:'Words permit a leading0. Dynamic programming tracks each ending digit d=0..6, initially one of each; next count is the sum of neighboring ending counts. Eleven transitions give5408 words and remainder1392 modulo2008.',
        137:'Degree sum is4n and2e=6n-12, so n=6. Existence is not inferred solely from the equation: start with K4 on u,v,w1,w2, insert w3 in face(u,v,w2), then w4 in face(u,v,w3). This is maximal planar K2 joined with path(w1,w2,w3,w4), with degrees5,5,3,4,4,3.'}
    units=[n for n in range(1,24) if math.gcd(n,24)==1]
    word_counts=[1]*7
    for _ in range(11): word_counts=[(word_counts[d-1] if d else 0)+(word_counts[d+1] if d<6 else 0) for d in range(7)]
    checks={'moment_value':str(3*(2*Fraction(8,3)-4)),
            'units':units,'unit_product_mod24':math.prod(units)%24,
            'interleavings':math.factorial(8)//(math.factorial(3)**2*math.factorial(2)),
            'order10mod7':next(k for k in range(1,7) if pow(10,k,7)==1),
            'word_end_counts':word_counts,'words':sum(word_counts),'word_remainder':sum(word_counts)%2008,
            'odd_witness_value':(5**2-1)//8,'negative_witness_value':((-5)**2-1)//8,
            'planar_witness_degrees':[5,5,3,4,4,3]}
    assert checks['moment_value']=='4' and checks['unit_product_mod24']==1
    assert checks['interleavings']==560 and checks['order10mod7']==6
    assert checks['words']==5408 and checks['word_remainder']==1392
    # Correct only the derived worked solution, with full original provenance.
    original118=sources['118']['checked_solution']
    sources['118']={**sources['118'],
        'checked_solution':'The question requests one witness. Choose k=5. Then (k²-1)/8=3=2*3/2 is triangular and prime. Also k=-5 works; no uniqueness is claimed.',
        'solution_correction':{'original_solution_hash':stable_hash(original118),
                               'reason':'Avoid unsupported uniqueness over all odd integers; preserve the requested witness and original question.'}}
    review=dict(protocol=allocation['protocol'],manifest_hash=stable_hash(allocation),
        review_provenance='assistant analytic source/solution review plus executable finite checks; not independent human gold',
        eligible_source_ids=allocation['partitions']['D4'],original_family_denominator=12,
        source_records_hash=stable_hash(sources),certificates=checks,
        reviews={str(i):{'status':'supported_with_stated_conventions','derivation':reviews[i]} for i in reviews},
        semantic_family_review='pending before student generation; no claim of source-family independence yet')
    (root/'source-preflight.json').write_text(json.dumps(review,indent=2,ensure_ascii=False)+'\n')
    (root/'sources.json').write_text(json.dumps({'sources':sources},indent=2,ensure_ascii=False)+'\n')
    frozen['source_content_review_started']=True
    (root/'freeze.json').write_text(json.dumps(frozen,indent=2)+'\n')
    print(json.dumps({'sources':len(sources),'checks':checks,'corrected_solution':[118]},indent=2))


if __name__=='__main__': main()
