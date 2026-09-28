#!/usr/bin/env python3
"""Exact counterexamples and explicit semantic differences for screen S."""
import json
from math import comb
from pathlib import Path
import sys
import sympy as s
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash


def main():
    root=Path('artifacts/reconstruct/d3-v2')
    run=json.loads((root/'repaired-student.json').read_text())
    a,b,c=map(s.Integer,[1,2,-3])
    value=1/(2*a*a+b*c)+1/(2*b*b+c*a)
    assert value==-s.Rational(1,20)
    radical_sum=s.simplify(sum(s.sqrt(n) for n in [18,72,98,32,128]))
    assert radical_sum==28*s.sqrt(2) and radical_sum**2!=60**2
    expanded=s.expand(sum(s.sqrt(n) for n in [2,3,5,7])**3)
    assert len(s.Add.make_args(expanded))==8
    x,t=s.symbols('x t',positive=True)
    area=s.simplify(s.integrate(s.sqrt(3)*x-t*x*x,(x,0,s.sqrt(3)/t)))
    assert area==s.sqrt(3)/(2*t*t)
    assert 23*(-434)+1==-9981 and 23*(-44)+1==-1011
    assert comb(8,3)==56 and comb(7,6)==7
    generic_binomial_count=0
    for aa in range(1,22):
        for bb in range(1,aa):
            X=comb(aa,bb)
            if X not in (7,21):continue
            for cc in range(1,22):
                for dd in range(1,cc):
                    Y=comb(cc,dd)
                    if Y!=1 and Y<=X and len({aa,bb,cc,dd})==4:generic_binomial_count+=1
    assert generic_binomial_count!=13
    notes={
      8:'Both questions replace the original three fractions with a two-term reciprocal sum. For distinct a=1,b=2,c=-3 satisfying sum0, that sum equals-1/20, not1. The question does not recover the original squared numerators or third term; its answer is independently false.',
      27:'Seed0 radical sum simplifies to28sqrt(2), not60. Seed1 expansion has exactly8 distinct simplified radical terms, not60 (or the16 claimed during its justification). The latter repeats the same question after recognizing a mismatch instead of fixing it. Both change the original range/minimal-count question.',
      33:'Both ask the pointwise-dominance/maxima lemma, not the original equal-maxima/meeting theorem. The lemma is true: evaluate f at a maximizer ofg. Premises differ: f=g=0 meets the original equal-maxima premise but not strict dominance, while f=1,g=0 meets the copied premise but not equal maxima. Retain any generic rubric credit separately; this is not original recovery.',
      77:'For a>0, the proposed parabola and line intersect at0 andsqrt(3)/a. Their area is sqrt(3)/(2a^2), unbounded as a→0+, and their separation is not the displayed sqrt(4-a^2)/sqrt(3). At a=1 the area already exceeds1/2. The curves and task differ from the fixed-cubic source.',
      86:'Seed0 leaves the integrand unspecified. The families gamma/(1+(x/a)^n), with gamma=1 or1/2, obey the qualitative bounds/threshold but have limits gamma*a. For n>1 the tail is at most gamma*a/(n-1); on[0,(1-epsilon)a] the integrand is at least gamma/(1+(1-epsilon)^n), proving the limit by squeezing. Seed1 uses f(x/a^n): taking f(u)=exp(-u) gives integral a^n, divergent at a=2, not2. Neither recovers the specified source integrand.',
      112:'Seed0 omits an extremal target: both-1011 and-1034 satisfy its conditions, so they do not determine a unique integer. Seed1 explicitly asks for the smallest, whose value is-9981, not-1011. The original asks for the largest. These are different task specifications even though the supplied answer satisfies the shared congruence.',
      136:'Without a fixed set size there is no finite maximum number of sets. For any N>=3, let S_i be the set of edges incident to vertexi in the complete graph K_N. Any two sets share exactly their connecting edge, no edge is common to all sets, and each d_x=1<=44. All displayed counting observations can hold with arbitrarily largeN. The source instead fixes1987 sets of size45 and asks for union size.',
      141:'The generated coefficient target is x^17 instead of x^21. After factoring x^12, the required sum is5; the upper bound7 is inactive and the coefficient is C(8,3)=56, not204. Seed0 reaches the8192-token cap while repeating that mismatch; no primary format recovery is performed. Seed1 is parseable but retains the wrong exponent.',
      143:f'The original outer equation and essential domain/distinctness restrictions are not supplied as a self-contained question. Even a generous completion requiring distinct positive variables, X in{{7,21}}, 1<Y<=X gives{generic_binomial_count} quadruples, not13. For example(7,1,4,2) has X=7,Y=6 and satisfies those displayed constraints, but its outer binomial is7 rather than21. Without an outer-domain bound the specified conditions may admit infinitely many quadruples. Neither candidate states the original task.'
    }
    rows=[{'response_key':key,'source_index':v['source_index'],'seed':v['sampling']['seed'],
       'response_output_hash':stable_hash(v['output']),'evidence_hash':v['evidence_hash'],
       'review':notes[v['source_index']],'assistant_semantic_equivalence_to_original':False}
       for key,v in run['responses'].items()]
    result={'provenance':'Assistant mathematical review with exact symbolic/integer checks; not independent human judge calibration',
      'scope':'All17 parseable responses, plus separate diagnosis of the primary coefficient truncation. This does not assign or overwrite teacher rubric scores.',
      'exact_checks':{'reciprocal_sum':str(value),'radical_sum':str(radical_sum),'radical_cube':str(expanded),
           'radical_cube_distinct_terms':8,'parabola_line_area':str(area),'coefficient_x17':56,
           'generously_completed_binomial_count':generic_binomial_count},'cases':rows,
      'source141_primary_failure':[{'key':f['key'],'raw_content_hash':stable_hash(f.get('raw',{}).get('content','')),
          'diagnosis':notes[141]} for f in run['failures'] if f['stage']=='student' and f['source_index']==141]}
    assert len(rows)==17
    (root/'repaired-student-math-review.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Saved17 response-bound mathematical/semantic reviews and exact counterexamples')


if __name__=='__main__':main()
