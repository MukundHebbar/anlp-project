#!/usr/bin/env python3
"""Freeze AJ's registered order-only intervention on every exact AH public input."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
old=Path('artifacts/reconstruct/one-gap-ah');root=Path('artifacts/reconstruct/output-order-aj')
assert not (root/'student.json').exists()
parent=json.loads((old/'student.json').read_text());previous=json.loads((old/'student-requests.json').read_text())
assert r.stable_hash(previous)==parent['metadata']['requests_hash']
check=json.loads((root/'prompt-equivalence-check.json').read_text());prompt_name='student_p15_verification_first';prompt=r.load_prompt(prompt_name)
assert check['new_prompt_hash']==r.stable_hash(prompt)
assert check['parent_prompt_hash']==parent['metadata']['student_prompt_hash']
requests={}
for key,job in previous.items():
 new=copy.deepcopy(job);new['arm']='verification_first'
 new['rendered_prompt']=r.render_template(prompt,{'FINAL_ANSWER':new['public_evidence']['final_answer'],'RENDERED_CLUES':new['public_evidence']['rendered_clues']})
 new['rendered_input_hash']=r.stable_hash(new['rendered_prompt'])
 assert new['public_evidence']==job['public_evidence'] and new['evidence_hash']==job['evidence_hash']
 requests[f"{job['source_index']}:verification_first:0"]=new
run=copy.deepcopy(parent);run.update(responses={},evaluations={},source_recovery={},failures=[])
for f in ('input-review.json','local-runtime-provenance.json'):(root/f).write_bytes((old/f).read_bytes())
run['metadata'].update(protocol='docs/plans/reconstruct-amendment-aj.md',jobs=list(requests),attempted_jobs=[],requests_hash=r.stable_hash(requests),student_prompt=prompt_name,student_prompt_hash=r.stable_hash(prompt),arms=['verification_first'],parent_root=str(old),parent_requests_hash=r.stable_hash(previous),maximum_substudy_cost_usd=.25,scope='Paired output-order intervention; exact public evidence unchanged; development only')
r.atomic_write_json(root/'student-requests.json',requests);r.atomic_write_json(root/'student.json',run)
print('AJ frozen:',len(requests),'unchanged public inputs; output field order only')
