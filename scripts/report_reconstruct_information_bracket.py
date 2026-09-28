#!/usr/bin/env python3
"""Compare fixed source families and nested information without selecting responses."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
base=Path('artifacts/reconstruct');roots={'p13_zero':base/'constructive-gate-al','p13_two':base/'inverse-bridges-aw/level2','p14_zero':base/'bridge-low-az','p14_one':base/'bridge-midpoint-ay','p14_two':base/'bridge-composition-ax'}
indices=[5,10,16,54,67,113];data={};inputs={}
for arm,root in roots.items():
 run=json.loads((root/'student.json').read_text());requests=json.loads((root/'student-requests.json').read_text());assert sorted(j['source_index'] for j in requests.values())==indices
 assert r.stable_hash(requests)==run['metadata']['requests_hash']
 assert set(run['metadata']['jobs'])==set(run['metadata']['attempted_jobs'])
 assert set(requests)<=set(run['responses'])|{f['key'] for f in run['failures'] if f['stage']=='student'}
 review=json.loads((root/'response-math-review.json').read_text());reviews={x['source_index']:x for x in review['rows']};inputs[arm]={j['source_index']:j['public_evidence'] for j in requests.values()};rows=[]
 for key,j in requests.items():
  i=j['source_index'];v=run['responses'].get(key);ref=reviews.get(i,{})
  if v and ref:assert ref['response_output_hash']==r.stable_hash(v['output']) and ref['evidence_hash']==v['evidence_hash']
  semantic=[x['output'] for x in run['source_recovery'].values() if x['response_key']==key]
  quality=[x['output'] for x in run['evaluations'].values() if x['response_key']==key]
  if arm in ['p13_two','p14_two']:
   audit=json.loads((base/'inverse-bridges-aw/level2/disclosure.json').read_text());a=[x for k,x in audit['records'].items() if int(k.split(':')[0])==i];disclosure=a[0]['output']['status'] if a else 'missing'
  elif arm=='p14_one':
   audit=json.loads((root/'disclosure.json').read_text());a=[x for k,x in audit['records'].items() if int(k.split(':')[0])==i];disclosure=a[0]['output']['status'] if a else 'missing'
  else:disclosure='ACCEPT'
  rows.append(dict(source_index=i,response_key=key,clue_count=j['public_evidence']['clue_count'],readable=bool(v),manual_meaningful_semantic=ref.get('semantic_equivalent',False),manual_grounded_semantic=ref.get('grounded_semantic_success',False),disclosure=disclosure,teacher_semantic=semantic[0].get('source_recovery') if semantic else None,score_100=25*quality[0]['score'] if quality and quality[0].get('status')=='scored' else None))
 data[arm]={'root':str(root),'planned':len(requests),'readable':sum(x['readable'] for x in rows),'manual_meaningful_semantic':sum(x['manual_meaningful_semantic'] for x in rows),'disclosure_accepted_meaningful_semantic':sum(x['manual_meaningful_semantic'] and x['disclosure']=='ACCEPT' for x in rows),'manual_grounded_on_accepted_inputs':sum(x['manual_grounded_semantic'] and x['disclosure']=='ACCEPT' for x in rows),'teacher_semantic_matches':sum(x['teacher_semantic']==2 for x in rows),'teacher_semantic_missing':sum(x['teacher_semantic'] is None for x in rows),'rows':rows}
for i in indices:
 zero=inputs['p13_zero'][i];assert zero['clues']==inputs['p14_zero'][i]['clues']
 one=inputs['p14_one'][i];two=inputs['p14_two'][i]
 assert one['clues'][:-1]==zero['clues'] and two['clues'][:-2]==zero['clues'] and two['clues'][:-1]==one['clues']
 assert two['clues']==inputs['p13_two'][i]['clues']
 assert len({inputs[arm][i]['final_answer'] for arm in roots})==1
result={'independent_families':6,'original_allocation':16,'arms':data,'limitations':['Adaptive development on six fixed eligible families from a sixteen-source allocation; not fresh confirmation.','Raw semantic matches, non-tautological recovery, mathematical grounding and disclosure eligibility remain separate.','P14 changes instructions/example/output order together; do not attribute its effect to order alone.','The curve is not assumed monotonic; no best-of response selection or per-source exposure policy.','Teacher missing outputs remain missing; manual review is assistant analysis, not independent human gold.','Accepted columns use source disclosure; the final copying gate excludes high-arm67, leaving two verified successes (completion-audit.json).','P13/two teacher semantic checks were not run; its six unavailable labels are not API failures.']}
root=base/'bridge-composition-ax';r.atomic_write_json(root/'bracket-comparison.json',result)
lines=['# Matched information bracket','','| Prompt / added equations | Meaningful semantic /6 | On disclosure-accepted inputs /6 | Analytically grounded, accepted /6 | Teacher semantic matches | Missing semantic judgments |','|---|---:|---:|---:|---:|---:|']
for arm,d in data.items():lines.append(f"| {arm} | {d['manual_meaningful_semantic']}/6 | {d['disclosure_accepted_meaningful_semantic']}/6 | {d['manual_grounded_on_accepted_inputs']}/6 | {d['teacher_semantic_matches']} | {d['teacher_semantic_missing']} |")
lines+=['']+result['limitations'];(root/'bracket-comparison.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
