#!/usr/bin/env python3
import argparse,json,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
from anlp_project.reconstruct_gates import validate_strict_disclosure, validate_copy_challenge
p=argparse.ArgumentParser();p.add_argument('--level',type=int,default=2);p.add_argument('--study-root',type=Path);p.add_argument('--copy',action='store_true');p.add_argument('--workers',type=int,choices=[1,2],default=2);a=p.parse_args();root=a.study_root or Path('artifacts/reconstruct/target-cues-av')/f'level{a.level}'
requests=json.loads((root/'student-requests.json').read_text());sources=json.loads((root/'student.json').read_text())['sources'];template=r.load_prompt('copy_challenge_p1' if a.copy else 'audit_source_disclosure_p4');target=root/('copy-challenge.json' if a.copy else 'disclosure.json')
state=json.loads(target.read_text()) if target.exists() else {'records':{},'failures':[],'attempted':[],'metadata':{'prompt_hash':r.stable_hash(template),'requests_hash':r.stable_hash(requests)}}
assert state['metadata']['requests_hash']==r.stable_hash(requests)
assert state['metadata']['prompt_hash']==r.stable_hash(template)
jobs=[(k,j) for k,j in requests.items() if k not in state['attempted']];state['attempted'] += [k for k,j in jobs];r.atomic_write_json(target,state)
def worker(key,j):
 ev=j['public_evidence'];public=ev['final_answer']+'\n'+ev['rendered_clues'];text=r.render_template(template,{'SOURCE_QUESTION':sources[str(j['source_index'])]['question'],'FINAL_ANSWER':ev['final_answer'],'PUBLIC_BANK':ev['rendered_clues']});raw=None
 try:
  raw=r.teacher_call(r.deepinfra_client(180),text,r.DEFAULT_TEACHER_MODEL,8192,'low');parsed=r.extract_json_object(raw['content']);out=validate_copy_challenge(parsed,public) if a.copy else validate_strict_disclosure(parsed,public,'source_disclosure')
  return key,{'output':out,'raw':raw,'rendered_prompt':text,'evidence_hash':j['evidence_hash']},None
 except Exception as exc:return key,None,{'id':key,'error':str(exc),'raw':raw or getattr(exc,'raw_response',None),'rendered_prompt':text}
with ThreadPoolExecutor(max_workers=a.workers) as pool:
 for future in as_completed([pool.submit(worker,k,j) for k,j in jobs]):
  key,record,error=future.result()
  if record:state['records'][key]=record
  else:state['failures'].append(error)
  r.atomic_write_json(target,state);print(key,record['output']['status'] if record else 'FAILED '+error['error'],flush=True)
print('Disclosure checks terminal.')
