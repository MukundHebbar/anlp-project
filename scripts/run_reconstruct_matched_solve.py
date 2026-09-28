#!/usr/bin/env python3
"""Once-only same-family local SOLVE control, separate from reconstruction metrics."""
import argparse,json,sys,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
p=argparse.ArgumentParser()
p.add_argument('--study-root',type=Path,default=Path('artifacts/reconstruct/matched-solve-ai'))
p.add_argument('--source-run',type=Path,default=Path('artifacts/reconstruct/one-gap-ah/run.json'))
p.add_argument('--protocol',default='docs/plans/reconstruct-amendment-ai.md')
args=p.parse_args()
ROOT=args.study_root
PROMPT='Solve the mathematical problem. Give a concise mathematical justification and the final answer. Return JSON only with keys "justification" and "final_answer".\n\nQUESTION:\n'
ROOT.mkdir(exist_ok=True)
target=ROOT/'run.json'
if target.exists():
    state=json.loads(target.read_text())
else:
    parent=json.loads(args.source_run.read_text())
    sources=parent['sources']
    state={'metadata':{'protocol':'docs/plans/reconstruct-amendment-ai.md','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model':r.DEFAULT_MODEL,'prompt_hash':r.stable_hash(PROMPT),'sources_hash':r.stable_hash(sources),'thinking':False,'quantization':'Q4_K_M','max_tokens':8192,'seed':0},'sources':sources,'requests':{str(i):{'source_index':i,'prompt':PROMPT+sources[str(i)]['question'],'source_hash':r.stable_hash(sources[str(i)])} for i in sorted(map(int,sources))},'attempted':[],'responses':{},'failures':[]}
    state['metadata']['requests_hash']=r.stable_hash(state['requests'])
    excluded=parent['metadata'].get('source_preflight_exclusions',{})
    state['requests']={k:v for k,v in state['requests'].items() if k not in excluded}
    state['metadata'].update(protocol=args.protocol,source_preflight_exclusions=excluded,original_denominator=len(sources),requests_hash=r.stable_hash(state['requests']),source_run=str(args.source_run))
    r.atomic_write_json(target,state)
assert r.stable_hash(state['requests'])==state['metadata']['requests_hash']
config=r.SamplingConfig(.7,.8,20,8192,0)
client=r.local_client(r.DEFAULT_LOCAL_URL,300)
for key,job in state['requests'].items():
    if key in state['attempted']:continue
    state['attempted'].append(key);r.atomic_write_json(target,state)
    raw=None
    try:
        raw=r.student_call(client,job['prompt'],r.DEFAULT_MODEL,config)
        if r.has_generated_thinking(raw):raise ValueError('Unexpected thinking output')
        out=r.extract_json_object(raw['content'])
        if not isinstance(out.get('justification'),str) or 'final_answer' not in out:raise ValueError('Missing justification/final_answer')
        state['responses'][key]={'source_index':int(key),'output':out,'raw':raw,'prompt_hash':r.stable_hash(job['prompt'])}
        print(key,'completed',raw['elapsed_seconds'],flush=True)
    except Exception as exc:
        state['failures'].append({'source_index':int(key),'error':f'{type(exc).__name__}: {exc}','raw':raw})
        print(key,'FAILED',str(exc),flush=True)
    r.atomic_write_json(target,state)
print('All',len(state['requests']),'SOLVE control slots terminal; analytic review required.',flush=True)
