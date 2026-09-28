#!/usr/bin/env python3
"""Build development-only judge controls with independent executable answer checks.

These small certified families complement, not replace, audits of real generated
DeepMath reconstructions. Related mutations are not independent sources.
"""
import copy
import json
import math
from fractions import Fraction
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def build():
    cases=[]
    def add(family,answer,computed,question,clues,proof):
        assert answer==computed,(family,answer,computed)
        cases.append({'family':family,'answer':answer,'question':question,'clues':clues,'proof':proof,
                      'certificate':{'computed':str(computed),'method':'Python exact arithmetic/enumeration','passed':True}})
    solutions=[n for n in range(1,30) if n*(n-1)//2==15]
    add('pair_inverse',6,solutions[0],
        'Every pair of distinct people at a gathering shakes hands exactly once. There are 15 handshakes. How many people are present?',
        ['Each unordered pair contributes one handshake.','For n people the number of pairs is n(n-1)/2.'],
        'n(n-1)/2=15 gives (n-6)(n+5)=0. The positive solution is n=6, with each unordered pair counted once.')
    def valuation(n,p):
        power,total=p,0
        while power<=n:total+=n//power;power*=p
        return total
    add('factorial_base',48,min(valuation(100,2)//2,valuation(100,3)),
        'How many trailing zeros does 100! have in base 12?',
        ['The exponent of 2 in the factorial is 97.','The exponent of 3 is 48.','Each base factor requires two factors of 2 and one of 3.'],
        'Since 12=2^2*3, the required count is min(floor(v2(100!)/2),v3(100!))=min(floor(97/2),48)=48.')
    add('quadratic_minimum',5,14-3**2,
        'Find the minimum of x^2-6x+14 over real x.',
        ['Completing the square produces a square centered at x=3.','The square term is nonnegative and can vanish.'],
        'x^2-6x+14=(x-3)^2+5. The square is nonnegative and is zero at x=3, so the attained minimum is 5.')
    add('lattice_paths',35,math.comb(7,3),
        'How many paths go from (0,0) to (3,4) using only unit steps right or up?',
        ['There are seven steps in total.','Choosing the positions of the three right steps determines the path.'],
        'Every path has three right and four up steps. Choosing the three right-step positions among seven gives binomial(7,3)=35.')
    solutions=[x for x in range(30) if x%5==2 and x%6==3]
    add('congruence',27,solutions[0],
        'Find the integer x with 0<=x<30, x congruent to 2 modulo 5, and x congruent to 3 modulo 6.',
        ['Writing x=2+5k converts the second congruence to k congruent to 5 modulo 6.','The moduli are coprime.'],
        '2+5k is congruent to 3 modulo 6, so -k is congruent to 1 and k to 5 modulo 6. Hence x is congruent to 27 modulo 30; coprimality gives one solution in the specified interval, namely 27.')
    add('geometric_sum',255,sum(2**j for j in range(8)),
        'Evaluate the sum 1+2+4+...+128.',
        ['Multiplying the sum by two shifts all powers by one place.','Subtracting cancels every middle power.'],
        'Let S=1+2+...+128. Then 2S=2+4+...+256. Subtracting cancels the middle powers and gives S=256-1=255.')
    total=sum((Fraction(1,k*(k+1)) for k in range(1,10)),Fraction())
    add('telescoping_rational',Fraction(9,10),total,
        'Evaluate the sum of 1/[k(k+1)] for integer k from 1 through 9.',
        ['Each summand can be written as 1/k-1/(k+1).','All interior fractions cancel.'],
        'Since 1/[k(k+1)]=1/k-1/(k+1), the sum telescopes to 1-1/10=9/10.')
    count=sum(a+b+c==6 for a in range(7) for b in range(7) for c in range(7))
    add('stars_bars',28,count,
        'How many ordered triples of nonnegative integers (a,b,c) satisfy a+b+c=6?',
        ['Six identical objects are separated into three groups.','Two separators can occupy any two of eight positions.'],
        'A string with six objects and two separators specifies the ordered group sizes, including empty groups. Choose the two separator positions among eight: binomial(8,2)=28.')
    counts=[sum(all(not (mask>>i&1 and mask>>(i+1)&1) for i in range(n-1)) for mask in range(1<<n)) for n in range(8)]
    add('path_independent_sets',34,counts[7],
        'How many subsets of seven positions in a row contain no adjacent positions, including the empty subset?',
        ['Including the last position excludes its neighbor.','The endpoint cases contribute 21 and 13.'],
        'With F(0)=1 and F(1)=2, split on the last position to get F(n)=F(n-1)+F(n-2). Thus F(5)=13, F(6)=21 and F(7)=21+13=34. The first term counts excluding the last position; the second counts including it and excluding its neighbor.')
    add('divisor_sum',56,sum(d for d in range(1,29) if 28%d==0),
        'What is the sum of all positive divisors of 28?',
        ['The prime factorization has a squared factor 2 and a single factor 7.','Choosing the prime exponents independently factors the divisor sum.'],
        '28=2^2*7. Every divisor is 2^a*7^b with 0<=a<=2 and 0<=b<=1, so their sum is (1+2+4)(1+7)=7*8=56.')
    fixtures=[]
    for case in cases:
        for variant in ['valid','wrong_answer','tautology']:
            response={'question':case['question'],'justification':case['proof'],'assumptions':[]}
            supplied=str(case['answer'])
            score=[4]
            if variant=='wrong_answer':
                supplied=str(case['answer']+1);score=[1]
            if variant=='tautology':
                response={'question':f'What is the supplied number {supplied}?',
                          'justification':f'The supplied number is {supplied}.','assumptions':[]};score=[0]
            fixtures.append({'id':f'certified_{case["family"]}_{variant}',
                'family_id':case['family'],'category':variant,'final_answer':supplied,
                'clues':case['clues'],'student_response':response,'acceptable_scores':score,
                'reference':{'provenance':'assistant-authored plus independently executed exact calculation',
                    'expected_question_answer':str(case['answer']), 'certificate':case['certificate'],
                    'derivation':case['proof'],'human_reviewed':False,
                    'label_reason':'Certified true answer; supplied answer is increased by one for the negative control.' if variant!='tautology' else 'The question copies the answer and does not use the mathematical observations.'}})
    old=json.loads((ROOT/'data/manifests/reconstruct-judge-fixtures.json').read_text())['fixtures']
    for fixture in old:
        item=copy.deepcopy(fixture);item['family_id']='historical_'+item['id']
        item['reference']={'provenance':'historical authored fixture; not independently machine-certified','human_reviewed':False}
        fixtures.append(item)
    return {'schema':'reconstruct_judge_fixtures_v1','split_role':'development_only',
        'limitations':'30 new cases come from 10 families. Historical fixtures may also be related. Do not treat all cases as independent or as a held-out near-perfect-accuracy study.',
        'fixtures':fixtures}


if __name__=='__main__':
    result=build();out=ROOT/'data/manifests/reconstruct-judge-development-v2.json'
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(f'Wrote {len(result["fixtures"])} development controls; 10 new families have executed answer checks.')
