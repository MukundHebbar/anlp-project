#!/usr/bin/env python3
"""Reproduce pre-inference D3 source checks and explicit answer normalization."""
import itertools
import json
import math
from pathlib import Path
from anlp_project.reconstruct_sources import normalize_option_answer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/reconstruct/followup-v2'


def main():
    run = json.loads((OUT / 'run.json').read_text())
    allocation = json.loads((ROOT / 'data/manifests/reconstruct-reserve-allocation-v1.json').read_text())
    ids = allocation['partitions']['D3']
    sources = {str(i): normalize_option_answer(run['sources'][str(i)]) for i in ids}
    checks = {
        8: 'When denominators are nonzero, 2a^2+bc=(a-b)(a-c) using a+b+c=0. The common-denominator numerator a^2(b-c)-b^2(a-c)+c^2(a-b) equals (a-b)(a-c)(b-c), so the value is1. Undefined inputs must not be asserted valid.',
        20: 'The wording allows the reading that x is any seventh root, including1. That gives six terms1/2 and sum3, whereas the checked solution assumes x is primitive and gives-4. Reuse of r as root parameter and summation index introduces another interpretation. The primitive-root solution is valid, but the original domain is unresolved; do not silently add x!=1.',
        27: 'Combine each square root as an integer multiple of its squarefree part. Every squarefree integer2..100 contributes a positive coefficient. The count is60. Minimality uses the standard linear independence over Q of distinct squarefree radicals; the executable check certifies the count, not that algebraic lemma.',
        33: 'At a maximum point of f, f-g>=0; at a maximum point of g, f-g<=0. Continuity and the intermediate value theorem give a zero, including either endpoint equality. Answer Yes.',
        77: 'Put u=x-a/2. The curve difference is a[3u^2+a^2/4-1]. Two distinct intersections require0<|a|<2. Integrating the absolute difference between roots gives area 4|a|/(3sqrt(3))*(1-a^2/4)^(3/2). With b=a^2/4, its square is proportional to b(1-b)^3, whose interior derivative vanishes at b=1/4 and whose boundary values are0. Thus |a|=1 and maximum area1/2.',
        86: 'Substitute x=ay. For n>=2 the integrand is at most1 on[0,1] and at most y^-2 on[1,infinity). These form an integrable dominator. Pointwise except y=1 it tends to the indicator of[0,1); dominated convergence gives integral a.',
        112: 'Enumerate integers from-9999 through-1000 inclusive and take the largest satisfying n mod23=1. This exhausts the stated four-digit negative domain.',
        122: 'Let s=m+n and D=m^2-mn+n^2+1. D mod3=s^2+1 mod3 is nonzero. The first divisibility implies gcd(D,s!)=1, so every prime factor of D exceeds s. Since 1<D=s^2-3mn+1<s^2, D cannot be composite; write D=p prime>s. The identity m^3+n^3=s(D-1) and Fermat give 3^(m^3+n^3)=1 modp. The second divisibility forces p|s+1, hence p=s+1. Then3mn=s(s-1), and mn<=s^2/4 forces s<=4. Checking positive sums2,3,4 leaves (m,n)=(2,2), D=5; both original divisibilities hold.',
        123: 'Take a_1=2 and a_n=4 for n>=2. Each prefix sum4n-2 is2 mod4. An odd-base perfect power is odd; an even-base power with exponent>=2 is0 mod4. Neither can equal a prefix sum. Answer Yes under the usual exponent>=2 definition.',
        136: 'Pairwise intersections have size45+45-89=1. Fix a set A; its45 points partition the other1986 sets according to their intersection with A. Some point belongs to at least45 other sets. Those45 sets intersect pairwise only at that point. A set omitting it would need45 distinct points to meet them plus its intersection with A, exceeding size45. Thus all sets share that one point, their remaining44 elements are disjoint, and the union has1+1987*44=87429 elements. Option A is normalized to this value.',
        141: 'The coefficient counts ordered four-tuples of exponents from3..10 with sum21. Exhaustive enumeration of8^4 tuples gives204.',
        143: 'Write N=C(a,b), K=C(c,d). Since C(N,K)=21>1, 1<=K<N, so C(N,K)>=N and N<=21. Distinct positive a,b imply b<a and N>=a, hence a<=21. Likewise c<=K<=20. Exhaustively enumerate these bounded domains with all four entries distinct; exactly13 quadruples satisfy the equation.'}
    radical_count = sum(all(n % (k*k) for k in range(2,math.isqrt(n)+1)) for n in range(2,101))
    coefficient = sum(sum(x)==21 for x in itertools.product(range(3,11),repeat=4))
    largest = max(n for n in range(-9999,-999) if n%23==1)
    quadruples = []
    for a in range(2,22):
        for b in range(1,a):
            n = math.comb(a,b)
            if n>21:
                continue
            for c in range(2,21):
                for d in range(1,c):
                    k = math.comb(c,d)
                    if len({a,b,c,d})==4 and 1<=k<n and math.comb(n,k)==21:
                        quadruples.append([a,b,c,d])
    assert (radical_count,coefficient,largest,len(quadruples)) == (60,204,-1011,13)
    assert sources['136']['final_answer'] == str(1+1987*44) == '87429'
    report = {'stage':'before any D3 model calls','source_ids':ids,
              'review_provenance':'assistant mathematical derivations and stated executable checks; no independent human review',
              'original_sources_unchanged':True,'eligible_sources':[i for i in ids if i!=20],
              'needs_review_sources':[20],
              'all_source_denominator':12,'eligible_denominator':11,
              'no_performance_based_exclusions':True,
              'certificates':{'squarefree_radical_count':radical_count,'coefficient':coefficient,
                              'largest_negative_integer':largest,'quadruples':quadruples,
                              'root_at_one_counterexample':3},
              'reviews':{str(i):{'status':'needs_review' if i==20 else 'supported_with_stated_domain',
                                 'derivation':checks[i]} for i in ids},
              'answer_normalizations':{i:s['answer_normalization'] for i,s in sources.items() if 'answer_normalization' in s}}
    (OUT / 'd3-source-preflight.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT / 'd3-derived-sources.json').write_text(json.dumps({'sources':sources,'preflight':'d3-source-preflight.json'},indent=2)+'\n')
    print(json.dumps({'eligible':report['eligible_sources'],'needs_review':[20],
                      'normalizations':report['answer_normalizations']},indent=2))


if __name__ == '__main__':
    main()
