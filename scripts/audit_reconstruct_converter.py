#!/usr/bin/env python3
"""Sequential, bounded audit stages; the batch runner owns each artifact lock."""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,required=True)
    p.add_argument('--bank-prompt',required=True)
    p.add_argument('--workers',type=int,default=2,choices=range(1,5))
    p.add_argument('--skip-support',action='store_true')
    a=p.parse_args()
    run=json.loads(a.artifact.read_text())
    indices=sorted({b['source_index'] for b in run['banks'].values()
                    if b['prompt']==a.bank_prompt and b['output'].get('status')=='OK'})
    if not indices:raise ValueError('No generated banks to audit')
    stages=([] if a.skip_support else ['audit_support_p1'])+['audit_public_p4','audit_source_disclosure_p2']
    for prompt in stages:
        cmd=[sys.executable,'scripts/run_reconstruct_batch.py','--workers',str(a.workers),'--','audit',
             '--output',str(a.artifact),'--audit-prompt',prompt,'--bank-prompt',a.bank_prompt,
             '--indices',*map(str,indices),'--teacher-max-tokens','8192','--reasoning-effort','low',
             '--timeout','180','--max-cost-usd','.50']
        print(f'Starting {prompt} for{len(indices)} banks; workers={a.workers}',flush=True)
        subprocess.run(cmd,check=True)
    print('All declared audit stages terminal; failures remain recorded.',flush=True)


if __name__=='__main__':main()
