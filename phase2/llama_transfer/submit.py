"""Submit one Llama job through the existing GPU ledger (scripts/turing/launch.py), run on the Turing login node:
the job enters the node's staged repo (stage.sh) and the experiment environment (env.sh).

    python3 phase2/llama_transfer/submit.py --name llama3b-judge --node node08 --gpus 3 --hours 9 -- \
        python phase2/llama_transfer/arm.py judge
"""
import argparse
import importlib.util
import shlex
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('project_launcher',ROOT/'scripts/turing/launch.py')
launch=importlib.util.module_from_spec(spec);spec.loader.exec_module(launch)
BASE='/scratch/mukund.hebbar/llama-transfer'
REPO=BASE+'/repo'
RUNTIME='/scratch/mukund.hebbar/ministral-baseline/python/bin/python3.12'  # node08 does not mount the home folder


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--name',required=True);p.add_argument('--node',required=True)
    p.add_argument('--gpus',type=int,required=True);p.add_argument('--hours',type=float,required=True)
    p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args()
    command=a.command[1:] if a.command[:1]==['--'] else a.command
    launch.OUT_ROOT=Path(BASE)/'runs'
    launch.HEADER=launch.HEADER.replace('#SBATCH --partition=u22','#SBATCH --partition=u22\n#SBATCH --chdir=/tmp')
    launch.HEADER=launch.HEADER.replace('#SBATCH --output={rundir}/slurm-%j.out',f'#SBATCH --output={BASE}/slurm-%j.out')
    launch.HEADER=launch.HEADER.replace('cd {repo}','cd /tmp')
    wrapped=(f'cd {REPO}; [ -x {RUNTIME} ] && export ANLP_PYTHON={RUNTIME}; '
             f'exec bash phase2/failure_driven/scripts/env.sh {shlex.join(command)}')
    launch.submit(argparse.Namespace(name=a.name,node=a.node,gpus=a.gpus,hours=a.hours,after=''),['bash','-c',wrapped])


if __name__=='__main__':main()
