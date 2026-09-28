#!/usr/bin/env python3
"""Judge terminal AA student draws, keeping source-blind grounding separate."""
import argparse,json,subprocess,sys
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--study-root',type=Path,default=Path('artifacts/reconstruct/richer-exposure-aa'));args=parser.parse_args()
root=args.study_root;p=root/'student.json';r=json.loads(p.read_text())
assert set(r['metadata']['jobs'])==set(r['metadata']['attempted_jobs'])
terminal=set(r['responses']) | {f['key'] for f in r['failures'] if f['stage']=='student'}
assert set(r['metadata']['jobs'])<=terminal, 'Student requests still in flight; attempted does not mean terminal'
for command,flag,prompt in [('evaluate','--evaluate-prompt','evaluate_p3'),('recover','--recovery-prompt','source_recovery_p2')]:
    subprocess.run([sys.executable,'scripts/run_reconstruct_batch.py','--workers','4','--',command,'--output',str(p),flag,prompt,'--teacher-max-tokens','8192','--reasoning-effort','low','--timeout','180','--max-cost-usd',str(r['metadata']['maximum_substudy_cost_usd'])],check=True)
print('All AA judgments terminal; manual response review still required',flush=True)
