#!/usr/bin/env python3
"""Audit changed successful repairs once; never rejudge unchanged public facts."""
import json
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact',type=Path,default=Path('artifacts/reconstruct/d3-v2/repair-study.json'))
    parser.add_argument('--workers',type=int,choices=range(1,5),default=3)
    args=parser.parse_args()
    artifact=args.artifact
    run=json.loads(artifact.read_text())
    outcomes=run['metadata']['repair_outcomes']
    indices=sorted(int(i) for i,o in outcomes.items() if o['status']=='OK' and not o['public_unchanged'])
    print(f'Changed successful repairs to audit: {indices}; unchanged inputs retain prior labels',flush=True)
    if not indices:return
    for prompt in ['audit_support_p1','audit_public_p4','audit_source_disclosure_p2']:
        subprocess.run([sys.executable,'scripts/run_reconstruct_batch.py','--workers',str(args.workers),'--','audit',
            '--output',str(artifact),'--indices',*map(str,indices),'--bank-prompt','repair_disclosure_p1',
            '--audit-prompt',prompt,'--teacher-max-tokens','8192','--reasoning-effort','low',
            '--timeout','180','--max-cost-usd','.50'],check=True)


if __name__=='__main__':main()
