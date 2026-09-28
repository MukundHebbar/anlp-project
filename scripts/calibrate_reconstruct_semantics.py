#!/usr/bin/env python3
"""Run a frozen semantic-control manifest with blinded labels and bounded calls."""
import argparse
import fcntl
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import (DEFAULT_TEACHER_MODEL, deepinfra_client, extract_json_object,
    failure, load_prompt, render_template, reserve_teacher_request, stable_hash, teacher_call,
    validate_source_recovery)
from anlp_project.storage import atomic_write_json


def render_case(template, case):
    return render_template(template,{'SOURCE_QUESTION':case['source_question'],
                                     'CANDIDATE_QUESTION':case['candidate_question']})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixtures',type=Path,default=Path('data/manifests/reconstruct-semantic-development-v1.json'))
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--prompt',choices=['source_recovery_p1','source_recovery_p2'],default='source_recovery_p2')
    p.add_argument('--limit',type=int)
    a=p.parse_args()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.with_suffix('.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        payload=json.loads(a.fixtures.read_text())
        template=load_prompt(a.prompt)
        signature=stable_hash({'fixtures':payload,'template':template,'model':DEFAULT_TEACHER_MODEL,
                               'reasoning':'low','max_tokens':8192,'timeout':180})
        run=json.loads(a.output.read_text()) if a.output.exists() else {
            'metadata':{'signature':signature,'fixture_path':str(a.fixtures),'prompt':a.prompt,
                        'status':'development calibration, no independent accuracy claim'},
            'banks':{},'judge_fixtures':{},'failures':[]}
        if run['metadata']['signature']!=signature:
            raise ValueError('Calibration configuration changed; use a new artifact')
        client=deepinfra_client(180)
        for case in payload['fixtures'][:a.limit]:
            key=f'{case["id"]}:{signature}'
            if key in run['judge_fixtures'] or any(f['key']==key for f in run['failures']):
                continue
            prompt=render_case(template,case)
            raw=None
            try:
                reserve_teacher_request(run,prompt,8192,.25)
                raw=teacher_call(client,prompt,DEFAULT_TEACHER_MODEL,8192,'low')
                value=validate_source_recovery(extract_json_object(raw['content']),strict=a.prompt=='source_recovery_p2')
                run['judge_fixtures'][key]={'fixture_id':case['id'],'family':case['family'],
                    'expected':case['expected'],'passed':value['source_recovery']==case['expected'],
                    'output':value,'rendered_prompt':prompt,'model':DEFAULT_TEACHER_MODEL,
                    'prompt':a.prompt,'raw_content':raw['content'],
                    'request':{k:v for k,v in raw.items() if k!='content'}}
                print(f'{case["id"]}: expected={case["expected"]} observed={value["source_recovery"]}',flush=True)
            except Exception as exc:
                failure(run,'semantic_fixture',-1,key,exc,raw)
                print(f'{case["id"]}: FAILED {exc}',flush=True)
            atomic_write_json(a.output,run)


if __name__=='__main__':
    main()
