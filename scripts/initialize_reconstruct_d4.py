#!/usr/bin/env python3
"""Initialize fixed D4 conversion after explicit mathematical/family review."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project.reconstruct import stable_hash, load_prompt


def main():
    root=Path('artifacts/reconstruct/verified-examples-v')
    if (root/'run.json').exists(): raise SystemExit('Run already initialized')
    sources=json.loads((root/'sources.json').read_text())['sources']
    preflight=json.loads((root/'source-preflight.json').read_text())
    assert preflight['source_records_hash']==stable_hash(sources)
    parent=json.loads(Path('data/manifests/reconstruct-reserve-allocation-v1.json').read_text())
    earlier=parent['existing_partitions_unchanged']['D1']+parent['existing_partitions_unchanged']['D2']+parent['partitions']['D3']
    original=json.loads(Path('artifacts/reconstruct/followup-v2/run.json').read_text())
    review=dict(provenance='assistant comparison of all12 D4 questions against the36 earlier development questions and both prompt demonstration packages',
        compared_source_question_hashes={str(i):stable_hash(original['sources'][str(i)]['question']) for i in earlier},
        D4_question_hashes={i:stable_hash(s['question']) for i,s in sources.items()},
        near_duplicate_exclusions=[],
        thematic_relationships=[
            'D4 source0 quadrature moments and demonstration8 rational identity both involve low-degree polynomials; objects, premises and requested quantities differ. This is thematic transfer, not a parameter substitution of the same question.',
            'D4 source46 counts interleavings of ordered chains; demonstration141 counts bounded compositions through a generating function. Different constraints and targets; not the same counting template.',
            'D4 source62 Laurent outer radius versus earlier30 local pole order: related complex-series concepts, different functions and targets. D4 source63 lacunary-series convergence is another distinct target structure.',
            'D4 source129 adjacency walks and the incumbent row-subset demonstration share recurrence reasoning but count different objects under different adjacency constraints.',
            'D4 source137 uses degree sum and planar edge formula; U graph fixtures share the degree-sum lemma. U fixtures are evaluator development, not student demonstrations. Do not claim evaluator-concept-disjoint validation.'],
        limitation='Assistant semantic review, not independent adjudication; shared mathematical techniques remain. Fresh source IDs do not imply concept-independent generalization.',
        student_eligibility='All12 proceed to conversion; actual eligibility still requires exact-input disclosure/copy/support reviews.')
    (root/'family-review.json').write_text(json.dumps(review,indent=2,ensure_ascii=False)+'\n')
    run=dict(sources=sources,partitions={'D1':sorted(map(int,sources))},banks={},audits={},responses={},
             evaluations={},source_recovery={},failures=[],
             metadata={'protocol':'docs/plans/reconstruct-amendment-v.md',
                       'source_preflight_hash':stable_hash(preflight),'family_review_hash':stable_hash(review),
                       'convert_prompt_hash':stable_hash(load_prompt('convert_p4')),
                       'planned_conversion_calls':12,'student_readiness':{'status':'pending','approved_evidence_hashes':{}},
                       'substudy_max_cost_usd':.75})
    (root/'run.json').write_text(json.dumps(run,indent=2,ensure_ascii=False)+'\n')
    print('Initialized12 D4 sources; student generation remains blocked pending input review.')


if __name__=='__main__': main()
