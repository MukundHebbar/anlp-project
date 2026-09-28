#!/usr/bin/env python3
"""Verify complete cohort/provenance bindings without new model calls."""
import importlib.util,json,hashlib
from pathlib import Path
spec=importlib.util.spec_from_file_location('extension100',Path(__file__).with_name('run_reconstruct_valid100.py'))
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
m=e.m;run=e.Run();s=run.state;manifest=run.manifest
assert s['metadata'].get('terminal') is True,'Run still active'
assert hashlib.sha256((e.ROOT/'calibration-47.jsonl').read_bytes()).hexdigest()==manifest['calibration_file_sha256']
assert hashlib.sha256((e.ROOT/'runner-frozen.py').read_bytes()).hexdigest()==manifest['runner_sha256']
parent=json.loads((e.PARENT/'manifest.json').read_text())
parent_state=json.loads((e.PARENT/'run.json').read_text())
assert parent_state['metadata']['manifest_hash']==m.r.stable_hash(parent)
assert manifest['parent_manifest_hash']==m.r.stable_hash(parent)
assert manifest['prompts']==parent['prompts']
assert manifest['sampling']==parent['sampling']
assert manifest['rating_boundaries']==[18.75,43.75,56.25,75]
by={x['source_index']:x for x in manifest['sources']};assert len(by)==len(manifest['sources'])
failures={x['id']:x for x in s['failures']}
assert len(s['attempted'])==len(set(s['attempted']))
assert set(s['attempted'])==set(s['records'])|set(failures),'Unresolved in-flight call'
assert not set(s['records'])&set(failures),'A call both passed and failed'
prefix=manifest['sources'][:s['metadata']['completed_batches']*6]
assert {r['source_index'] for r in prefix}=={int(k.split(':')[1]) for k in s['attempted'] if k.startswith('convert:')},'Attempt order is not a complete source-order prefix'
count=0
for key,record in list(s['records'].items())+list(failures.items()):
 stage=record['stage'];i=record['source_index'];src=by[i];assert key==f'{stage}:{i}'
 base=dict(SOURCE_QUESTION=src['question'],FINAL_ANSWER=src['final_answer'],CHECKED_SOLUTION=src['checked_solution'])
 ev=s['items'][str(i)].get('evidence')
 if stage=='convert':args=base
 else:
  bank=s['records'][f'convert:{i}']['output'];assert bank['status']=='OK'
  expected=[{'id':c['id'],'sentence':c['sentence']} for c in bank['clues'][:4]]
  assert len(ev['clues'])==4 and ev['clues']==expected
  assert ev['final_answer']==src['final_answer']
  assert ev['rendered_clues']=='\n'.join(f'{n}. {c["sentence"]}' for n,c in enumerate(expected,1))
  assert s['items'][str(i)]['evidence_hash']==m.r.stable_hash(ev)
  if stage=='audit':args={**base,'RENDERED_CLUES':ev['rendered_clues']}
  elif stage=='copy':args=dict(FINAL_ANSWER=ev['final_answer'],PUBLIC_BANK=ev['rendered_clues'])
  else:
   assert s['items'][str(i)]['input_status']=='accepted'
   assert s['records'][f'audit:{i}']['output']['status']=='ACCEPT'
   assert s['records'][f'copy:{i}']['output']['status']=='no_direct_reconstruction'
   if stage=='student':args=dict(FINAL_ANSWER=ev['final_answer'],RENDERED_CLUES=ev['rendered_clues'])
   else:
    response=s['records'][f'student:{i}']['output']
    if stage=='judge_fidelity':args=dict(SOURCE_QUESTION=src['question'],CANDIDATE_QUESTION=response['question'])
    elif stage=='judge_validity':args=dict(FINAL_ANSWER=ev['final_answer'],RENDERED_CLUES=ev['rendered_clues'],STUDENT_RESPONSE=response)
    else:raise AssertionError('Unknown stage '+stage)
 assert record['input_hash']==m.r.stable_hash(args),'Input binding mismatch: '+key
 assert record['prompt']==m.r.render_template(manifest['prompts'][stage],args),'Prompt mismatch: '+key
 if key in s['records']:
  assert record['prompt_hash']==m.r.stable_hash(record['prompt'])
  out=record['output']
  if stage=='convert':m.validate_bank(out)
  elif stage=='audit':m.validate_audit(out,ev)
  elif stage=='copy':m.validate_copy(out,ev)
  elif stage=='student':
   m.r.validate_student(out);assert not m.r.has_generated_thinking(record['raw'])
  else:m.validate_judgment(out,stage.removeprefix('judge_'),question=response['question'],response=response,clue_count=4)
 count+=1
rows=[json.loads(x) for x in (e.ROOT/'questions-answers.jsonl').read_text().splitlines()]
baseline=[json.loads(x) for x in (e.ROOT/'calibration-47.jsonl').read_text().splitlines()]
assert len(rows)==100 and len(baseline)==47
assert [r['source_index'] for r in rows[:47]]==[r['source_index'] for r in baseline]
for current,original in zip(rows[:47],baseline):
 assert original=={k:v for k,v in current.items() if k not in ['cohort','rating_v4']}
 i=original['source_index'];assert e.complete(parent_state,i)
 assert parent_state['records'][f'student:{i}']['output']==original['qwen']
 assert original['score']==e.aggregate(parent_state['records'][f'judge_fidelity:{i}']['output'],parent_state['records'][f'judge_validity:{i}']['output'])
 assert original['clues']==[c['sentence'] for c in parent_state['items'][str(i)]['evidence']['clues']]
eligible=[r['source_index'] for r in manifest['sources'] if e.complete(s,r['source_index'])]
assert [r['source_index'] for r in rows[47:]]==eligible[:53]
assert len({e.normalize_question(r['source_question']) for r in rows})==100
for row in rows:
 assert len(row['clues'])==4
 assert row['rating_v4']==e.balanced_rating_v4(row['score']['score_100'])
 if row['cohort']=='extension':
  i=row['source_index']
  assert row['score']==e.aggregate(s['records'][f'judge_fidelity:{i}']['output'],s['records'][f'judge_validity:{i}']['output'])
assert all(r['source_index'] in {p['source_index'] for p in prefix} for r in rows[47:])
result={'status':'passed','selected_source_count':100,'calibration_count':47,'extension_count':53,'extension_bound_attempts':count,'accepted_records':len(s['records']),'preserved_failures':len(s['failures']),'public_clue_count':4,'selection':'first53 completely scored gate-passed rows in frozen source order','scope':'Structural/provenance verification, not independent mathematical truth or universal leakage accuracy.'}
m.r.atomic_write_json(e.ROOT/'verification.json',result);print(json.dumps(result,indent=2))
