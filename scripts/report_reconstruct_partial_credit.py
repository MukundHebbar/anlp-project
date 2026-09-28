#!/usr/bin/env python3
"""Describe PC-v1 distributions without mixing independent and repeated sources."""
import argparse,json,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
from anlp_project.reconstruct_partial_credit import aggregate
parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path('artifacts/reconstruct/partial-credit-ba'));ROOT=parser.parse_args().root
manifest=json.loads((ROOT/'manifest.json').read_text());run=json.loads((ROOT/'run.json').read_text())
assert run['metadata']['manifest_hash']==r.stable_hash(manifest)
failures={x['id']:x for x in run['failures']}
assert set(run['attempted'])==set(run['records'])|set(failures), 'Scoring still running'
inputs={}
for arm,folder in [('zero','bridge-low-az'),('one','bridge-midpoint-ay'),('two','bridge-composition-ax')]:
 source=json.loads(Path('artifacts/reconstruct',folder,'student.json').read_text())
 inputs[arm]=source

def eligibility(arm,index):
 if arm=='zero':return 'accepted'
 folder='bridge-midpoint-ay' if arm=='one' else 'inverse-bridges-aw/level2'
 root=Path('artifacts/reconstruct')/folder
 d=json.loads((root/'disclosure.json').read_text());c=json.loads((root/'copy-challenge.json').read_text())
 dr=next((v['output']['status'] for k,v in d['records'].items() if int(k.split(':')[0])==index),None)
 cr=next((v['output']['status'] for k,v in c['records'].items() if int(k.split(':')[0])==index),None)
 if dr=='REJECT' or cr=='direct_candidate':return 'rejected'
 if dr=='ACCEPT' and cr=='no_direct_reconstruction':return 'accepted'
 return 'unresolved'

rows=[]
for arm in ['zero','one','two']:
 for i in [5,10,16,54,67,113]:
  records={}
  for role in ['fidelity','validity']:
   key=f'{arm}:{i}:{role}';case=next(c for c in manifest['cases'] if c['id']==key)
   v=inputs[arm]['responses'][case['response_key']]
   assert case['response_hash']==r.stable_hash(v['output']) and case['evidence_hash']==v['evidence_hash']
   record=run['records'].get(key)
   if record:assert record['case_hash']==r.stable_hash(case)
   records[role]=record['output'] if record else None
  score=aggregate(**records)
  rows.append(dict(arm=arm,source_index=i,input_status=eligibility(arm,i),**score))

def stats(items):
 scores=[x['score_100'] for x in items if x['score_100'] is not None];hist=[sum(x['rating_1_to_5']==j for x in items) for j in range(1,6)]
 n=len(items);complete=n>0 and len(scores)==n
 return dict(planned=n,scored=len(scores),missing=n-len(scores),mean=statistics.mean(scores) if scores else None,sample_variance=statistics.variance(scores) if len(scores)>1 else None,histogram_1_to_5=hist,middle_heavy_observed=(hist[2]>max(hist[:2]+hist[3:]) and hist[1]>hist[0] and hist[3]>hist[4]) if complete else None,planned_mean_bounds=[sum(x['score_bounds'][0] for x in items)/n,sum(x['score_bounds'][1] for x in items)/n] if n else None)
arms={}
for arm in ['zero','one','two']:
 items=[x for x in rows if x['arm']==arm];arms[arm]={'all_diagnostic':stats(items),'accepted_inputs':stats([x for x in items if x['input_status']=='accepted']),'input_counts':{status:sum(x['input_status']==status for x in items) for status in ['accepted','rejected','unresolved']}}
result={'judge_version':manifest.get('judge_version','partial_credit_v1'),'scoring_version':'RECONSTRUCT-PC-v1','independent_families':6,'responses':18,'arms':arms,'rows':rows,'limitations':['Saved p14 one-gap responses, not new outputs from the proposed PC-v1 converter/student prompt.','Six repeated families, not18 independent questions; no population-shape claim.','Judging failures and unresolved input validity remain explicit; no retries or score tuning.','Raw automated grades require review; no histogram-driven label correction.','Display bands differ from the old0–4 rubric and its plus-one display.']}
r.atomic_write_json(ROOT/'distribution.json',result)
lines=['# PC-v1: observed score distributions','','| Added bridge clues | Input scope | Scored/planned | Mean /100 | Ratings1,2,3,4,5 | Missing |','|---|---|---:|---:|---|---:|']
for arm,d in arms.items():
 for scope in ['all_diagnostic','accepted_inputs']:
  s=d[scope];lines.append(f"| {arm} | {scope} | {s['scored']}/{s['planned']} | {s['mean']} | {s['histogram_1_to_5']} | {s['missing']} |")
lines+=['','The all-diagnostic rows include invalid/unresolved inputs solely to characterize the saved responses; they are not benchmark scores.']+result['limitations']
(ROOT/'distribution.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
