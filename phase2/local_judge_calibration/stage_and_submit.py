"""On the login node: wait for verified downloads, stage under a CPU allocation, then submit calibration."""
import json
from pathlib import Path
import subprocess
import time
import argparse

parser=argparse.ArgumentParser()
parser.add_argument('--model',choices=['selene','gemma'],default='selene')
parser.add_argument('--full',action='store_true')
args=parser.parse_args()

REPO=Path('/home/mukund.hebbar/anlp-project-grpo')
DEST='/scratch/mukund.hebbar/local-judge-calibration'
STAGE='/scratch/mukund.hebbar/ministral-baseline'

for name in (args.model,):
    model=Path('/tmp/mukund-anlp-local-judges')/name
    deadline=time.monotonic()+3*3600
    while not (model/'source.json').is_file():
        if time.monotonic()>deadline:
            raise RuntimeError('Download not ready: '+name)
        time.sleep(30)
    print('Verified download ready:',name,flush=True)
    marker=f'{DEST}/.stage-{name}'+('-full-ready' if args.full else '-ready')
    wrap=(f'mkdir -p {DEST}/models; for i in $(seq 300); do '
          f'[ -f {marker} ] && exit 0; sleep 3; done; exit 1')
    job=subprocess.check_output(['sbatch','--parsable','--account=priyesh.shukla','--partition=u22',
        '--nodelist=node08','--nodes=1','--ntasks=1','--cpus-per-task=1','--mem=2G','--time=00:15:00',
        '--chdir=/tmp',f'--job-name=stage-cal-{name}',f'--output={STAGE}/stage-{name}-%j.out',
        '--wrap',wrap],text=True).strip().split(';')[0]
    print('CPU staging job',job,flush=True)
    while True:
        state=subprocess.check_output(['squeue','-h','-j',job,'-o','%T'],text=True).strip()
        if state=='RUNNING': break
        if not state: raise RuntimeError('CPU staging allocation ended before transfer')
        time.sleep(3)
    try:
        subprocess.run(['ssh','-o','BatchMode=yes','node08',f'mkdir -p {DEST}/models/{name}'],check=True)
        if not args.full:
            subprocess.run(['rsync','-a','--exclude=.cache',str(model)+'/',f'node08:{DEST}/models/{name}/'],check=True)
        archive='/tmp/mukund-calibration-full-code.tar.gz' if args.full else '/tmp/mukund-calibration-code.tar.gz'
        subprocess.run(['scp','-q',archive,f'node08:{DEST}/code.tar.gz'],check=True)
        subprocess.run(['ssh','-o','BatchMode=yes','node08',
                        f'tar -xzf {DEST}/code.tar.gz -C {STAGE}/repo; touch {marker}'],check=True)
    except Exception:
        subprocess.run(['scancel',job])
        raise
    result=subprocess.check_output(['python3',str(REPO/'phase2/ministral_baseline/submit_calibration.py'),name]+
                                   (['--full'] if args.full else []),
                                   cwd=REPO,text=True)
    print(result,flush=True)
print('REQUESTED_CALIBRATION_SUBMITTED',flush=True)
