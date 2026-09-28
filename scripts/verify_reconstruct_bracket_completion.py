#!/usr/bin/env python3
"""Audit the immediate recovery goal against immutable inputs and raw verdicts."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
from anlp_project.reconstruct_gates import verify_response_bindings
root=Path('artifacts/reconstruct/bridge-composition-ax');auditroot=Path('artifacts/reconstruct/inverse-bridges-aw/level2')
load=lambda p:json.loads(p.read_text())
run=load(root/'student.json');req=load(root/'student-requests.json');disc=load(auditroot/'disclosure.json');copy=load(auditroot/'copy-challenge.json');math=load(root/'math-verification.json');manual=load(root/'response-math-review.json');cert=load(root/'success-certificates.json');adjud=load(root/'alpha-adjudication.json');manifest=load(root/'alpha-adjudication-manifest.json')
assert r.stable_hash(req)==run['metadata']['requests_hash']
assert len(req)==6 and set(req)==set(run['responses'])==set(run['metadata']['attempted_jobs'])
assert set(disc['attempted'])==set(disc['records']) and set(copy['attempted'])==set(copy['records'])
assert len(math['audits'])+len(math['failures'])==6
checks=adjud['records']['alpha_logic']['output']['checks'];expected={c['id']:c['expected'] for c in manifest['cases']}
assert len(checks)==4 and all(c['valid'] is expected[c['id']] and c.get('proof') for c in checks)
assert adjud['records']['alpha_logic']['rendered_prompt']==manifest['rendered_prompt']
rows=[];scores=[]
for key,response in run['responses'].items():
 i=response['source_index'];eh=response['evidence_hash'];assert eh==r.stable_hash(response['public_evidence'])==req[key]['evidence_hash']
 assert response['model']=='Qwen/Qwen3-4B' and response['sampling']==dict(temperature=.7,top_p=.8,top_k=20,max_tokens=8192,seed=0)
 assert not r.has_generated_thinking(response['request'])
 primary=[v for v in run['evaluations'].values() if v['response_key']==key];semantic=[v for v in run['source_recovery'].values() if v['response_key']==key]
 assert len(primary)==1;score=primary[0]['output']['score'];scores.append(25*score)
 d=next(v for k,v in disc['records'].items() if int(k.split(':')[0])==i);c=next(v for k,v in copy['records'].items() if int(k.split(':')[0])==i)
 assert d['evidence_hash']==c['evidence_hash']==eh
 m=next((v for v in math['audits'].values() if v['response_key']==key),None)
 if m:assert m['evidence_hash']==eh and m['response_output_hash']==r.stable_hash(response['output'])
 review=next(v for v in manual['rows'] if v['source_index']==i);assert review['response_output_hash']==r.stable_hash(response['output'])
 eligible=d['output']['status']=='ACCEPT' and c['output']['status']=='no_direct_reconstruction'
 binding=bool(semantic and verify_response_bindings(key,response,primary[0],semantic[0],run['sources'][str(i)]))
 sem=bool(binding and semantic[0]['output']['source_recovery']==2 and review['semantic_equivalent'])
 grounded=r.is_grounded_success(primary[0]['output'])
 rawmath=bool(m and m['output']['status']=='valid')
 correctedmath=rawmath
 if i==113:
  assert m['output']['status']=='invalid' and m['output']['question_answer_correct'] is True
  falsechecks=[x for x in m['output']['checks'] if x['verdict']=='false'];assert len(falsechecks)==1
  assert 'alpha' in falsechecks[0]['evidence'] or 'α' in falsechecks[0]['evidence']
  assert review['grounded_response_before_disclosure'] is True
  assert next(v for v in cert['cases'] if v['source_index']==113)['response_output_hash']==r.stable_hash(response['output'])
  correctedmath=True
 passed=bool(eligible and sem and grounded and correctedmath and review['grounded_response_before_disclosure'])
 rows.append(dict(source_index=i,source_disclosure=d['output']['status'],copy_status=c['output']['status'],eligible=eligible,semantic=sem,quality_score_100=25*score,raw_math_status=m['output']['status'] if m else 'validation_failure',adjudicated_math_pass=correctedmath,fully_automatic_pass=bool(eligible and sem and grounded and rawmath),verified_recovery=passed,evidence_hash=eh,response_hash=r.stable_hash(response['output'])))
passed=[x['source_index'] for x in rows if x['verified_recovery']];assert passed==[54,113]
result={'objective':'At least2–3 verified semantic recoveries using a controlled richer-information search','achieved':True,'planned_families':6,'disclosure_and_copy_eligible':sum(x['eligible'] for x in rows),'verified_source_indices':passed,'verified_recoveries':len(passed),'fully_automatic_recoveries':sum(x['fully_automatic_pass'] for x in rows),'all_scheduled_rate':len(passed)/6,'conditional_eligible_rate':len(passed)/sum(x['eligible'] for x in rows),'mean_raw_quality_100':sum(scores)/len(scores),'rating_counts_1_to_5':[sum(s==25*k for s in scores) for k in range(5)],'rows':rows,'adjudication':'113 raw mathematical rejection preserved; its sole disputed inverse implication is proved analytically and confirmed by a once-only four-implication independent check. No student regeneration or output edit.','limitations':['Six adaptively reused development families, not independent confirmation.','2/6 counts end-to-end scheduled successes; among three eligible inputs the rate is2/3. Do not confuse these denominators.','The raw fully automatic gate passes only54;113 passes after disclosed adjudication.','Middle-heavy ratings, near-perfect teacher reliability,5/25 confirmation and training transfer are not established.']}
r.atomic_write_json(root/'completion-audit.json',result);print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
