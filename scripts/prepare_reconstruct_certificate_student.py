#!/usr/bin/env python3
"""Freeze AE student requests only after certificate, support, copy and manual review."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
ROOT=Path('artifacts/reconstruct/certificate-adjudication-ae')
assert not (ROOT/'student.json').exists()
manifest=json.loads((ROOT/'manifest.json').read_text());ad=json.loads((ROOT/'run.json').read_text());parent=json.loads((ROOT/'copy-study.json').read_text())
assert r.stable_hash(manifest)==ad['metadata']['manifest_hash']
manual={96:{'passed':True,'reason':'Differentiability and g(0)=0 leave derivative a free. Taylor g(u)=a*u+o(u) yields the limit a/12 for every admissible g, not merely linear examples. The provided1/12 therefore infers a=1. The clues do not contain this derivation or the derivative value. All six statements hold for the original setting, and the missing premise is essential to the question, not merely a solution witness.'}}
rows=[];requests={};prompt_name='student_p13_infer_missing';prompt=r.load_prompt(prompt_name)
for c in manifest['cases']:
 i=c['source_index'];a=ad['audits'].get(str(i));row={'source_index':i,'eligible':False,'bank_hash':c['bank_hash'],'source_hash':c['source_hash']}
 if not a or a['output']['status']!='ACCEPT':row['reason']='Certificate adjudication did not accept; retain exclusion.';rows.append(row);continue
 assert a['bank_output_hash']==c['bank_hash'] and a['source_record_hash']==c['source_hash'] and a['certificate_hash']==r.stable_hash(c['certificate'])
 assert r.stable_hash(parent['banks'][c['bank_key']]['output'])==c['bank_hash']
 audits=[v for v in parent['audits'].values() if v['bank_key']==c['bank_key']]
 for name in ['audit_support_p1','audit_source_disclosure_p4']:
  record=next(x for x in audits if x['prompt']==name)
  assert record['output']['status']=='ACCEPT' and record['bank_output_hash']==c['bank_hash'] and record['source_record_hash']==c['source_hash']
 copies=[v for v in parent['copy_challenges'].values() if v['bank_key']==c['bank_key']];assert len(copies)==1
 cp=copies[0];expected={'FINAL_ANSWER':c['source']['final_answer'],'PUBLIC_BANK':{'role_cue_id':c['bank']['output'].get('role_cue_id'),'clues':[{'id':v['id'],'sentence':v['sentence']} for v in c['bank']['output']['clues']]}}
 assert cp['public_input']==expected and cp['public_input_hash']==r.stable_hash(expected) and cp['output']['status']=='no_direct_reconstruction'
 assert manual[i]['passed']
 row.update(eligible=True,reason=manual[i]['reason'],copy_hash=r.stable_hash(cp['output']),adjudication_hash=r.stable_hash(a),policy='AE explicit mathematical adjudication; original public REJECT retained and not overwritten');rows.append(row)
 evidence=r.public_evidence(c['source']['final_answer'],c['bank']['output']['clues'],'sentence');evidence.update(selection_policy='frozen_AA_rich6',disclosure='medium')
 text=r.render_template(prompt,{'FINAL_ANSWER':evidence['final_answer'],'RENDERED_CLUES':evidence['rendered_clues']});key=f'{i}:rich6:0'
 requests[key]={'source_index':i,'arm':'rich6','bank_key':c['bank_key'],'public_evidence':evidence,'evidence_hash':r.stable_hash(evidence),'rendered_prompt':text,'rendered_input_hash':r.stable_hash(text)}
assert list(requests)==['96:rich6:0']
review={'rows':rows,'reviewer':'Assistant analytic review, not human gold','protocol':manifest['protocol']};r.atomic_write_json(ROOT/'input-review.json',review)
runtime=json.loads(Path('artifacts/reconstruct/missing-premise-ab/local-runtime-provenance.json').read_text());assert Path('/proc/749542/cmdline').read_bytes().decode().split('\0')[:-1]==runtime['command_line'];runtime['checked_for']='AE live command unchanged';runtime['checked_at']=r.utc_now();r.atomic_write_json(ROOT/'local-runtime-provenance.json',runtime)
run=copy.deepcopy(parent);run.update(responses={},evaluations={},source_recovery={},failures=[])
run['metadata'].update(protocol=manifest['protocol'],jobs=list(requests),attempted_jobs=[],requests_hash=r.stable_hash(requests),student_prompt=prompt_name,student_prompt_hash=r.stable_hash(prompt),arms=['rich6'],input_review_hash=r.stable_hash(review),runtime_hash=r.stable_hash(runtime),original_denominator=12,maximum_substudy_cost_usd=.15,certificate_adjudication_hash=r.stable_hash(ad),required_math_verifier='verify_math_p1',scope='Newly eligible input after explicit certificate review; do not retroactively change AA.')
r.atomic_write_json(ROOT/'student-requests.json',requests);r.atomic_write_json(ROOT/'student.json',run);print('Frozen one newly eligible AE request, unchanged six public sentences; source137 remains excluded')
