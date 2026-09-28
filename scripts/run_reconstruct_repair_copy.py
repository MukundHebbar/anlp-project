#!/usr/bin/env python3
"""Freeze exact effective banks, then challenge all registered eligible inputs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash,atomic_write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--artifact',type=Path,default=Path('artifacts/reconstruct/d3-v2/repair-study.json'))
    parser.add_argument('--protocol',default='docs/plans/reconstruct-amendment-r.md')
    parser.add_argument('--boundary-indices',type=int,nargs='*',default=[123])
    parser.add_argument('--max-cases',type=int,default=10)
    parser.add_argument('--workers',type=int,choices=range(1,5),default=4)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--base-bank-prompt',default='convert_p4')
    args=parser.parse_args()
    artifact=args.artifact
    manifest=args.manifest or artifact.with_name('repair-copy-manifest.json')
    run=json.loads(artifact.read_text())
    if not manifest.exists():
        selected=[]
        for original_key,bank in run['banks'].items():
            if bank['prompt']!=args.base_bank_prompt:continue
            index=bank['source_index']
            outcome=run['metadata'].get('repair_outcomes',{}).get(str(index))
            key=outcome['effective_bank_key'] if outcome else original_key
            candidate=run['banks'][key]
            statuses={a['prompt']:a['output']['status'] for a in run['audits'].values() if a.get('bank_key')==key}
            accepted=all(statuses.get(p)=='ACCEPT' for p in ['audit_support_p1','audit_public_p4','audit_source_disclosure_p2'])
            if accepted or index in args.boundary_indices:
                selected.append({'source_index':index,'bank_key':key,'bank_prompt':candidate['prompt'],
                   'bank_output_hash':stable_hash(candidate['output']),
                   'source_record_hash':stable_hash(run['sources'][str(index)]),
                   'all_three_audits_accepted':accepted,
                   'inclusion':'accepted effective bank' if accepted else 'preregistered boundary diagnostic'})
        if len(selected)>args.max_cases:raise ValueError('Registered copy-call budget exceeded')
        atomic_write_json(manifest,{'protocol':args.protocol,'base_bank_prompt':args.base_bank_prompt,'rows':sorted(selected,key=lambda r:r['source_index']),
            'private_fields_in_challenge':False,'student_readiness':'pending independent reviews'})
    frozen=json.loads(manifest.read_text())
    assert frozen['protocol']==args.protocol
    assert frozen.get('base_bank_prompt','convert_p4')==args.base_bank_prompt
    assert len(frozen['rows'])<=args.max_cases
    for row in frozen['rows']:
        assert stable_hash(run['banks'][row['bank_key']]['output'])==row['bank_output_hash']
        assert stable_hash(run['sources'][str(row['source_index'])])==row['source_record_hash']
    print(f'Frozen {len(frozen["rows"])} copying inputs',flush=True)
    if args.prepare_only:return
    for prompt in [args.base_bank_prompt,'repair_disclosure_p1']:
        indices=[r['source_index'] for r in frozen['rows'] if r['bank_prompt']==prompt]
        if not indices:continue
        subprocess.run([sys.executable,'scripts/run_reconstruct_batch.py','--workers',str(args.workers),'--','copy-challenge',
            '--output',str(artifact),'--indices',*map(str,indices),'--bank-prompt',prompt,
            '--copy-prompt','copy_challenge_p1','--teacher-max-tokens','8192',
            '--reasoning-effort','low','--timeout','180','--max-cost-usd','.50'],check=True)


if __name__=='__main__':main()
