#!/usr/bin/env python3
"""Bounded sequential audits; optional cascade avoids calls on already excluded banks."""
import argparse,json,subprocess,sys
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--study-root',type=Path,default=Path('artifacts/reconstruct/richer-exposure-aa'));parser.add_argument('--bank-prompt',default='convert_p6_rich');parser.add_argument('--min-clues',type=int,default=6);parser.add_argument('--max-clues',type=int,default=6);parser.add_argument('--cascade',action='store_true');parser.add_argument('--timeout',type=int,default=180);parser.add_argument('--workers',type=int,choices=range(1,5),default=4);args=parser.parse_args()
root=args.study_root;target=root/'run.json';run=json.loads(target.read_text());cap=str(run['metadata'].get('maximum_substudy_cost_usd',.75))
ids=sorted(b['source_index'] for b in run['banks'].values() if b['prompt']==args.bank_prompt and b['output']['status']=='OK' and args.min_clues<=len(b['output']['clues'])<=args.max_clues)
assert ids
required=run['metadata']['required_bank_audits'][args.bank_prompt];prior=[];schedule=[]
for prompt in required:
    run=json.loads(target.read_text());stage_ids=ids
    if args.cascade:
        eligible=[]
        for key,b in run['banks'].items():
            statuses={a['prompt']:a['output']['status'] for a in run['audits'].values() if a['bank_key']==key}
            if b['source_index'] in ids and b['prompt']==args.bank_prompt and all(statuses.get(p)=='ACCEPT' for p in prior):eligible.append(b['source_index'])
        stage_ids=sorted(eligible)
    schedule.append({'prompt':prompt,'indices':stage_ids,'cascade':args.cascade,'requires_prior_accept':list(prior) if args.cascade else []})
    (root/'audit-schedule.json').write_text(json.dumps(schedule,indent=2)+'\n')
    if stage_ids:
        subprocess.run([sys.executable,'scripts/run_reconstruct_batch.py','--workers',str(args.workers),'--','audit','--output',str(target),'--bank-prompt',args.bank_prompt,'--audit-prompt',prompt,'--indices',*map(str,stage_ids),'--teacher-max-tokens','8192','--reasoning-effort','low','--timeout',str(args.timeout),'--max-cost-usd',cap],check=True)
    prior.append(prompt)
run=json.loads(target.read_text());eligible=[]
for key,b in run['banks'].items():
    statuses={a['prompt']:a['output']['status'] for a in run['audits'].values() if a['bank_key']==key}
    if b['source_index'] in ids and b['prompt']==args.bank_prompt and all(statuses.get(p)=='ACCEPT' for p in required):eligible.append(b['source_index'])
if eligible:
    subprocess.run([sys.executable,'scripts/run_reconstruct_batch.py','--workers',str(args.workers),'--','copy-challenge','--output',str(target),'--bank-prompt',args.bank_prompt,'--indices',*map(str,eligible),'--teacher-max-tokens','8192','--reasoning-effort','low','--timeout',str(args.timeout),'--max-cost-usd',cap],check=True)
print('Audits and copy challenges terminal. Manual review required before local calls.',flush=True)
