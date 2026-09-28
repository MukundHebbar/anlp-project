#!/usr/bin/env python3
"""Independent assistant checks of stronger-model feasibility, with explicit caveats."""
import json
from pathlib import Path
import sys
import sympy as s
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash


def main():
    root=Path('artifacts/reconstruct/d3-v2')
    run=json.loads((root/'stronger-feasibility.json').read_text())
    a,b,x,u=s.symbols('a b x u',real=True)
    c=-a-b
    rational=a*a/(2*a*a+b*c)+b*b/(2*b*b+c*a)+c*c/(2*c*c+a*b)
    assert s.cancel(rational)==1
    squarefree=[n for n in range(2,101) if s.mobius(n)!=0]
    assert len(squarefree)==60
    assert s.binomial(12,3)-4*s.binomial(4,3)==204
    source_second=(x-a)**3-(x-a)
    generated_second=x**3-3*a*x*x+3*a*a*x-a*(a*a-1)
    assert s.expand(source_second+x-generated_second)==0
    area=u*(4-u*u)**s.Rational(3,2)/(6*s.sqrt(3))
    derivative=2*(1-u*u)*s.sqrt(4-u*u)/(3*s.sqrt(3))
    assert s.simplify(s.diff(area,u)-derivative)==0 and s.simplify(area.subs(u,1))==s.Rational(1,2)
    notes={
        8:('verified_original','The full cyclic expression and zero-sum premise match. Explicit nonzero denominators clarify the source expression domain. Symbolic cancellation verifies1; the supplied interpolation argument grounds both denominator observations.'),
        27:('verified_equivalent_formulation','Removing sqrt(1) changes only the allowed integer constant. Canonical squarefree radicals are linearly independent overQ, so their60 nonzero components give the minimum term count. See stronger-radical-equivalence.md for the explicit correspondence and primary mathematical reference.'),
        33:('different_question','The dominance/maxima theorem is true but differs from the source equal-maxima/meeting theorem. It is also directly assembled from a displayed lemma, illustrating a construction-versus-copy scoring concern; preserve the raw score4.'),
        77:('equivalence_requires_domain_review','Adding x to both original curve ordinates gives the generated curves, an invertible area-preserving shear. Root separation and area are unchanged. For0<|a|<2, area has its maximum1/2 at|a|=1. The generated explicit domain includes0 and±2; these produce no nondegenerate enclosed region. Treating them as zero-area closure points preserves the optimum, but that convention is not explicit in the generated question. Keep this as a qualified equivalence rather than silently declaring every domain check passed.'),
        86:('verified_original_with_minor_proof_omission','The generated integral and positive scale match the source. Its justification identifies the pointwise limit and scaling but omits a tail bound. For n>1 the tail beyonda is at mosta/(n-1); on[0,(1-epsilon)a] the integrand is at least1/(1+(1-epsilon)^n). Together with the upper bound1 on[0,a], this proves limita. This completes the routine omission allowed by score3; it is not claimed to have appeared in the generated text.'),
        112:('verified_original','Greatest and largest are equivalent. Solving -9999<=23k+1<=-1000 yields integerk from-434 to-44; the greatestn is-1011. The response gives the missing extremal target and verifies it.'),
        136:('wrong_answer_and_different_question','The generated set-size-bound/max-family question differs from the original fixed-family/union-size question. Its purported maximum87429 is unattainable: equality requires every point to lie in45 sets, but87429*1987 has remainder3 modulo45. See the separate exact incidence proof.'),
        141:('verified_original','The polynomial and requested exponent21 match. Factoring x^12 leaves coefficientx^9 in(1+x+...+x^7)^4: C(12,3)-4*C(4,3)=220-16=204. Two coordinates cannot simultaneously exceed7 when their sum is9.')}
    cases=[]
    for key,response in run['responses'].items():
        index=response['source_index'];status,note=notes[index]
        cases.append({'response_key':key,'source_index':index,'response_output_hash':stable_hash(response['output']),
          'evidence_hash':response['evidence_hash'],'status':status,'review':note,
          'clear_grounded_semantic_witness':index in [8,27,86,112,141]})
    result={'provenance':'Assistant mathematical review with symbolic/integer checks, not independent human calibration',
       'planned_families':9,'parseable_responses':len(cases),'clear_grounded_semantic_witnesses':5,
       'additional_qualified_equivalence':77,'different_lemma':33,'refuted_maximum':136,
       'no_visible_response_after_two_attempts':143,
       'squarefree_basis_elements':squarefree,'cases':cases,
       'claim_scope':'Feasibility witnesses for these exact inputs and p1 prompt; not a Qwen success, a population recovery rate, or proof of learnability. All five clear witnesses came from the first call for their source.'}
    assert len(cases)==8
    (root/'stronger-math-review.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Five clear grounded semantic witnesses; one qualified shear/domain case; two nonrecoveries')


if __name__=='__main__':main()
