#!/usr/bin/env python3
"""Freeze one public exposure per reviewed family, with no model calls."""
import argparse,copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
p=argparse.ArgumentParser();p.add_argument('--study-root',type=Path,required=True);p.add_argument('--bank-prompt',required=True);p.add_argument('--arm',required=True);a=p.parse_args();root=a.study_root
assert not (root/'student.json').exists()
parent=json.loads((root/'run.json').read_text());review=json.loads((root/'input-review.json').read_text());runtime=json.loads(Path('artifacts/reconstruct/certificate-adjudication-ae/local-runtime-provenance.json').read_text())
assert Path('/proc/749542/cmdline').read_bytes().decode().split('\0')[:-1]==runtime['command_line'];runtime.update(checked_at=r.utc_now(),checked_for=str(root));r.atomic_write_json(root/'local-runtime-provenance.json',runtime)
prompt_name='student_p13_infer_missing';prompt=r.load_prompt(prompt_name);requests={}
for row in sorted(review['rows'],key=lambda v:v['source_index']):
 if not row['eligible']:continue
 i=row['source_index'];key,bank=r.accepted_bank(parent,i,a.bank_prompt)
 assert row['bank_hash']==r.stable_hash(bank['output']) and row['source_hash']==r.stable_hash(parent['sources'][str(i)])
 assert all(row[f] is True for f in ['support_pass','disclosure_pass','copy_pass','manual_content_pass'])
 copies=[v for v in parent['copy_challenges'].values() if v['bank_key']==key];assert len(copies)==1 and r.stable_hash(copies[0]['output'])==row['copy_hash']
 evidence=r.public_evidence(parent['sources'][str(i)]['final_answer'],bank['output']['clues'],'sentence');evidence.update(selection_policy='frozen_'+a.arm,disclosure='medium')
 text=r.render_template(prompt,{'FINAL_ANSWER':evidence['final_answer'],'RENDERED_CLUES':evidence['rendered_clues']});jobid=f'{i}:{a.arm}:0'
 requests[jobid]={'source_index':i,'arm':a.arm,'bank_key':key,'public_evidence':evidence,'evidence_hash':r.stable_hash(evidence),'rendered_prompt':text,'rendered_input_hash':r.stable_hash(text)}
run=copy.deepcopy(parent);run.update(responses={},evaluations={},source_recovery={},failures=[])
run['metadata'].update(jobs=list(requests),attempted_jobs=[],requests_hash=r.stable_hash(requests),student_prompt=prompt_name,student_prompt_hash=r.stable_hash(prompt),arms=[a.arm],input_review_hash=r.stable_hash(review),runtime_hash=r.stable_hash(runtime),original_denominator=len(parent['sources']),required_math_verifier='verify_math_p1')
r.atomic_write_json(root/'student-requests.json',requests);r.atomic_write_json(root/'student.json',run)
print('Frozen',len(requests),'requests:',list(requests),flush=True)
