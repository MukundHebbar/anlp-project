#!/usr/bin/env python3
import argparse,copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
p=argparse.ArgumentParser();p.add_argument('--level',type=int,choices=[1,2],required=True);a=p.parse_args()
base=Path('artifacts/reconstruct/target-cues-av');root=base/f'level{a.level}';root.mkdir(exist_ok=True);assert not(root/'student.json').exists()
cues=json.loads((base/'conversion.json').read_text());assert len(cues['records'])==7
parent=json.loads(Path('artifacts/reconstruct/target-prefix-ap/student.json').read_text());old=json.loads(Path('artifacts/reconstruct/target-prefix-ap/student-requests.json').read_text())
review={'protocol':'docs/plans/reconstruct-amendment-av.md','reviewer':'Assistant pre-student analytic review; independent teacher disclosure check pending','rows':[]}
run=copy.deepcopy(parent);run.update(responses={},evaluations={},source_recovery={},failures=[]);requests={};prompt=r.load_prompt('student_p13_infer_missing')
for oldjob in old.values():
 i=oldjob['source_index'];c=cues['records'][str(i)]['output'];sentences=oldjob['public_evidence']['clues']+[c['target_family_cue']]+([c['method_cue']] if a.level==2 else [])
 ev=r.public_evidence(parent['sources'][str(i)]['final_answer'],[{'id':f'c{n+1}','sentence':s} for n,s in enumerate(sentences)],'sentence');ev['selection_policy']=f'AV_level{a.level}'
 text=r.render_template(prompt,{'FINAL_ANSWER':ev['final_answer'],'RENDERED_CLUES':ev['rendered_clues']});key=f'{i}:level{a.level}:0'
 requests[key]=dict(source_index=i,arm=f'level{a.level}',bank_key=oldjob['bank_key'],public_evidence=ev,evidence_hash=r.stable_hash(ev),rendered_prompt=text,rendered_input_hash=r.stable_hash(text))
 missing={21:'Which residue property is counted; totient suggests but does not state generators.',35:'Exact regularity property and its quantifier distinction.',54:'Exact extremal expression tan squared; slopes/discriminant suggest a method but do not state the target.',68:'Exact event, in particular determinant equal to minus one.',113:'Normalization by n, which is absent from the input.',114:'Exact convergence quantity, rather than coefficient growth or boundary behavior.',132:'Minimum guaranteeing hand versus largest avoiding hand; no threshold value or full construction is supplied.'}[i]
 review['rows'].append(dict(source_index=i,evidence_hash=r.stable_hash(ev),support_pass=True,manual_candidate_pass=True,missing_essential_element=missing,reason='Source supports coarse question family and named method. Complete target and final derivation remain absent. This is provisional manual review, not a teacher acceptance.'))
run['metadata'].update(protocol=review['protocol'],jobs=list(requests),attempted_jobs=[],arms=[f'level{a.level}'],student_seed=0,maximum_substudy_cost_usd=.20,input_review_hash=r.stable_hash(review),requests_hash=r.stable_hash(requests))
r.atomic_write_json(root/'input-review.json',review);r.atomic_write_json(root/'student-requests.json',requests);r.atomic_write_json(root/'student.json',run)
(root/'local-runtime-provenance.json').write_bytes(Path('artifacts/reconstruct/target-prefix-ap/local-runtime-provenance.json').read_bytes())
print('Frozen',len(requests),'inputs, level',a.level)
