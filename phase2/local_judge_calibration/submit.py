"""Submit one judge calibration through the project ledger, using node08 scratch paths."""
import argparse
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('launch',ROOT/'scripts/turing/launch.py')
launch=importlib.util.module_from_spec(spec);spec.loader.exec_module(launch)
p=argparse.ArgumentParser();p.add_argument('model',choices=['selene','gemma'])
p.add_argument('--full',action='store_true');a=p.parse_args()
stage='/scratch/mukund.hebbar/ministral-baseline'
out='/scratch/mukund.hebbar/local-judge-calibration'
result_name='gemma-full-explicit' if a.full else ('gemma-screen' if a.model=='gemma' else a.model)
launch.OUT_ROOT=Path(out)/'job-output'
launch.HEADER=launch.HEADER.replace('#SBATCH --partition=u22','#SBATCH --partition=u22\n#SBATCH --chdir=/tmp')
launch.HEADER=launch.HEADER.replace('#SBATCH --output={rundir}/slurm-%j.out',f'#SBATCH --output={stage}/slurm-%j.out')
launch.HEADER=launch.HEADER.replace('cd {repo}','cd /tmp')
request_option = (' --requests artifacts/local-judge-calibration/gemma-screen-requests.jsonl'
                  if a.model=='gemma' and not a.full else '')
if a.full:
    request_option = ' --label-protocol explicit'
command=(f'cd {stage}/repo; export ANLP_PYTHON={stage}/python/bin/python3.12; '
         f'exec bash phase2/failure_driven/scripts/env.sh python phase2/local_judge_calibration/infer.py '
         f'--name {a.model} --model-path {out}/models/{a.model} --out {out}/{result_name}{request_option}')
job_name = ('calibrate-gemma-screen-20261027' if a.model=='gemma'
            else 'calibrate-selene-historical-20261027')
if a.full:
    job_name='calibrate-gemma-full-20261027'
launch.submit(argparse.Namespace(name=job_name,node='node08',gpus=1,
                                 hours=.5 if a.full else (.25 if a.model=='gemma' else 2.0),after=''),['bash','-c',command])
