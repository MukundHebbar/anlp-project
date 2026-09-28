#!/usr/bin/env python3
"""Independent analytic/finite checks of all frozen V outputs; no judge reads."""
import json
import math
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash


def planar_counterexample():
    # Two pentagonal rings triangulate an annulus, capped by vertices10 and11.
    # This explicitly embeds a degree-five triangulation on the sphere.
    faces=[]
    for i in range(5):
        j=(i+1)%5;previous=(i-1)%5
        faces += [(10,i,j),(i,j,5+i),(i,5+previous,5+i),(11,5+i,5+j)]
    flips=[]
    for u,v in [(10,0),(11,5)]:
        adjacent=[f for f in faces if u in f and v in f]
        assert len(adjacent)==2
        a,b=[next(w for w in f if w not in (u,v)) for f in adjacent]
        edges={tuple(sorted((f[i],f[(i+1)%3]))) for f in faces for i in range(3)}
        assert tuple(sorted((a,b))) not in edges
        faces=[f for f in faces if f not in adjacent]+[(a,b,u),(a,b,v)]
        flips.append({'removed_edge':[u,v],'inserted_edge':[a,b]})
    edge_counts=Counter(tuple(sorted((f[i],f[(i+1)%3]))) for f in faces for i in range(3))
    assert set(edge_counts.values())=={2}
    degrees=Counter(v for edge in edge_counts for v in edge)
    assert Counter(degrees.values())=={4:4,5:4,6:4}
    assert len(edge_counts)==3*12-6 and 12-len(edge_counts)+len(faces)==2
    return dict(vertices=12,edges=[list(e) for e in sorted(edge_counts)],faces=faces,flips=flips,
        degrees=dict(degrees),certificate='Two pentagonal rings form a triangulated annulus capped by vertices10 and11. Flipping the two indicated cap edges replaces diagonals of embedded quadrilaterals and preserves a simple sphere triangulation. Thus this is maximal planar, with four vertices of each degree4,5,6. It contradicts uniqueness of n=6 when the three degree values are unspecified.')


