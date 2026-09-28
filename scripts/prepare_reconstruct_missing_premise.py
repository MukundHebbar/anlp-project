#!/usr/bin/env python3
"""Freeze AB on the exact AA rich6 public inputs; no model calls."""
import argparse,copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
parser=argparse.ArgumentParser();parser.add_argument('--study-root',type=Path,default=Path('artifacts/reconstruct/missing-premise-ab'));parser.add_argument('--prompt',default='student_p13_infer_missing');parser.add_argument('--protocol',default='docs/plans/reconstruct-amendment-ab.md');args=parser.parse_args()
old=Path('artifacts/reconstruct/richer-exposure-aa');root=args.study_root;root.mkdir(exist_ok=True)
assert not (root/'student.json').exists()
parent=json.loads((old/'student.json').read_text());assert set(parent['metadata']['attempted_jobs'])==set(parent['metadata']['jobs'])
oldrequests=json.loads((old/'student-requests.json').read_text());requests={};prompt_name=args.prompt;prompt=r.load_prompt(prompt_name)
run=copy.deepcopy(parent);run.update(responses={},evaluations={},source_recovery={},failures=[])
for f in ['input-review.json','local-runtime-provenance.json']:(root/f).write_bytes((old/f).read_bytes())
for key,job in oldrequests.items():
 if job['arm']!='rich6':continue
 new=copy.deepcopy(job);new['rendered_prompt']=r.render_template(prompt,{'FINAL_ANSWER':new['public_evidence']['final_answer'],'RENDERED_CLUES':new['public_evidence']['rendered_clues']});new['rendered_input_hash']=r.stable_hash(new['rendered_prompt']);requests[key]=new
assert sorted(j['source_index'] for j in requests.values())==[46,62,129]
run['metadata'].update({'protocol':args.protocol,'jobs':list(requests),'attempted_jobs':[],'requests_hash':r.stable_hash(requests),'student_prompt':prompt_name,'student_prompt_hash':r.stable_hash(prompt),'arms':['rich6'],'parent_root':str(old),'parent_requests_hash':r.stable_hash(oldrequests),'scope':'Adaptive prompt-package diagnostic on same reviewed inputs; no independent confirmation','maximum_substudy_cost_usd':.15})
r.atomic_write_json(root/'student-requests.json',requests);r.atomic_write_json(root/'student.json',run)
print('AB frozen:3 unchanged rich6 inputs; one global prompt/example change')
