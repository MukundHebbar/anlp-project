#!/usr/bin/env python3
"""Recover parseable saved student failures without making model calls."""
import argparse
import copy
import fcntl
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import parse_student_response,stable_hash
from anlp_project.storage import atomic_write_json


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    with a.run.with_suffix(a.run.suffix+'.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        r=json.loads(a.run.read_text());recovered=0
        configs={stable_hash(x['sampling']):x['sampling'] for x in r['responses'].values()}
        for failure in r['failures']:
            key=failure['key'];raw=failure.get('raw')
            if failure['stage']!='student' or key in r['responses'] or not raw:continue
            prefix,config_hash=key.rsplit(':',1)
            templates=[v for k,v in r['responses'].items() if k.rsplit(':',1)[0]==prefix]
            if not templates or config_hash not in configs:continue
            try:parsed,flag=parse_student_response(raw['content'])
            except ValueError:continue
            row=copy.deepcopy(templates[0]);row['sampling']=configs[config_hash]
            row['output']=parsed;row['format_error']=flag;row['raw_content']=raw['content']
            row['request']={k:v for k,v in raw.items() if k!='content'}
            row['recovered_from_failure']={'key':key,'time':failure['time'],'method':'deterministic parser; no model call'}
            assert key==f"{row['source_index']}:{row['evidence_hash']}:{row['prompt_hash']}:{row['model']}:{stable_hash(row['sampling'])}"
            r['responses'][key]=row;recovered+=1
        atomic_write_json(a.run,r);print(f'Recovered {recovered} raw responses; failure records preserved')


if __name__=='__main__':main()
