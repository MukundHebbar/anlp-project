#!/usr/bin/env python3
"""Run all frozen Z populations sequentially within the aggregate budget."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash
ROOT=Path('artifacts/reconstruct/witness-boundary-z')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retry-failed-once',action='store_true')
    args=parser.parse_args();m=json.loads((ROOT/'manifest.json').read_text())
    assert sum(json.loads(Path(p['root'],'manifest.json').read_text())['maximum_substudy_cost_usd'] for p in m['populations'])<=m['aggregate_cost_cap_usd']+1e-12
    for p in m['populations']:
        assert stable_hash(json.loads(Path(p['root'],'manifest.json').read_text()))==p['manifest_hash']
        cmd=[sys.executable,'scripts/run_reconstruct_inverse_disclosure.py','--root',p['root']]
        if args.retry_failed_once:cmd.append('--retry-failed-once')
        subprocess.run(cmd,check=True)
    print('All Z populations terminal; inspect regressions before any adoption.',flush=True)


if __name__=='__main__':main()
