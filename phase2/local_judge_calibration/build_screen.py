"""Freeze a small, checkpoint-balanced Gemma screen before observing its predictions."""
from pathlib import Path
import hashlib
import json
import random

ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'artifacts/qwen-judge-calibration/requests.jsonl'
rows=[json.loads(line) for line in source.open()]
groups={}
for row in rows:
    key=row['key'].rsplit('|',1)[0]
    groups.setdefault(key,[]).append(row)
buckets={}
for key in groups:
    arm,uid=key.split('|')
    task='judge' if uid.startswith('judge-') else 'reconstruct'
    buckets.setdefault((arm,task),[]).append(key)
chosen=[]
for (arm,task),keys in sorted(buckets.items()):
    rng=random.Random(f'20261027:gemma-screen:{arm}:{task}')
    chosen.extend(rng.sample(sorted(keys),min(12,len(keys))))
selected=set(chosen)
requests=[row for row in rows if row['key'].rsplit('|',1)[0] in selected]
out=ROOT/'local/local-judge-calibration'
out.mkdir(parents=True,exist_ok=True)
with (out/'gemma-screen-requests.jsonl').open('w') as f:
    for row in requests:f.write(json.dumps(row,ensure_ascii=False)+'\n')
selection={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
           'seed':'20261027:gemma-screen:<arm>:<task>','per_checkpoint_per_task':12,
           'response_groups':sorted(chosen),'requests':len(requests),
           'questions':sum(len(r['questions']) for r in requests),
           'purpose':'Light calibration screen; not a full validation or proof of equivalence.'}
(ROOT/'phase2/local_judge_calibration/gemma-screen-selection.json').write_text(json.dumps(selection,indent=2)+'\n')
for name,path in [('qwen27b-screen-reference',ROOT/'artifacts/qwen-judge-calibration/answers.jsonl'),
                  ('selene-screen-reference',ROOT/'local/local-judge-calibration/selene/answers.jsonl')]:
    folder=out/name
    folder.mkdir(exist_ok=True)
    records=[json.loads(line) for line in path.open()]
    records=[r for r in records if r['key'].rsplit('|',1)[0] in selected]
    with (folder/'answers.jsonl').open('w') as f:
        for r in records:f.write(json.dumps(r)+'\n')
print(json.dumps({k:v for k,v in selection.items() if k!='response_groups'},indent=2))
