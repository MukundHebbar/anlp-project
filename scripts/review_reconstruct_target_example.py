#!/usr/bin/env python3
"""Bind exact mathematical counterexamples to W responses; no judge labels read."""
import json
import sys
from fractions import Fraction
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash,atomic_write_json


def main():
    root=Path('artifacts/reconstruct/target-example-w')
    run=json.loads((root/'student.json').read_text())
    assert len(run['responses'])==16
    vector=[1]*7
    for _ in range(9):
        vector=[(vector[d-1] if d else 0)+(vector[d+1] if d<6 else 0) for d in range(7)]
    exact={'source0_seed1_coefficient_target':str(3*(Fraction(1)+Fraction(4)+Fraction(4,9))),
           'source129_actual_no_equal_adjacent':{'length':10,'count':7*6**9,'remainder_mod2008':(7*6**9)%2008},
           'source129_charitable_difference_one':{'length':10,'count':sum(vector),'remainder_mod2008':sum(vector)%2008}}
    assert exact['source0_seed1_coefficient_target']=='49/3'
    assert exact['source129_actual_no_equal_adjacent']['remainder_mod2008']!=1392
    assert exact['source129_charitable_difference_one']['remainder_mod2008']!=1392
    notes={
      (0,0):'The proposed roots satisfy x^2-(a+b)x+ab=(x-a)(x-b), so alpha^2+beta^2=a^2+b^2. The given second moment therefore forces the requested a^2+b^2 to8/3, not4. The target also changes from3(alpha-beta)^2.',
      (0,1):'The question asks3a^2+3b^2+3c^2, while the justification switches to3(alpha-beta)^2. Take(a,b,c)=(1,-2,2/3), roots1±1/sqrt(3). Their difference is2/sqrt(3) and even the external second-moment clue8/3 holds, but the actual requested coefficient statistic is49/3. Scaling the polynomial changes that statistic while preserving roots. Not grounded or same target.',
      (13,0):'Counts units rather than their product. Literally integers less than24 include infinitely many negative units; under the charitable positive domain there are8 and the requested remainder is8, not1. The response itself acknowledges the contradiction. Original product operation is missing.',
      (62,0):'For1/(z^2-1), the numerator is constant, with no first-order zero. Its |z|<1 expansion is -sum(z^(2k)), with zero negative powers; its |z|>1 expansion is sum(z^(-2k-2)), with infinitely many negative powers. Neither has exactly one negative term. The stated nearest-singularity computation gives1 rather than the supplied infinity. The outer annulus ambiguity cannot rescue incompatible clues or the changed source function.',
      (80,0):'Merely says P,Q are linear, omitting coefficients. On the positively oriented radius2 circle, P=-y,Q=x gives8*pi by Green, whereas P=x,Q=y gives0. Both satisfy the stated linear-component/curve/method conditions; the integral is not determined. Original integrand is not recovered.',
      (118,0):'Asks the fifth triangular number that is prime. The only prime triangular number is3=T2: for n>=3, Tn=n(n+1)/2 has two factors greater than1. No fifth prime triangular number exists. If interpreted as asking whether T5 is prime, T5=15 is not. Neither reading yields odd witness5 for the source formula.',
      (120,0):'Changes a question about specified prime7 into existence of any prime>3. The decimal repunit R2=11 is prime, so11 is its least prime divisor and the existential answer is Yes, contrary to supplied No. Divisibility by3 only when3 divides n does not establish a universal prohibition.',
      (129,0):'No equal adjacent digits is weaker than adjacent difference exactly1. For the actual length10 question there are7*6^9=70543872 words, remainder824 modulo2008. Even replacing the condition by the displayed difference-one recurrence at length10 does not yield1392. Changes both adjacency constraint and original length12.',
      (137,0):'Sum of degrees4n and handshaking imply E=2n but do not determine n. K5 has n5 and all degrees4; the octahedral graph has n6 and all degrees4. Both simple undirected examples satisfy the proposed premises. Original maximal-planarity and degree3/4/5 groups are omitted.'}
    for i in [13,62,80,118,120,129,137]:notes[(i,1)]=notes[(i,0)]
    rows=[]
    for key,response in run['responses'].items():
        i=response['source_index'];seed=response['sampling']['seed']
        assert response['prompt']=='student_p10_recover_original'
        rows.append({'response_key':key,'source_index':i,'seed':seed,'response_output_hash':stable_hash(response['output']),
                     'evidence_hash':stable_hash(response['public_evidence']),
                     'mathematically_grounded_valid':False,'confirmed_original_recovery':False,
                     'reference_score':None,'reason':notes[(i,seed)]})
    assert len({(r['source_index'],r['seed']) for r in rows})==16
    atomic_write_json(root/'response-math-review.json',{'provenance':'Assistant analytic review with explicit mathematical witnesses; not independent human gold',
        'teacher_judgments_used':False,'responses':16,'confirmed_original_recoveries':0,'mathematically_grounded_valid':0,
        'exact_checks':exact,'rows':rows,'score_policy':'Counterexamples disprove grounded validity and original recovery. They do not adjudicate every0-versus1 rubric distinction; raw teacher scores remain separate.'})
    print(json.dumps({'reviewed_responses':16,'valid_reconstructions':0,'original_recoveries':0,'exact_checks':exact}))


if __name__=='__main__':main()
