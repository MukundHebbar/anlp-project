#!/usr/bin/env python3
"""Verify complete cohort/provenance bindings without new model calls."""
import importlib.util,json
from pathlib import Path
spec=importlib.util.spec_from_file_location('final100',Path(__file__).with_name('run_reconstruct_final100.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
run=m.Run();s=run.state;manifest=run.manifest
assert s['metadata'].get('terminal') is True,'Run still active'
assert len(manifest['sources'])==100
by={x['source_index']:x for x in manifest['sources']};assert len(by)==100
failures={x['id']:x for x in s['failures']}
assert len(s['attempted'])==len(set(s['attempted']))
assert set(s['attempted'])==set(s['records'])|set(failures),'Unresolved in-flight call'
assert not set(s['records'])&set(failures),'A call both passed and failed'
assert all(f'convert:{i}' in s['attempted'] for i in by),'An allocated source was not attempted'
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
result={'status':'passed','source_count':100,'bound_attempts':count,'accepted_records':len(s['records']),'preserved_failures':len(s['failures']),'public_clue_count':4,'scope':'Structural/provenance verification, not independent mathematical truth or universal leakage accuracy.'}
m.r.atomic_write_json(m.ROOT/'verification.json',result);print(json.dumps(result,indent=2))
