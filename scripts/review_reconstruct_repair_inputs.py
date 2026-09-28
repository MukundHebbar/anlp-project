#!/usr/bin/env python3
"""Bind independent assistant math checks to ten exact inputs; no safety auto-approval."""
import json
from math import comb
from pathlib import Path
import sympy as s
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash


def main():
    root=Path('artifacts/reconstruct/d3-v2')
    run=json.loads((root/'repair-study.json').read_text())
    manifest=json.loads((root/'repair-copy-manifest.json').read_text())
    a,b,c,x=s.symbols('a b c x',real=True)
    assert s.expand((2*a*a+b*c-(a-b)*(a-c)).subs(c,-a-b))==0
    difference=s.expand(x**3-x-((x-a)**3-(x-a)))
    assert s.expand(difference-a*(3*x*x-3*a*x+a*a-1))==0
    assert s.discriminant(3*x*x-3*a*x+a*a-1,x)==12-3*a*a
    assert 23*(-44)+1==-1011 and 23*(-43)+1>-1000
    assert 1+44*1987==87429
    quadruples=[]
    for aa in range(1,22):
        for bb in range(1,aa):
            X=comb(aa,bb)
            if X not in (7,21):continue
            for cc in range(1,21):
                for dd in range(1,cc):
                    Y=comb(cc,dd)
                    if Y<=X and comb(X,Y)==21 and len({aa,bb,cc,dd})==4:
                        quadruples.append([aa,bb,cc,dd])
    assert len(quadruples)==13
    notes={
      8:'Factorization checked symbolically under a+b+c=0. The other denominator is copied correctly. These are local source observations, not unconditional identities for arbitrary real a,b,c; the reconstructed question must supply suitable constraints and defined fractions.',
      27:'For positive integers n=s^2 m with positive s and squarefree m, sqrt(n)=s sqrt(m). Grouping identical squarefree parts adds positive integer multipliers; a direct m term contributes1. These clues do not state the original range or minimal radical-count target. Domain is interpreted as the source positive-integer radical setting.',
      33:'Differences of continuous functions are continuous. If f>g pointwise on compact[0,1], take a maximizer x0 of g: max f>=f(x0)>g(x0)=max g. Symmetric dominance follows similarly. The equal-maxima premise and universal meeting target remain absent.',
      77:'Exact difference and quadratic discriminant verified symbolically for f=x^3-x. For a nonzero shift with two distinct intersections,0<|a|<2 and root separation sqrt(4-a^2)/sqrt(3). Area is indeed the source target; the curves and integrand remain absent. Nonzero shift follows from two distinct isolated intersections, not from the discriminant alone.',
      86:'For a>0, x>=0 and n>0,1/(1+(x/a)^n) lies in(0,1]. At x<a the powered ratio tends to0; at x>a it diverges, explaining thresholda. The integral family is considered for sufficiently large integers n>1; convergence of the n=1 integral is not claimed. Exact integrand and convergence contributions are not displayed.',
      112:'The interval is exactly the four-digit negative range, and n=23k+1 is equivalent to congruence1. The upper endpoint gives k<=floor(-1001/23)=-44, hence maximum-1011. The maximizing target is not supplied by the public observations; it must not be mistaken for a merely missing asking verb.',
      123:'The source example(2,4,4,...) is eventually constant and has even partial sums4n-2. For a putative perfect power m^k with k>=2, oddm gives odd values and evenm gives multiples of4. All three repaired observations are supported. Separate direct-question disclosure concern remains open; missing construction is not necessarily a missing question element.',
      136:'Pairwise intersection size is45+45-89=1. Each other set meets fixedS once, giving sum d_x=N-1. Under no common element, for any x inS choose a setB not containingx. All d_x+1 sets containingx must meetB at distinct points (otherwise two intersections), so d_x+1<=45 and d_x<=44. N=1987 then contradicts sum d_x<=45*44=1980 versus1986, forcing a common point. The union is1+1987*44=87429. Public clues omit N and the explicit size/union target; the complete proof above is private review material only.',
      141:'Factoring x^3 from each of four factors yields x^12(1+x+...+x^7)^4. Coefficients count bounded ordered quadruples. Exact convolution in p4-coefficient-check.json verifies204 at shifted exponents9 and19; the answer does not uniquely specify an exponent, though complementing all four coordinates supplies a valid counting correspondence.',
      143:'For binom(X,Y)=21, positive relevant pairs are(21,1),(21,20),(7,2),(7,5). For3<=Y<=X-3, X=6 gives20 and X>=7 gives at least35, so no additional pairs. Distinct positive c,d excludeY=1. As1<=b<a, binom(a,b)>=a, giving a<=21; similarly c<=20. Exhaustive enumeration over those justified bounds yields13 ordered quadruples.'
    }
    rows=[]
    for entry in manifest['rows']:
        index=entry['source_index'];bank=run['banks'][entry['bank_key']]
        assert stable_hash(bank['output'])==entry['bank_output_hash']
        rows.append({**entry,'mathematical_support_review':'supported_under_stated_local_domain',
          'review':notes[index],'disclosure_approval':'pending copying and semantic review',
          'source_record_hash':stable_hash(run['sources'][str(index)])})
    output={'provenance':'Assistant mathematical review plus exact symbolic/integer checks, not independent human gold',
        'private_review_only':True,'student_readiness':'not granted by this review',
        'source143_enumeration':{'a_upper_bound':21,'c_upper_bound':20,'count':13,'quadruples':quadruples},
        'rows':rows}
    (root/'repair-input-math-review.json').write_text(json.dumps(output,indent=2)+'\n')
    print(f'Saved {len(rows)} exact-bank mathematical reviews; disclosure remains pending')


if __name__=='__main__':main()
