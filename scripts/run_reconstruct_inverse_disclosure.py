#!/usr/bin/env python3
"""Run frozen X audit slots with unchanged teacher settings and bounded retries."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash
ROOT=Path('artifacts/reconstruct/inverse-disclosure-x')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retry-failed-once',action='store_true')
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args()
    root=args.root
    manifest=json.loads((root/'manifest.json').read_text())
    run=json.loads((root/'run.json').read_text())
    assert run['metadata']['manifest_hash']==stable_hash(manifest)
    for row in manifest['fixtures']:
        assert stable_hash(run['banks'][row['bank_key']]['output'])==row['bank_output_hash']
        assert stable_hash(run['sources'][str(row['source_index'])])==row['source_record_hash']
    bank_prompts={run['banks'][row['bank_key']]['prompt'] for row in manifest['fixtures']}
    assert len(bank_prompts)==1
    bank_prompt=bank_prompts.pop()
    for prompt in manifest['prompts']:
        assert stable_hash(Path(f'data/prompts/reconstruct/runtime/{prompt}.md').read_text())==manifest['prompt_file_hashes'][prompt]
        print(str(root)+' stage '+prompt,flush=True)
        cmd=[sys.executable,'scripts/run_reconstruct_batch.py','--workers','4']
        if args.retry_failed_once:cmd.append('--retry-failed-once')
        cmd+=['--','audit','--output',str(root/'run.json'),'--bank-prompt',bank_prompt,
              '--audit-prompt',prompt,'--teacher-max-tokens','8192','--reasoning-effort','low',
              '--timeout','180','--max-cost-usd',str(manifest.get('maximum_substudy_cost_usd',.50))]
        subprocess.run(cmd,check=True)
    print('All declared stages terminal; inspect missingness and hard negatives before any adoption.',flush=True)


if __name__=='__main__':main()
