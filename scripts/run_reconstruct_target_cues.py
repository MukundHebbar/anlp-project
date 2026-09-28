#!/usr/bin/env python3
import json,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
root=Path('artifacts/reconstruct/target-cues-av');root.mkdir(exist_ok=True)
sources=json.loads(Path('artifacts/reconstruct/target-prefix-ap/student.json').read_text())['sources']
requests=json.loads(Path('artifacts/reconstruct/target-prefix-ap/student-requests.json').read_text())
template=r.load_prompt('convert_p10_target_cues');path=root/'conversion.json'
state=json.loads(path.read_text()) if path.exists() else {'metadata':{'protocol':'docs/plans/reconstruct-amendment-av.md','prompt_hash':r.stable_hash(template)},'records':{},'failures':[],'attempted':[]}
assert state['metadata']['prompt_hash']==r.stable_hash(template)
jobs=[j for j in requests.values() if str(j['source_index']) not in state['attempted']]
state['attempted'] += [str(j['source_index']) for j in jobs];r.atomic_write_json(path,state)
def worker(j):
 i=str(j['source_index']);s=sources[i];text=r.render_template(template,{'SOURCE_QUESTION':s['question'],'FINAL_ANSWER':s['final_answer'],'CHECKED_SOLUTION':s['checked_solution'],'RENDERED_CLUES':j['public_evidence']['rendered_clues']});raw=None
 try:
  raw=r.teacher_call(r.deepinfra_client(180),text,r.DEFAULT_TEACHER_MODEL,8192,'low');out=r.extract_json_object(raw['content'])
  assert all(isinstance(out.get(k),str) and out[k].strip() for k in ['target_family_cue','method_cue','hidden_support'])
  return i,{'output':out,'raw':raw,'rendered_prompt':text,'source_hash':r.stable_hash(s)},None
 except Exception as exc:return i,None,{'id':i,'error':str(exc),'raw':raw or getattr(exc,'raw_response',None),'rendered_prompt':text}
with ThreadPoolExecutor(max_workers=4) as pool:
 for f in as_completed([pool.submit(worker,j) for j in jobs]):
  i,record,error=f.result()
  if record:state['records'][i]=record
  else:state['failures'].append(error)
  r.atomic_write_json(path,state);print(i,record['output'] if record else error['error'],flush=True)
print('AV conversion terminal; freeze manual input review before any local draws.')
