#!/usr/bin/env python3
"""Resume a frozen extension with bounded transport recovery and a circuit breaker."""
import argparse
import copy
import hashlib
import importlib.util
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

spec=importlib.util.spec_from_file_location('extension',Path(__file__).with_name('run_reconstruct_valid100.py'))
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
ORIGINAL=e.ROOT
ROOT=Path('artifacts/reconstruct/valid-100-recovery-v1')
e.ROOT=ROOT;e.m.ROOT=ROOT
r=e.m.r

class CircuitOpen(RuntimeError):pass

def transport_failure(row):
    return row.get('error_class') in ['APIConnectionError','APITimeoutError'] or row.get('error') in ['Connection error.','Request timed out.']

def prepare():
    ROOT.mkdir(parents=True,exist_ok=True)
    assert not (ROOT/'manifest.json').exists(),'Already prepared'
    parent=json.loads((ORIGINAL/'manifest.json').read_text())
    manifest=copy.deepcopy(parent)
    manifest.update(version='RECONSTRUCT-VALID100-RECOVERY-v1',protocol='docs/plans/reconstruct-valid100-transport-recovery.md',cost_ceiling_usd=4.75,original_extension_manifest_hash=r.stable_hash(parent),original_extension_path=str(ORIGINAL),retry_policy='At most2 total attempts only for transport failures; parsed/model-validation failures are not retried',runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    state=json.loads((ORIGINAL/'run.json').read_text())
    state['metadata']=dict(manifest_hash=r.stable_hash(manifest),created_at=r.utc_now(),completed_batches=0,original_phase_metadata=state['metadata'])
    state['transport_history']=[]
    for f in list(state['failures']):
        if transport_failure(f):
            f['history_origin']=str(ORIGINAL);state['transport_history'].append(f)
            state['failures'].remove(f);state['attempted'].remove(f['id'])
    for key,item in state['items'].items():
        if item.get('orchestration_error'):item['prior_orchestration_error']=item.pop('orchestration_error')
        if 'convert:'+key not in state['attempted']:item['status']='allocated'
    for name in ['calibration-47.jsonl','manual-review.json','EXPORTS.md','tests.log']:
        (ROOT/name).write_bytes((ORIGINAL/name).read_bytes())
    (ROOT/'runner-frozen.py').write_bytes(Path(__file__).read_bytes())
    r.atomic_write_json(ROOT/'manifest.json',manifest);r.atomic_write_json(ROOT/'run.json',state)
    print('Preserved successful records:',len(state['records']),'transport failures eligible for one retry:',len(state['transport_history']),flush=True)

class Run(e.Run):
    def __init__(self):
        super().__init__();self.circuit=threading.Event();self.transport_streak=0;self.budget_stop=False

    def cost(self):
        rows=list(self.state['records'].values())+self.state['failures']+self.state.get('transport_history',[])
        return sum((x.get('raw') or {}).get('usage',{}).get('estimated_cost') if (x.get('raw') or {}).get('usage',{}).get('estimated_cost') is not None else x.get('reserved_cost_usd',0) for x in rows if x.get('stage')!='student')

    def health(self):
        client=None
        try:
            client=r.deepinfra_client(20);client.client.models.list();return True
        except Exception as exc:
            print('Unpaid health check failed:',type(exc).__name__,str(exc)[:160],flush=True);return False
        finally:
            if client:client.client.close()

    def call(self,stage,source,args,validator,student=False):
        key=f'{stage}:{source["source_index"]}';prompt=r.render_template(self.manifest['prompts'][stage],args)
        cap=16384 if stage=='convert' else 8192
        reserve=0 if student else (len(prompt)*.20+cap*.60)/1e6
        while True:
            with e.m.LOCK:
                if key in self.state['records']:return self.state['records'][key]['output']
                if self.circuit.is_set():raise CircuitOpen('Transport circuit open; source remains pending')
                prior=[x for x in self.state.get('transport_history',[]) if x['id']==key]
                failed=next((x for x in self.state['failures'] if x['id']==key),None)
                if failed:
                    if not transport_failure(failed) or len(prior)>=1:return None
                    self.state['failures'].remove(failed);failed['history_origin']=str(ROOT)
                    self.state['transport_history'].append(failed);self.state['attempted'].remove(key)
                    prior.append(failed)
                if key in self.state['attempted']:return None
            with e.LOCAL if student else e.TEACHER:
                with e.m.LOCK:
                    if self.circuit.is_set():raise CircuitOpen('Transport circuit open; source remains pending')
                    if self.cost()+self.reserved+reserve>self.manifest['cost_ceiling_usd']:
                        self.budget_stop=True;raise RuntimeError('Recovery cost ceiling cannot reserve next call')
                    self.reserved+=reserve;self.state['attempted'].append(key);self.save()
                raw=None;out=None;client=None;retry=False
                try:
                    client=r.local_client(timeout=600) if student else r.deepinfra_client(180)
                    raw=r.student_call(client,prompt,self.manifest['student'],r.SamplingConfig(**self.manifest['sampling'])) if student else r.teacher_call(client,prompt,self.manifest['teacher'],cap,'low')
                    if student and r.has_generated_thinking(raw):raise ValueError('Unexpected thinking output')
                    out=r.extract_json_object(raw['content']);validator(out)
                    record=dict(reserved_cost_usd=reserve,stage=stage,source_index=source['source_index'],output=out,raw=raw,prompt=prompt,prompt_hash=r.stable_hash(prompt),input_hash=r.stable_hash(args),model=self.manifest['student'] if student else self.manifest['teacher'],validation_notes=e.m.validation_notes(out,args.get('STUDENT_RESPONSE',{})),attempt_number=len(prior)+1)
                    with e.m.LOCK:self.state['records'][key]=record;self.transport_streak=0
                    print(key,'completed',flush=True);return out
                except Exception as exc:
                    chain=[];cause=exc
                    while cause is not None:
                        chain.append(dict(type=type(cause).__name__,message=str(cause)[:500]));cause=cause.__cause__
                    failure=dict(id=key,reserved_cost_usd=reserve,stage=stage,source_index=source['source_index'],error=str(exc),error_class=type(exc).__name__,error_chain=chain,output=out,raw=raw or getattr(exc,'raw_response',None),prompt=prompt,input_hash=r.stable_hash(args),attempt_number=len(prior)+1)
                    with e.m.LOCK:
                        self.state['failures'].append(failure)
                        if transport_failure(failure):
                            self.transport_streak+=1;retry=len(prior)==0
                            if self.transport_streak>=3:self.circuit.set()
                        else:self.transport_streak=0
                    print(key,'FAILED',type(exc).__name__,str(exc)[:200],flush=True)
                finally:
                    if client:
                        try:client.client.close()
                        except Exception:pass
                    with e.m.LOCK:self.reserved-=reserve;self.save()
            if not retry:return None
            time.sleep(3)

    def run(self):
        if self.state['metadata'].get('terminal'):return e.report(self.manifest,self.state)
        if not self.health():
            self.state['metadata']['paused_reason']='Unpaid API health check failed';self.save();return e.report(self.manifest,self.state)
        sources=self.manifest['sources'];pos=self.state['metadata']['completed_batches']*6
        while pos<len(sources):
            with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(self.workflow,sources[pos:pos+6]))
            self.state['metadata']['recorded_cost_usd']=self.cost()
            if self.circuit.is_set():
                self.state['metadata']['paused_reason']='Three consecutive transport failures';self.save();e.report(self.manifest,self.state)
                healthy=False
                for _ in range(6):
                    time.sleep(30)
                    if self.health():healthy=True;break
                if not healthy:return e.report(self.manifest,self.state)
                self.circuit.clear();self.transport_streak=0;self.state['metadata'].pop('paused_reason',None);self.save();continue
            self.state['metadata']['completed_batches']=pos//6+1;self.save()
            total=sum(e.complete(self.state,s['source_index']) for s in sources)
            print(f'BATCH {pos//6+1}: complete added={total}/53; conservative cost=${self.cost():.5f}',flush=True)
            e.report(self.manifest,self.state)
            if total>=53 or self.budget_stop:break
            pos+=6
        self.state['metadata'].update(terminal=True,finished_at=r.utc_now(),recorded_cost_usd=self.cost());self.save()
        return e.report(self.manifest,self.state)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','report']);a=p.parse_args()
    if a.action=='prepare':prepare()
    elif a.action=='run':print(json.dumps(Run().run(),indent=2))
    else:
        obj=Run();print(json.dumps(e.report(obj.manifest,obj.state),indent=2))
