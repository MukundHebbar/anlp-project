#!/usr/bin/env python3
"""Describe scored-draw variability without treating repeated sources as independent."""
import json,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
root=Path('artifacts/reconstruct/student-variance-as');manifest=json.loads((root/'manifest.json').read_text());indices=manifest['source_indices'];paths=[Path(manifest['baseline_root']),root/'seed1',root/'seed2'];rows=[];reference={}
for seed,path in enumerate(paths):
 s=json.loads((path/'student.json').read_text());requests=json.loads((path/'student-requests.json').read_text());assert r.stable_hash(requests)==s['metadata']['requests_hash']
 assert set(s['metadata']['jobs'])==set(s['metadata']['attempted_jobs'])
 terminal=set(s['responses'])|{f['key'] for f in s['failures'] if f['stage']=='student'};assert set(s['metadata']['jobs'])<=terminal
 assert sorted(j['source_index'] for j in requests.values())==indices
 for key,job in requests.items():
  i=job['source_index'];identity=(job['evidence_hash'],job['rendered_input_hash'])
  if seed==0:reference[i]=identity
  else:assert identity==reference[i]
  v=s['responses'].get(key);score=None
  if v:
   assert v['sampling']['seed']==seed
   es=[e for e in s['evaluations'].values() if e['response_key']==key];assert len(es)<=1
   assert es or any(f['stage']=='evaluate' and f['source_index']==i for f in s['failures']), 'Primary judging still in flight'
   if es and es[0]['output'].get('status')=='scored':score=25*es[0]['output']['score']
  rows.append({'source_index':i,'seed':seed,'response_key':key,'readable':v is not None,'score_100':score,'rating_1_to_5':1+score/25 if score is not None else None})
per_seed={}
for seed in range(3):
 a=[x for x in rows if x['seed']==seed];xs=[x['score_100'] for x in a if x['score_100'] is not None]
 per_seed[str(seed)]={'planned':len(a),'scored':len(xs),'mean':statistics.mean(xs) if xs else None,'sample_variance':statistics.variance(xs) if len(xs)>1 else None,'histogram_1_to_5':[sum(x==25*(j-1) for x in xs) for j in range(1,6)],'missing':len(a)-len(xs)}
per_source=[]
for i in indices:
 a=[x for x in rows if x['source_index']==i];xs=[x['score_100'] for x in a if x['score_100'] is not None]
 per_source.append({'source_index':i,'scores_by_seed':[x['score_100'] for x in sorted(a,key=lambda x:x['seed'])],'scored':len(xs),'mean_available':statistics.mean(xs) if xs else None,'within_source_sample_variance':statistics.variance(xs) if len(xs)>1 else None})
xs=[x['score_100'] for x in rows if x['score_100'] is not None];n=len(rows);eligible=[x for x in per_source if x['scored']>=2];df=sum(x['scored']-1 for x in eligible)
result={'protocol':manifest['protocol'],'independent_source_families':len(indices),'planned_draws':n,'scored_draws':len(xs),'per_seed':per_seed,'per_source':per_source,'source_balanced_available_mean':statistics.mean(x['mean_available'] for x in per_source if x['mean_available'] is not None),'all_draw_available_mean':statistics.mean(xs) if xs else None,'all_draw_sample_variance':statistics.variance(xs) if len(xs)>1 else None,'pooled_within_source_variance':sum((x['scored']-1)*x['within_source_sample_variance'] for x in eligible)/df if df else None,'within_source_degrees_of_freedom':df,'complete_three_score_sources':sum(x['scored']==3 for x in per_source),'planned_mean_bounds':[sum(xs)/n,(sum(xs)+100*(n-len(xs)))/n],'rows':rows,'limitations':['Seven families with repeated draws, not21 independent questions.','Within-input score variability includes student sampling and one-off judging; this is not isolated judge repeatability.','Available-score estimates are conditional on missingness; failed draws are retained in planned bounds.','Ordinal rubric variance is descriptive; no best-seed selection, normality claim, or held-out confirmation.']}
r.atomic_write_json(root/'variance.json',result)
lines=['# AS: scored-draw variability','','| Seed | Scored / planned | Mean /100 | Ratings1,2,3,4,5 | Missing |','|---|---:|---:|---|---:|']
for seed,v in per_seed.items():lines.append(f"| {seed} | {v['scored']}/{v['planned']} | {v['mean']} | {v['histogram_1_to_5']} | {v['missing']} |")
lines+=['',f"Pooled within-source sample variance: {result['pooled_within_source_variance']} points squared. Across all available ratings: {result['all_draw_sample_variance']} points squared.",f"Source-balanced available mean: {result['source_balanced_available_mean']}; planned mean bounds: {result['planned_mean_bounds']}.",'']+result['limitations'];(root/'variance.md').write_text('\n'.join(lines)+'\n');print(json.dumps({k:result[k] for k in ['per_seed','pooled_within_source_variance','all_draw_sample_variance','planned_mean_bounds']},indent=2))
