"""Unattended preparation: download -> staging -> verified smoke -> baseline and LR probes."""
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
HOST='mukund.hebbar@turing.iiit.ac.in'
HOME_REPO='/home/mukund.hebbar/anlp-project-grpo'
REMOTE='/scratch/node08/mukund.hebbar/llama-transfer'
LOCAL=ROOT/'local/llama-transfer'


def ssh(command,**kwargs):
    return subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',HOST,command],**kwargs)


def state(stage):
    suffix='-r2' if stage=='smoke' else ''
    return json.loads(ssh(f'cat {HOME_REPO}/runs/llama3b-{stage}-20261028{suffix}/state.json',
                          capture_output=True,text=True,check=True).stdout)


def wait_job(stage,record):
    job=record['job_id']
    ssh(f'sbatch --wait --parsable --account=priyesh.shukla --partition=u22 --nodelist=node08 '
        f'--nodes=1 --ntasks=1 --cpus-per-task=1 --mem=1G --time=00:01:00 --chdir=/tmp '
        f'--dependency=afterany:{job} --job-name=llama-{stage}-finished '
        f'--output=/scratch/mukund.hebbar/llama-transfer/{stage}-finished-%j.out --wrap=true',check=True)
    destination=LOCAL/stage;destination.mkdir(parents=True,exist_ok=True)
    subprocess.run(['rsync','-az','--exclude=adapters','--exclude=optimizer.pt',
                    f"{HOST}:{record['out'].replace('/scratch/', '/scratch/node08/', 1)}/",str(destination)+'/'],check=True)
    subprocess.run(['scp','-q',f'{HOST}:{REMOTE}/slurm-{job}.out',str(destination/f'slurm-{job}.out')],check=True)
    status=ssh(f'sacct -j {job} -X -n -P -o State,Elapsed,ExitCode',capture_output=True,text=True,check=True).stdout
    (destination/'job-status.txt').write_text(status)
    if not status.startswith('COMPLETED|') or not (destination/'done').exists():
        raise RuntimeError(f'{stage} job {job} failed: {status.strip()}; inspect collected logs before retrying')
    ssh(f'cd {HOME_REPO} && python3 scripts/turing/launch.py reconcile',capture_output=True,check=True)


def main():
    LOCAL.mkdir(parents=True,exist_ok=True)
    print('Waiting for verified CPU download/staging; no GPU allocated during download.',flush=True)
    ssh(f'cd {HOME_REPO} && python3 phase2/llama_transfer/submit.py smoke',check=True)
    smoke=state('smoke')
    print('LLAMA_SMOKE_SUBMITTED',smoke['job_id'],flush=True)
    wait_job('smoke',smoke)
    print('LLAMA_SMOKE_PASSED',flush=True)
    jobs={}
    for stage in ('baseline','probes'):
        ssh(f'cd {HOME_REPO} && python3 phase2/llama_transfer/submit.py {stage}',check=True)
        jobs[stage]=state(stage)
        print('LLAMA_STAGE_SUBMITTED',stage,jobs[stage]['job_id'],flush=True)
    (LOCAL/'jobs.json').write_text(json.dumps({'smoke':smoke,**jobs},indent=2))
    for stage,record in jobs.items():wait_job(stage,record)
    print('LLAMA_BASELINE_AND_PROBES_COMPLETE',flush=True)


if __name__=='__main__':main()
