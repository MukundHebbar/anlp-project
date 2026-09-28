#!/usr/bin/env python3
"""Separate teacher self-judgments from checked source-blind feasibility witnesses."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import is_grounded_success,stable_hash
from anlp_project.reconstruct_gates import verify_response_bindings


def main():
    root=Path('artifacts/reconstruct/d3-v2')
    run=json.loads((root/'stronger-feasibility.json').read_text())
    review=json.loads((root/'stronger-math-review.json').read_text())
    reviewed={c['response_key']:c for c in review['cases']}
    evaluations={v['response_key']:v for v in run['evaluations'].values()}
    semantics={v['response_key']:v for v in run['source_recovery'].values()}
    failed_first={f['key'] for f in run['failures'] if f['stage']=='student'}
    cases=[]
    for key,response in run['responses'].items():
        e=evaluations.get(key,{});s=semantics.get(key,{})
        checked=reviewed[key]
        assert checked['response_output_hash']==stable_hash(response['output'])
        assert checked['evidence_hash']==response['evidence_hash']
        bound=verify_response_bindings(key,response,e,s,run['sources'][str(response['source_index'])])
        raw_grounded=is_grounded_success(e.get('output',{}))
        cases.append({'source_index':response['source_index'],'response_key':key,
            'score':e.get('output',{}).get('score'),'semantic_score':s.get('output',{}).get('source_recovery'),
            'bindings_verified':bound,'raw_grounded_semantic_success':bool(bound and raw_grounded and s['output']['source_recovery']==2),
            'clear_checked_feasibility_witness':checked['clear_grounded_semantic_witness'],
            'review_status':checked['status'],'first_attempt_response':key not in failed_first})
    result={'scope':'Source-blind feasibility on the same nine p1 inputs; different model/reasoning/compute, not a Qwen release result',
       'planned_families':9,'responses':len(cases),'grounding_judgments':len(evaluations),
       'semantic_judgments':len(semantics),'raw_grounded_semantic_successes':sum(c['raw_grounded_semantic_success'] for c in cases),
       'clear_checked_feasibility_witnesses':sum(c['clear_checked_feasibility_witness'] for c in cases),
       'qualified_equivalence_source':77,'qwen_primary_confirmed_grounded_semantic_successes':0,
       'qwen_primary_eligible_families':9,'review_provenance':review['provenance'],
       'cases':cases,'unresolved_generation_source':143,
       'generation_attempts':len(cases)+sum(f['stage']=='student' for f in run['failures'])}
    (root/'stronger-feasibility-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Same-input stronger-model feasibility','',result['scope'], '',
        f'Planned9 families; {len(cases)} parsed responses. Teacher judges count{result["raw_grounded_semantic_successes"]} grounded source recoveries. Assistant mathematical review verifies5 clear witnesses, with a sixth shear/domain formulation kept qualified. All five clear witnesses came from their first generation call. Qwen primary seed0 recovered0 originals on these same9 inputs.', '',
        '| Source | Raw score | Raw semantic label | Independent assistant review |',
        '|---|---:|---:|---|']
    for c in sorted(cases,key=lambda c:c['source_index']):
        lines.append(f'| {c["source_index"]} | {c["score"]} | {c["semantic_score"]} | {c["review_status"]} |')
    lines+=['', 'Source143 produced no visible response on either permitted attempt. Source136 is a wrong maximum claim: an exact incidence-divisibility obstruction refutes attainability. Source33 is a different lemma, not original recovery, and its direct copying raises a separate scoring-contract concern.', '',
        'This establishes concrete feasibility for several inputs, not general learnability, an isolated thinking effect, near-perfect teacher accuracy, or the required Qwen5/25 result. Model size, reasoning and effective compute differ; the source-disjoint confirmation set remains untouched.', '',
        'Evidence: [raw requests and results](stronger-feasibility.json), [case-level analysis](stronger-feasibility-analysis.json), [mathematical review](stronger-math-review.json), [set-bound obstruction](stronger-set-bound-counterexample.json), [radical equivalence and reference](stronger-radical-equivalence.md), [preregistration](../../../docs/plans/reconstruct-amendment-t.md).']
    (root/'stronger-feasibility-report.md').write_text('\n'.join(lines)+'\n')
    print('Saved stronger-model report with raw versus independently checked counts')


if __name__=='__main__':main()
