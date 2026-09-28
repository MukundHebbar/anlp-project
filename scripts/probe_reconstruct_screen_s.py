#!/usr/bin/env python3
"""Same public evidence and p1 prompt, stronger source-blind teacher as student."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
import copy
import fcntl
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r

ROOT=Path('artifacts/reconstruct/d3-v2')
OUTPUT=ROOT/'stronger-feasibility.json'
MODEL='deepseek-ai/DeepSeek-V4.1-Flash'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--retry-failed-once',action='store_true')
    args=parser.parse_args()
    template=r.load_prompt('student_p1')
    with OUTPUT.with_suffix('.json.lock').open('w') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        if not OUTPUT.exists():
            base=json.loads((ROOT/'repaired-student.json').read_text())
            public=json.loads((ROOT/'repaired-student-inputs.json').read_text())
            requests={}
            for index,item in public.items():
                e=item['evidence'];assert r.stable_hash(e)==item['evidence_hash']
                prompt=r.render_template(template,{'FINAL_ANSWER':e['final_answer'],'RENDERED_CLUES':e['rendered_clues']})
                requests[index]={'rendered_prompt':prompt,'rendered_prompt_hash':r.stable_hash(prompt),
                                 'public_evidence':e,'bank_key':item['bank_key']}
            assert sorted(map(int,requests))==[8,27,33,77,86,112,136,141,143]
            run={k:copy.deepcopy(base[k]) for k in ['sources','partitions','banks','audits']}
            run.update(metadata={'study':'amendment T, stronger source-blind feasibility',
                'template_hash':r.stable_hash(template),'frozen_requests':requests,
                'no_private_fields_in_rendered_prompt':True,'created_at':r.utc_now()},
                responses={},evaluations={},source_recovery={},failures=[])
            r.atomic_write_json(OUTPUT,run)
        else:run=json.loads(OUTPUT.read_text())
        assert run['metadata']['template_hash']==r.stable_hash(template)
        if args.prepare_only:
            print('Frozen nine source-blind stronger-model requests; no calls')
            return
        sampling={'temperature':0.0,'max_tokens':8192,'reasoning_effort':'low','seed':None,'draw_index':0}
        attempts=Counter(f['key'] for f in run['failures'] if f['stage']=='student')
        jobs=[]
        for index,item in run['metadata']['frozen_requests'].items():
            assert r.stable_hash(item['rendered_prompt'])==item['rendered_prompt_hash']
            key=f'{index}:{r.stable_hash(item["public_evidence"])}:{r.stable_hash(template)}:{MODEL}:{r.stable_hash(sampling)}'
            if key not in run['responses'] and attempts[key]==(1 if args.retry_failed_once else 0):jobs.append((key,index,item))
        reserve=sum((len(i['rendered_prompt'])/4*.20+8192*.60)/1e6 for _,_,i in jobs)
        if r.actual_cost(run)+reserve>.50:raise RuntimeError('Reserved cost exceeds probe artifact ceiling')
        def worker(key,index,item):
            raw=None
            try:
                raw=r.teacher_call(r.deepinfra_client(180),item['rendered_prompt'],MODEL,8192,'low')
                output,flag=r.parse_student_response(raw['content'])
                return key,index,item,raw,output,flag,None
            except Exception as exc:return key,index,item,raw,None,None,exc
        with ThreadPoolExecutor(max_workers=3) as pool:
            for future in as_completed([pool.submit(worker,*job) for job in jobs]):
                key,index,item,raw,output,flag,error=future.result()
                if error is not None:
                    r.failure(run,'student',int(index),key,error,raw)
                    print(f'stronger {index}: failed {error}',flush=True)
                else:
                    run['responses'][key]={'source_index':int(index),'bank_key':item['bank_key'],
                      'condition':'bank','public_evidence':item['public_evidence'],
                      'evidence_hash':r.stable_hash(item['public_evidence']),
                      'prompt':'student_p1','prompt_hash':r.stable_hash(template),'model':MODEL,
                      'sampling':sampling,'output':output,'format_error':flag,
                      'request':{k:v for k,v in raw.items() if k!='content'},'raw_content':raw['content'],
                      'rendered_prompt_hash':item['rendered_prompt_hash']}
                    print(f'stronger {index}: saved',flush=True)
                r.atomic_write_json(OUTPUT,run)


if __name__=='__main__':main()
