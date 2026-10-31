"""Wait for the verified CPU download, stage isolated code/weights, then submit the smoke job."""
from pathlib import Path
import subprocess
import time

HOME_REPO=Path('/home/mukund.hebbar/anlp-project-grpo')
BASE='/scratch/mukund.hebbar/llama-transfer'
SOURCE=Path('/tmp/mukund-anlp-llama-transfer/llama')


def main():
    deadline=time.monotonic()+3*3600
    while not (SOURCE/'source.json').exists():
        if time.monotonic()>deadline:raise RuntimeError('Llama download did not complete within three hours')
        time.sleep(30)
    print('Verified Llama download ready; requesting CPU-only staging allocation.',flush=True)
    marker=BASE+'/.stage-ready-20261028'
    wrap=f'mkdir -p {BASE}; for i in $(seq 400); do [ -f {marker} ] && exit 0; sleep 3; done; exit 1'
    job=subprocess.check_output(['sbatch','--parsable','--account=priyesh.shukla','--partition=u22',
        '--nodelist=node08','--nodes=1','--ntasks=1','--cpus-per-task=1','--mem=2G','--time=00:20:00',
        '--chdir=/tmp','--job-name=stage-llama3b','--output=/tmp/mukund-stage-llama-%j.out','--wrap',wrap],text=True).strip().split(';')[0]
    while True:
        state=subprocess.check_output(['squeue','-h','-j',job,'-o','%T'],text=True).strip()
        if state=='RUNNING':break
        if not state:raise RuntimeError('CPU staging allocation ended before transfer')
        time.sleep(3)
    try:
        subprocess.run(['ssh','-o','BatchMode=yes','node08',f'mkdir -p {BASE}/models/llama {BASE}/repo'],check=True)
        subprocess.run(['rsync','-a','--exclude=.cache',str(SOURCE)+'/',f'node08:{BASE}/models/llama/'],check=True)
        subprocess.run(['scp','-q','/tmp/mukund-llama-code.tar',f'node08:{BASE}/code.tar'],check=True)
        subprocess.run(['ssh','-o','BatchMode=yes','node08',
                        f'tar -xf {BASE}/code.tar -C {BASE}/repo; touch {marker}'],check=True)
    except Exception:
        subprocess.run(['scancel',job]);raise
    subprocess.run(['python3',str(HOME_REPO/'phase2/llama_transfer/submit.py'),'smoke'],cwd=HOME_REPO,check=True)


if __name__=='__main__':main()
