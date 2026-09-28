#!/usr/bin/env python3
import json,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
root=Path('artifacts/reconstruct/inverse-bridges-aw');root.mkdir(exist_ok=True)
parent=json.loads(Path('artifacts/reconstruct/constructive-gate-al/student.json').read_text());requests=json.loads(Path('artifacts/reconstruct/constructive-gate-al/student-requests.json').read_text());template=r.load_prompt('convert_p11_inverse_bridge');target=root/'conversion.json'
state=json.loads(target.read_text()) if target.exists() else {'metadata':{'protocol':'docs/plans/reconstruct-amendment-aw.md','prompt_hash':r.stable_hash(template)},'records':{},'failures':[],'attempted':[]}
assert state['metadata']['prompt_hash']==r.stable_hash(template)
jobs=[j for j in requests.values() if str(j['source_index']) not in state['attempted']];state['attempted'] += [str(j['source_index']) for j in jobs];r.atomic_write_json(target,state)
def worker(j):
 i=str(j['source_index']);s=parent['sources'][i];text=r.render_template(template,{'SOURCE_QUESTION':s['question'],'FINAL_ANSWER':s['final_answer'],'CHECKED_SOLUTION':s['checked_solution'],'RENDERED_CLUES':j['public_evidence']['rendered_clues']});raw=None
 try:
  raw=r.teacher_call(r.deepinfra_client(180),text,r.DEFAULT_TEACHER_MODEL,8192,'low');out=r.extract_json_object(raw['content']);assert len(out['bridge_clues'])==2 and all(isinstance(x,str) and x.strip() for x in out['bridge_clues']);assert isinstance(out['hidden_support'],str)
  return i,dict(output=out,raw=raw,rendered_prompt=text,source_hash=r.stable_hash(s)),None
 except Exception as exc:return i,None,dict(id=i,error=str(exc),raw=raw or getattr(exc,'raw_response',None),rendered_prompt=text)
with ThreadPoolExecutor(max_workers=2) as pool:
 for future in as_completed([pool.submit(worker,j) for j in jobs]):
  i,record,error=future.result()
  if record:state['records'][i]=record
  else:state['failures'].append(error)
  r.atomic_write_json(target,state);print(i,record['output'] if record else error['error'],flush=True)
print('AW conversion terminal; inspect and freeze before student calls.')
