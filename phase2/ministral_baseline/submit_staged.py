"""Use the existing GPU ledger/launcher with scratch paths on a node lacking the home mount."""
import argparse
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("turing_launch", ROOT / "scripts/turing/launch.py")
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)

STAGE = "/scratch/mukund.hebbar/ministral-baseline"
launch.OUT_ROOT = Path(STAGE) / "job-output"
launch.HEADER = launch.HEADER.replace("#SBATCH --partition=u22", "#SBATCH --partition=u22\n#SBATCH --chdir=/tmp")
launch.HEADER = launch.HEADER.replace("#SBATCH --output={rundir}/slurm-%j.out",
                                    f"#SBATCH --output={STAGE}/slurm-%j.out")
launch.HEADER = launch.HEADER.replace("cd {repo}", "cd /tmp")
command = (f"for i in $(seq 240); do [ -f {STAGE}/.staged-ready ] && break; sleep 10; done; "
           f"test -f {STAGE}/.staged-ready || exit 1; cd {STAGE}/repo; "
           f"export ANLP_PYTHON={STAGE}/python/bin/python3.12; "
           f"export ANLP_MINISTRAL_MODEL_PATH={STAGE}/model; "
           "exec bash phase2/ministral_baseline/run.sh")
parser = argparse.ArgumentParser()
parser.add_argument("--name", default="ministral-instruct-bf16-solve-node08-20261027")
args = parser.parse_args()
launch.submit(argparse.Namespace(name=args.name, node="node08",
                                 gpus=1, hours=3.0, after=""), ["bash", "-c", command])