def main():
    root=Path('artifacts/reconstruct/verified-examples-v')
    run=json.loads((root/'student.json').read_text())
    assert len(run['responses'])==32
    s=Fraction(2);p=Fraction(2,3)
    cubic=s**3-3*p*s
    assert cubic==4
    interleavings={f'{columns}x{height}':math.factorial(columns*height)//math.factorial(height)**columns
                   for columns,height in [(7,10),(7,7),(7,8),(4,2)]}
    assert interleavings['4x2']==2520 and all(n!=560 for n in interleavings.values())
    # Count the actual 'unequal adjacent digits' words, not the displayed path recurrence.
    counts=[1 if d in [0,6] else 0 for d in range(7)]
    for _ in range(9): counts=[sum(counts)-counts[d] for d in range(7)]
    restricted_end_count=counts[1]+counts[5]
    different_end_count=0
    for start in range(7):
        counts=[int(d==start) for d in range(7)]
        for _ in range(9): counts=[sum(counts)-counts[d] for d in range(7)]
        different_end_count+=sum(counts)-counts[start]
    residues=[1]+[0]*10;divisible_counts=[]
    for _ in range(10):
        next_counts=[0]*11
        for residue,count in enumerate(residues):
            for digit in range(7):next_counts[(10*residue+digit)%11]+=count
        residues=next_counts;divisible_counts.append(residues[0])
    planar=planar_counterexample()
    certificates={'cubic_alternative':str(cubic),'interleavings':interleavings,
        'unequal_adjacent_length10_starts_0or6_ends_1or5':restricted_end_count,
        'unequal_adjacent_length10_different_endpoints':different_end_count,
        'divisible11_digit0to6_counts_by_length':divisible_counts,
        'divisible11_lengths1to10_total':sum(divisible_counts),
        'n12_maximal_planar_counterexample':planar,
        'unit_square_or_cube_integrals_lower_bound':'Every integrand proposed for source96 is >=1 throughout its unit-measure domain (away from a measure-zero singular boundary), so each integral is >=1, not1/12. For the exponential integral the exact value is(e-1)^3>1.'}
    rows=[]
    for key,response in run['responses'].items():
        index=response['source_index'];candidate=response['prompt']=='student_p12_verified_examples';seed=response['sampling']['seed']
        valid=index==0 and candidate
        if index==0:
            reason=('The sum-cubes identity correctly gives4 and substantively uses both clues. This is a valid alternative. The source requests3(alpha-beta)², not alpha³+beta³. Coinciding values after solving the constraints do not by themselves preserve the requested statistic; classify as related, not an exact original recovery.' if candidate else
                    'The requested roots are1±1/sqrt(3), not the supplied scalar4. A correct calculation for another target does not give the required answer.')
        elif index==13:
            reason=('The requested square residue/theorem is directly stated by the first clue. It is a copy-only restatement, not reconstruction of the source product.' if candidate else
                    'With the literal unbounded integer domain a<24 there are infinitely many solutions1-24k. Even under the charitable positive-domain reading there are8, not the supplied1. The target is a count instead of a product.')
        elif index==46:
            dimensions=('7x7' if seed==0 else '4x2') if candidate else ('7x10' if seed==0 else '7x8')
            reason=f"The proposed/assumed equal-height configuration {dimensions} has {interleavings[dimensions]} interleavings, not560. In the4x2 response, equality of column sizes is also not stated in the question. Original heights3,3,2 are never recovered."
        elif index==87:
            reason='The proposed 1/x function is continuous at every1/n; this directly violates the displayed discontinuity clue. Accumulation at0 is not density in a neighborhood. A No answer for continuity at0 cannot establish the original small-o/differentiability theorem or ground the reciprocal-point clue.'
        elif index==96:
            reason=certificates['unit_square_or_cube_integrals_lower_bound']+' None of the proposed ordinary unit-domain integrals restores the source nested asymptotic limit or supports the H(t) clue.'
        elif index==118:
            reason=('The question never defines the associated computation, and its justification returns3 rather than the supplied5. Adding a minimum target does not make the missing relation well-defined.' if candidate else
                    ('The question omits the associated computation. Even granting the assumption that it counts subsets of proper divisors, every prime has proper positive divisor set{1}, with2 subsets, not3. Also3 is T2, not the third triangular number.' if seed==0 else
                     'The question omits the computation. Its assumption T_p=p(p+1)/2 equals3 has p=2 among positive integers, not an odd prime; for5 it gives15. The supplied5 is unsupported.'))
        elif index==129:
            if not candidate:
                count=restricted_end_count if seed==0 else different_end_count
                reason=f"The no-equal-adjacency question has {count} words under its stated endpoint conditions, not1392. Its transition is the sum over all other digits, not only d±1; its extra initial/end restrictions also invalidate the displayed initial counts."
            elif seed==0:
                reason='The question leaves n and d unspecified, yet the answer is a scalar. Forbidding a leading0 gives initial count0 for digit0, contradicting the displayed symmetric initial conditions. No-equal adjacency is not adjacency difference1.'
            else:
                reason=f"Divisibility by11 is an invented constraint. At length1 only digit0 is divisible by11, contradicting the stated initial counts. Counting all digit0..6 words of lengths1..10 with numeric value divisible by11 gives {sum(divisible_counts)}, not1392."
        elif index==137:
            reason=('With6 vertices, handshaking and e=3n-6 give degree sum24, not the supplied6; the model has put the supplied answer into a premise and changed the target.' if candidate else
                    'The degree values are unspecified. Both the source six-vertex construction and the explicit twelve-vertex triangulation certificate have three equally sized degree classes. Thus n=6 is not determined by this question; the missing source degrees are essential.')
        else:raise AssertionError(index)
        rows.append({'response_key':key,'source_index':index,'prompt':response['prompt'],'seed':seed,
            'response_output_hash':stable_hash(response['output']),'evidence_hash':stable_hash(response['public_evidence']),
            'mathematically_grounded_valid':valid,'confirmed_original_recovery':False,
            'review':reason,'score_reference':4 if valid else (0 if index==13 and candidate else None),
            'score_note':'For remaining failures, the review certifies lack of grounded success without forcing every ambiguous0-versus1 boundary into a reference label.'})
    result={'provenance':'assistant analytic review with executable finite/exact certificates; no teacher labels read by this script, not independent human gold',
            'responses':32,'grounded_valid_alternatives':2,'confirmed_original_recoveries':0,
            'certificates':certificates,'rows':rows}
    rpath=root/'response-math-review.json'
    if rpath.exists() and json.loads(rpath.read_text())!=result:raise ValueError('Existing review differs; version explicitly')
    rpath.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'responses':32,'grounded_valid_alternatives':2,'confirmed_original_recoveries':0,
                      'planar_degree_counts':dict(Counter(planar['degrees'].values()))},indent=2))


if __name__=='__main__':main()
