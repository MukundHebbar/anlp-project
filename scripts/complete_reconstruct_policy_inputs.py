#!/usr/bin/env python3
"""After audits are terminal, finish needed copy checks and freeze reviewed exposure."""
import argparse,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
p=argparse.ArgumentParser();p.add_argument('--study-root',type=Path,required=True);p.add_argument('--bank-prompt',required=True);p.add_argument('--arm',required=True);p.add_argument('--workers',type=int,default=2,choices=range(1,5));a=p.parse_args();root=a.study_root;target=root/'run.json'
run=json.loads(target.read_text());refs={x['source_index']:x for x in json.loads((root/'prestudent-content-review.json').read_text())['rows']};todo=[]
for index,ref in refs.items():
 if not ref['manual_content_pass']:continue
 try:key,bank=r.accepted_bank(run,index,a.bank_prompt)
 except ValueError:continue
 assert ref['bank_hash']==r.stable_hash(bank['output'])
 matches=[v for v in run.get('copy_challenges',{}).values() if v['bank_key']==key]
 if not matches and not any(f['stage']=='copy_challenge' and f['source_index']==index for f in run['failures']):todo.append(index)
if todo:
 subprocess.run([sys.executable,'scripts/run_reconstruct_batch.py','--workers',str(a.workers),'--','copy-challenge','--output',str(target),'--bank-prompt',a.bank_prompt,'--indices',*map(str,sorted(todo)),'--teacher-max-tokens','8192','--reasoning-effort','low','--timeout','600','--max-cost-usd',str(run['metadata']['maximum_substudy_cost_usd'])],check=True)
subprocess.run([sys.executable,'scripts/freeze_reconstruct_richer_review.py','--study-root',str(root),'--bank-prompt',a.bank_prompt],check=True)
subprocess.run([sys.executable,'scripts/prepare_reconstruct_policy_student.py','--study-root',str(root),'--bank-prompt',a.bank_prompt,'--arm',a.arm],check=True)
