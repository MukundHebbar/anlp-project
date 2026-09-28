#!/usr/bin/env python3
"""Freeze W's single positive-example edit and unchanged source cohort, no calls."""
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash,atomic_write_json


def main():
    root=Path('artifacts/reconstruct/target-example-w')
    prompt_path=Path('data/prompts/reconstruct/runtime/convert_p5.md')
    if prompt_path.exists() or (root/'run.json').exists():raise SystemExit('W already frozen')
    old_path=Path('data/prompts/reconstruct/runtime/convert_p4.md')
    old=old_path.read_text()
    head,rest=old.split('Positive example:\n',1)
    _,tail=rest.split('\nNegative example:\n',1)
    example='''Source: A rectangle has perimeter20 and area24. Find its longer side. Answer6. Checked solution: x+y=10, xy=24; x(10-x)=24 gives sides4,6.
Output: {"status":"OK","clues":[{"id":"c1","sentence":"The two side lengths x and y satisfy x+y=10.","fragment":"x+y=10 for the two sides","hidden_support":"Perimeter20 gives2(x+y)=20."},{"id":"c2","sentence":"Expressing area in terms of one side x gives x(10-x).","fragment":"Area=x(10-x)","hidden_support":"Substitute y=10-x in area xy."},{"id":"c3","sentence":"The requested quantity is the longer side length.","fragment":"target: longer side length","hidden_support":"The source asks for the longer side, and the checked solution selects6 from the sides4,6."}],"withheld":"The area24 is absent. The target role is retained. From the supplied longer-side answer6 and the side sum10, infer the other side4 and hence the missing area constraint24. This constructs an essential source premise rather than copying a complete question."}
'''
    new=head+'Positive example:\n'+example+'\nNegative example:\n'+tail
    assert new.split('Positive example:\n')[0]==old.split('Positive example:\n')[0]
    assert new.split('\nNegative example:\n')[1]==old.split('\nNegative example:\n')[1]
    sources=json.loads(Path('artifacts/reconstruct/verified-examples-v/sources.json').read_text())['sources']
    assert sorted(map(int,sources))==[0,13,46,62,63,80,87,96,118,120,129,137]
    review=json.loads(Path('artifacts/reconstruct/verified-examples-v/response-math-review.json').read_text())
    assert review['responses']==32 and review['confirmed_original_recoveries']==0
    root.mkdir(parents=True,exist_ok=True)
    prompt_path.write_text(new)
    (root/'converter-example.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='convert_p4.md',tofile='convert_p5.md')))
    run=dict(sources=sources,partitions={'D1':sorted(map(int,sources))},banks={},audits={},responses={},evaluations={},source_recovery={},failures=[],
        metadata={'protocol':'docs/plans/reconstruct-amendment-w.md','planned_conversion_slots':12,
                  'source_records_hash':stable_hash(sources),'old_prompt_file_hash':stable_hash(old),
                  'new_prompt_file_hash':stable_hash(new),'student_readiness':{'status':'pending','approved_evidence_hashes':{}},
                  'maximum_substudy_cost_usd':.75,'source_population':'D4 reused for development; not held out',
                  'launch_condition':'Finish V judgment accounting before W calls. No model call made by this script.'})
    atomic_write_json(root/'run.json',run)
    print('Frozen one positive-example edit and12 unchanged source records; no W model calls.')


if __name__=='__main__':main()
