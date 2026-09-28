#!/usr/bin/env python3
"""Revalidate saved strict-audit responses after the public-header boundary fix.

No model calls; no mathematical text edits; failures remain immutable records.
"""
import argparse
import fcntl
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import extract_json_object, latest_bank, load_prompt, stable_hash
from anlp_project.reconstruct_gates import public_disclosure_text, validate_strict_disclosure
from anlp_project.storage import atomic_write_json


def recover(run):
    prompt='audit_public_p4'
    digest=stable_hash(load_prompt(prompt))
    recovered=[]
    for f in run.get('failures',[]):
        if (f['stage']!='audit' or f['key'] in run['audits']
            or f.get('error')!='ValueError: Disclosure review quotes hidden or nonexistent text'):
            continue
        index=f['source_index']
        bank_key,bank=latest_bank(run,index)
        prefix=f'{index}:{stable_hash(bank["output"])}:{digest}:'
        if not f['key'].startswith(prefix):continue
        model,effort=f['key'][len(prefix):].rsplit(':',1)
        raw=f.get('raw') or {}
        try:
            parsed=extract_json_object(raw['content'])
            public=public_disclosure_text(run['sources'][str(index)]['final_answer'],bank['output'],'public_disclosure')
            validate_strict_disclosure(parsed,public,'public_disclosure')
        except (KeyError,ValueError,TypeError):
            continue
        run['audits'][f['key']]={'source_index':index,'bank_key':bank_key,'prompt':prompt,
           'prompt_hash':digest,'model':model,'reasoning_effort':effort,'output':parsed,
           'request':{k:v for k,v in raw.items() if k!='content'},'raw_content':raw['content'],
           'validation_recovery':{'rule':'include actual public header and structured payload in quote boundary',
                                  'original_failure_key':f['key'],'new_model_call':False,'text_changed':False}}
        recovered.append(index)
    return recovered


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('artifact',type=Path)
    a=p.parse_args()
    with a.artifact.with_suffix(a.artifact.suffix+'.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        run=json.loads(a.artifact.read_text())
        indices=recover(run)
        atomic_write_json(a.artifact,run)
        print(json.dumps({'revalidated_sources':indices,'new_calls':0}))
