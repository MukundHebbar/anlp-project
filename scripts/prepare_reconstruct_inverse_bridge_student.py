#!/usr/bin/env python3
import argparse,copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
p=argparse.ArgumentParser();p.add_argument('--level',type=int,choices=[1,2],required=True);a=p.parse_args();base=Path('artifacts/reconstruct/inverse-bridges-aw');root=base/f'level{a.level}';root.mkdir(exist_ok=True);assert not(root/'student.json').exists()
converted=json.loads((base/'conversion.json').read_text());assert len(converted['records'])==6,'Wait for all conversions and manual review'
parent=json.loads(Path('artifacts/reconstruct/constructive-gate-al/student.json').read_text());old=json.loads(Path('artifacts/reconstruct/constructive-gate-al/student-requests.json').read_text());review={'protocol':'docs/plans/reconstruct-amendment-aw.md','reviewer':'Assistant pre-student review; high-exposure disclosure checks pending','rows':[]}
run=copy.deepcopy(parent);run.update(responses={},evaluations={},source_recovery={},failures=[]);requests={};prompt=r.load_prompt('student_p13_infer_missing')
for oldjob in old.values():
 i=oldjob['source_index'];extra=converted['records'][str(i)]['output']['bridge_clues'][:a.level];sentences=oldjob['public_evidence']['clues']+extra
 ev=r.public_evidence(parent['sources'][str(i)]['final_answer'],[{'id':f'c{n+1}','sentence':s} for n,s in enumerate(sentences)],'sentence');ev['selection_policy']=f'AW_level{a.level}'
 text=r.render_template(prompt,{'FINAL_ANSWER':ev['final_answer'],'RENDERED_CLUES':ev['rendered_clues']});key=f'{i}:level{a.level}:0'
 requests[key]=dict(source_index=i,arm=f'level{a.level}',bank_key=oldjob['bank_key'],public_evidence=ev,evidence_hash=r.stable_hash(ev),rendered_prompt=text,rendered_input_hash=r.stable_hash(text))
 review['rows'].append(dict(source_index=i,evidence_hash=r.stable_hash(ev),manual_candidate_pass=True,missing_essential_element={5:'minimum cycle threshold t',10:'factorial index n',16:'power k and hence N',54:'modulus R',67:'scalar c',113:'root multiplier alpha'}[i],reason='Symbolic relation does not substitute supplied answer or disclose missing source value. Inversion and question composition remain. High exposure; independent disclosure verdict retained separately.',domain_note={5:'Fixed-k count is applied to qualifying k>=t>50, as specified by the surrounding observations.',54:'A finite positive maximum implies R>1; the max formula is used in this regime.'}.get(i,'')))
run['metadata'].update(protocol=review['protocol'],jobs=list(requests),attempted_jobs=[],arms=[f'level{a.level}'],student_seed=0,student_prompt='student_p13_infer_missing',student_prompt_hash=r.stable_hash(prompt),maximum_substudy_cost_usd=.2,input_review_hash=r.stable_hash(review),requests_hash=r.stable_hash(requests))
r.atomic_write_json(root/'input-review.json',review);r.atomic_write_json(root/'student-requests.json',requests);r.atomic_write_json(root/'student.json',run)
(root/'local-runtime-provenance.json').write_bytes(Path('artifacts/reconstruct/constructive-gate-al/local-runtime-provenance.json').read_bytes())
print('Frozen6 inputs at level',a.level)
