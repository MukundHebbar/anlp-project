#!/usr/bin/env python3
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
root=Path('artifacts/reconstruct/information-bracket-au');root.mkdir(exist_ok=True)
assert not (root/'student.json').exists()
parent=json.loads(Path('artifacts/reconstruct/target-prefix-ap/student.json').read_text())
banks=json.loads(Path('artifacts/reconstruct/missing-target-an/run.json').read_text())
prompt_name='student_p13_infer_missing';prompt=r.load_prompt(prompt_name)
run=copy.deepcopy(parent);run.update(responses={},evaluations={},source_recovery={},failures=[])
review={'protocol':'docs/plans/reconstruct-amendment-au.md','diagnostic_only':True,'rows':[]}
requests={}
for i in [21,35,54,68,113,114,132]:
 bankkey,bank=next((k,v) for k,v in banks['banks'].items() if v['source_index']==i)
 run['banks'][bankkey]=bank
 clues=bank['output']['clues']
 for arm,exposure in [('ceiling',[{'id':'source','sentence':'Information-ceiling control: the original question is '+run['sources'][str(i)]['question']}]),('full_bank',clues)]:
  evidence=r.public_evidence(run['sources'][str(i)]['final_answer'],exposure,'sentence');evidence['selection_policy']='AU_'+arm
  text=r.render_template(prompt,{'FINAL_ANSWER':evidence['final_answer'],'RENDERED_CLUES':evidence['rendered_clues']})
  key=f'{i}:{arm}:0';requests[key]={'source_index':i,'arm':arm,'bank_key':bankkey,'public_evidence':evidence,'evidence_hash':r.stable_hash(evidence),'rendered_prompt':text,'rendered_input_hash':r.stable_hash(text)}
 review['rows'].append({'source_index':i,'diagnostic_only':True,'full_bank_audit_in':'artifacts/reconstruct/missing-target-an/run.json','ceiling_leaks_original':True})
run['metadata'].update(protocol=review['protocol'],student_prompt=prompt_name,student_prompt_hash=r.stable_hash(prompt),jobs=list(requests),attempted_jobs=[],arms=['ceiling','full_bank'],student_seed=0,original_denominator=16,maximum_substudy_cost_usd=.25,input_review_hash=r.stable_hash(review),requests_hash=r.stable_hash(requests))
r.atomic_write_json(root/'input-review.json',review);r.atomic_write_json(root/'student-requests.json',requests);r.atomic_write_json(root/'student.json',run)
(root/'local-runtime-provenance.json').write_bytes(Path('artifacts/reconstruct/target-prefix-ap/local-runtime-provenance.json').read_bytes())
print('Frozen14 draws; full-question controls are not candidate successes.')
