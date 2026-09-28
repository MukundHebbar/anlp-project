#!/usr/bin/env python3
"""Freeze S/T responses for a separate p3 rescore only after U controls pass."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project.reconstruct import stable_hash, load_prompt


def main():
    root=Path('artifacts/reconstruct/inference-u')
    comparison=json.loads((root/'comparison.json').read_text())
    if comparison['decision']!='passes_development_gate':
        raise SystemExit('Calibration has not passed; no production rescore permitted')
    destination=root/'production-rescore.json'
    if destination.exists():
        raise SystemExit('Refusing to overwrite frozen rescore')
    run=dict(sources={},partitions={'D1':[]},banks={},responses={},evaluations={},failures=[],
             metadata={'protocol':'docs/plans/reconstruct-amendment-u.md',
                       'comparison_hash':stable_hash(comparison),'prompt':'evaluate_p3',
                       'prompt_hash':stable_hash(load_prompt('evaluate_p3')),
                       'planned_calls':25,'maximum_cost_usd':.20,'response_provenance':{},
                       'note':'No new student draws; no edits to historical p2 artifacts. Semantic labels are unchanged.'})
    for name in ['repaired-student.json','stronger-feasibility.json']:
        path=Path('artifacts/reconstruct/d3-v2')/name
        original=json.loads(path.read_text())
        for key,response in original['responses'].items():
            assert key not in run['responses']
            run['responses'][key]=response
            index=response['source_index']
            source=original['sources'][str(index)]
            assert str(index) not in run['sources'] or run['sources'][str(index)]==source
            run['sources'][str(index)]=source
            run['metadata']['response_provenance'][key]={'artifact':str(path),'response_hash':stable_hash(response)}
    assert len(run['responses'])==25
    run['partitions']['D1']=sorted(map(int,run['sources']))
    destination.write_text(json.dumps(run,indent=2,ensure_ascii=False)+'\n')
    print('Frozen 25 existing responses: 17 Qwen and 8 stronger-model responses; no new student generation.')


if __name__=='__main__': main()
