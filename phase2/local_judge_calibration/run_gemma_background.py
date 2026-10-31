"""Finish the Gemma screen unattended; wait on a Slurm dependency instead of polling the GPU job."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
HOST='mukund.hebbar@turing.iiit.ac.in'
REPO='/home/mukund.hebbar/anlp-project-grpo'
STATE=REPO+'/runs/calibrate-gemma-screen-20261027/state.json'
REMOTE='/scratch/node08/mukund.hebbar/local-judge-calibration/gemma-screen'
OUT=ROOT/'local/local-judge-calibration/gemma-screen'
OUT.mkdir(parents=True,exist_ok=True)


def ssh(command,**kwargs):
    return subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',HOST,command],**kwargs)


def main():
    existing=ssh('cat '+STATE,capture_output=True,text=True)
    if existing.returncode:
        print('Waiting for verified model download and CPU staging; no GPU is allocated for this wait.',flush=True)
        ssh('python3 -u /tmp/mukund-cal-stage-submit.py --model gemma',check=True)
    state=json.loads(ssh('cat '+STATE,capture_output=True,text=True,check=True).stdout)
    job=int(state['job_id'])
    print('Gemma GPU job submitted:',job,flush=True)
    # --wait blocks until this tiny dependent CPU job finishes; no repeated squeue/sacct requests.
    command=(f'sbatch --wait --parsable --account=priyesh.shukla --partition=u22 --nodelist=node08 '
             f'--nodes=1 --ntasks=1 --cpus-per-task=1 --mem=1G --time=00:01:00 --chdir=/tmp '
             f'--dependency=afterany:{job} --job-name=gemma-screen-finished '
             f'--output=/scratch/mukund.hebbar/ministral-baseline/gemma-finished-%j.out --wrap=true')
    ssh(command,check=True)
    subprocess.run(['rsync','-az',f'{HOST}:{REMOTE}/',str(OUT)+'/'],check=True)
    subprocess.run(['scp','-q',f'{HOST}:/scratch/node08/mukund.hebbar/ministral-baseline/slurm-{job}.out',
                    str(OUT/f'slurm-{job}.out')],check=True)
    if not (OUT/'done').is_file():
        raise RuntimeError(f'Gemma job {job} did not complete calibration; see its saved log.')
    subprocess.run([sys.executable,str(ROOT/'phase2/local_judge_calibration/fit.py'),
                    '--name','gemma-screen','--folder',str(OUT)],cwd=ROOT,check=True)
    sys.path.insert(0,str(ROOT/'phase2/local_judge_calibration'))
    import audit_reconstruct
    audit=audit_reconstruct.audit('gemma-screen',OUT/'answers.jsonl')
    reference=audit_reconstruct.audit('qwen27b-screen-reference',
        ROOT/'local/local-judge-calibration/qwen27b-screen-reference/answers.jsonl')
    dest=ROOT/'phase2/results/local-judge-calibration/gemma-screen'
    gemma=json.loads((dest/'summary.json').read_text())
    qwen=json.loads((ROOT/'phase2/results/local-judge-calibration/qwen27b-screen-reference/summary.json').read_text())
    def fmt(value):return 'undefined' if value is None else f'{value:.3f}'
    lines=['# Gemma 4 12B: light calibration screen','',
           'Frozen sample: 12 responses per task per historical checkpoint; 96 JUDGE and 96 RECONSTRUCT responses. '
           'Four checkpoints fit thresholds, four evaluate them (48 held-out responses per task). '
           'No new reference API calls. This is a small screen, not proof of equivalence.','',
           '| Held-out correlation with saved reference labels | Gemma 12B | Qwen27B, same subset |',
           '|---|---:|---:|']
    for task in ('judge','reconstruct'):
        lines.append(f"| {task}, total calibrated score with gates | "
                     f"{fmt(gemma['heldout_total_scores'][task]['pearson_r'])} | "
                     f"{fmt(qwen['heldout_total_scores'][task]['pearson_r'])} |")
    lines += [f"| RECONSTRUCT continuous rubric-only, reference non-shortcuts | "
              f"{fmt(audit['reference_non_shortcuts']['continuous_rubric_only']['pearson_r'])} | "
              f"{fmt(reference['reference_non_shortcuts']['continuous_rubric_only']['pearson_r'])} |",'',
              'Shortcut classification and rubric-only grading are audited separately in `reconstruct-audit.json`. '
              'The production scoring function and the calibration aggregation must match exactly. '
              'Qwen27B remains the final evaluator; no training job is started by this screen.','']
    (dest/'comparison.md').write_text('\n'.join(lines))
    (dest/'selection.json').write_text((ROOT/'phase2/local_judge_calibration/gemma-screen-selection.json').read_text())
    with (OUT/'budget-reconciled.txt').open('w') as output:
        ssh('cd '+REPO+' && python3 scripts/turing/launch.py reconcile',stdout=output,check=True)
    print('\n'.join(lines),flush=True)
    print('GEMMA_SCREEN_COMPLETE',flush=True)


if __name__=='__main__':
    main()
