"""Stage, run and collect the full historical Gemma calibration without manual polling."""
import json
from pathlib import Path
import subprocess
import sys

from run_gemma_background import ssh, ROOT, HOST, REPO

NAME = 'gemma-full-explicit'
STATE = REPO + '/runs/calibrate-gemma-full-20261027/state.json'
REMOTE = '/scratch/node08/mukund.hebbar/local-judge-calibration/' + NAME
OUT = ROOT / 'local/local-judge-calibration' / NAME


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    existing = ssh('cat ' + STATE, capture_output=True, text=True)
    if existing.returncode:
        ssh('python3 -u /tmp/mukund-cal-stage-submit-full.py --model gemma --full', check=True)
    state = json.loads(ssh('cat ' + STATE, capture_output=True, text=True, check=True).stdout)
    job = int(state['job_id'])
    print('Full Gemma calibration submitted:', job, flush=True)
    ssh(f'sbatch --wait --parsable --account=priyesh.shukla --partition=u22 --nodelist=node08 '
        f'--nodes=1 --ntasks=1 --cpus-per-task=1 --mem=1G --time=00:01:00 --chdir=/tmp '
        f'--dependency=afterany:{job} --job-name=gemma-full-finished '
        f'--output=/scratch/mukund.hebbar/ministral-baseline/gemma-full-finished-%j.out --wrap=true', check=True)
    subprocess.run(['rsync', '-az', f'{HOST}:{REMOTE}/', str(OUT) + '/'], check=True)
    subprocess.run(['scp', '-q', f'{HOST}:/scratch/node08/mukund.hebbar/ministral-baseline/slurm-{job}.out',
                    str(OUT / f'slurm-{job}.out')], check=True)
    if not (OUT / 'done').exists():
        raise RuntimeError(f'Job {job} failed; inspect the saved Slurm log before retrying.')
    import fit
    import audit_reconstruct
    fit.run(NAME, OUT)
    audit_reconstruct.audit(NAME, OUT / 'answers.jsonl')
    summary = json.loads((ROOT / 'phase2/results/local-judge-calibration' / NAME / 'summary.json').read_text())
    # Match successful complete response groups for both models; never compare different held-out subsets.
    successful = {r['key'] for r in fit.read(OUT / 'answers.jsonl') if r.get('ok')}
    requests = fit.read(ROOT / 'artifacts/qwen-judge-calibration/requests.jsonl')
    groups = {}
    for request in requests:
        groups.setdefault(request['key'].rsplit('|', 1)[0], set()).add(request['key'])
    complete = {key for keys in groups.values() if keys <= successful for key in keys}
    reference = ROOT / 'local/local-judge-calibration/qwen27b-full-matched'
    reference.mkdir(parents=True, exist_ok=True)
    rows = [r for r in fit.read(ROOT / 'artifacts/qwen-judge-calibration/answers.jsonl') if r['key'] in complete]
    (reference / 'answers.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    fit.run('qwen27b-full-matched', reference)
    audit_reconstruct.audit('qwen27b-full-matched', reference / 'answers.jsonl')
    with (OUT / 'budget-reconciled.txt').open('w') as output:
        ssh('cd ' + REPO + ' && python3 scripts/turing/launch.py reconcile', stdout=output, check=True)
    print('GEMMA_FULL_COMPLETE', json.dumps(summary['heldout_total_scores']), flush=True)


if __name__ == '__main__':
    main()
