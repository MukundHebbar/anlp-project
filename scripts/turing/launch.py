#!/usr/bin/env python3
"""Submit a GPU job on Turing with a GPU-hour reservation, or reconcile the ledger.

Run on the login node, from the repository root:

    python3 scripts/turing/launch.py submit --name gen-reconstruct --gpus 2 --hours 1 -- \
        python scripts/turing/teacher_gen.py --task reconstruct --out {out}
    python3 scripts/turing/launch.py reconcile

{out} becomes /scratch/$USER/anlp-opd/runs/<name> on the node. The job script, the command and a
state record are kept in runs/<name>/ in the repository copy. The ledger is turing_budget.json.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEDGER = REPO / "turing_budget.json"
NODE = "node07"
MAX_CONCURRENT_GPUS = 6  # user approval: one 3-GPU OPD job per node, on two nodes at once (2026-10-01)
SCRATCH = "/scratch/$USER/anlp-opd"

HEADER = """#!/bin/bash
#SBATCH --job-name={name}
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodelist={node}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:{gpus}
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem={mem}G
#SBATCH --time={walltime}
#SBATCH --output={rundir}/slurm-%j.out

set -euo pipefail
ROOT={scratch}
export HF_HOME=$ROOT/hf_cache HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export VLLM_CACHE_ROOT=$ROOT/vllm_cache TRITON_CACHE_DIR=$ROOT/triton_cache TORCHINDUCTOR_CACHE_DIR=$ROOT/inductor_cache
export XDG_CACHE_HOME=$ROOT/xdg_cache FLASHINFER_WORKSPACE_BASE=$ROOT/flashinfer
export PATH=$ROOT/venv/bin:$PATH
cd {repo}
mkdir -p {out}
echo "job $SLURM_JOB_ID on $(hostname) gpus $CUDA_VISIBLE_DEVICES start $(date -u +%FT%TZ)"
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader
timeout --signal=TERM --kill-after=120 {limit}s {command}
echo "end $(date -u +%FT%TZ)"
"""


def load():
    return json.loads(LEDGER.read_text())


def save(ledger):
    LEDGER.write_text(json.dumps(ledger, indent=1) + "\n")


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def job_state(job_id):
    out = sh("sacct", "-j", str(job_id), "-X", "-n", "-P", "-o", "State,ElapsedRaw,AllocTRES").strip().splitlines()
    if not out:
        return None, 0, 0
    state, elapsed, tres = out[0].split("|")
    gpus = next((int(x.split("=")[1]) for x in tres.split(",") if x.startswith("gres/gpu=")), 0)
    return state, int(elapsed or 0), gpus


def reconcile(ledger):
    for job in ledger["jobs"]:
        if job["status"] != "reserved":
            continue
        state, elapsed, gpus = job_state(job["job_id"])
        if state and not state.startswith(("PENDING", "RUNNING", "REQUEUED", "SUSPENDED")):
            job["status"] = state.split()[0].lower()
            # Whole GPU-minutes, rounded up.
            job["charged_gpu_hours"] = round(-(-elapsed * max(gpus, job["gpus"]) // 60) / 60, 3)
            job["elapsed_s"] = elapsed
    used = sum(j.get("charged_gpu_hours", 0) for j in ledger["jobs"])
    reserved = sum(j["gpus"] * j["hours"] for j in ledger["jobs"] if j["status"] == "reserved")
    ledger["used_gpu_hours"] = round(used, 3)
    ledger["reserved_gpu_hours"] = round(reserved, 3)
    ledger["remaining_gpu_hours"] = round(ledger["approved_gpu_hours"] - used - reserved, 3)
    return ledger


def submit(a, command):
    ledger = reconcile(load())
    active_gpus = sum(j["gpus"] for j in ledger["jobs"] if j["status"] == "reserved")
    need = a.gpus * a.hours
    if active_gpus + a.gpus > MAX_CONCURRENT_GPUS:
        raise SystemExit(f"refused: {active_gpus} GPUs already reserved; cap is {MAX_CONCURRENT_GPUS}")
    if need > ledger["remaining_gpu_hours"] + 1e-9:
        raise SystemExit(f"refused: needs {need} GPU-h, {ledger['remaining_gpu_hours']} left of the approval")
    rundir = REPO / "runs" / a.name
    if rundir.exists():
        raise SystemExit(f"{rundir} exists; choose a new name")
    rundir.mkdir(parents=True)
    node = a.node or NODE
    out = f"{SCRATCH}/runs/{a.name}"
    limit = int(a.hours * 3600) - 300  # internal timeout below the scheduler limit
    walltime = time.strftime("%H:%M:%S", time.gmtime(int(a.hours * 3600)))
    cmd = " ".join(c.replace("{out}", out) for c in command)
    script = HEADER.format(name=a.name, node=node, gpus=a.gpus, cpus=8 * a.gpus, mem=48 * a.gpus, walltime=walltime,
                           rundir=rundir, scratch=SCRATCH, repo=REPO, out=out, limit=limit, command=cmd)
    (rundir / "job.sbatch").write_text(script)
    job_id = sh("sbatch", "--parsable", str(rundir / "job.sbatch")).strip().split(";")[0]
    rec = {"name": a.name, "job_id": int(job_id), "gpus": a.gpus, "hours": a.hours, "node": node, "out": out,
           "command": cmd, "submitted": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "status": "reserved"}
    (rundir / "state.json").write_text(json.dumps(rec, indent=1) + "\n")
    ledger["jobs"].append(rec)
    save(reconcile(ledger))
    print(json.dumps(rec, indent=1))
    print(f"remaining after reservation: {load()['remaining_gpu_hours']} GPU-h")


def main():
    argv = sys.argv[1:]
    command = []
    if "--" in argv:
        i = argv.index("--")
        argv, command = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["submit", "reconcile"])
    ap.add_argument("--name")
    ap.add_argument("--gpus", type=int)
    ap.add_argument("--hours", type=float)
    ap.add_argument("--node", default="", help=f"compute node (default {NODE}); it needs the env and weights on its scratch")
    a = ap.parse_args(argv)
    if a.action == "reconcile":
        ledger = reconcile(load())
        save(ledger)
        print(json.dumps({k: v for k, v in ledger.items() if k != "jobs"}, indent=1))
        for j in ledger["jobs"]:
            print(j["name"], j["job_id"], j["status"], j.get("charged_gpu_hours"))
        return
    if not (a.name and a.gpus and a.hours and command):
        raise SystemExit("submit needs --name, --gpus, --hours and a command after --")
    submit(a, command)


if __name__ == "__main__":
    main()
