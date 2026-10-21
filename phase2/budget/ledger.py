#!/usr/bin/env python3
"""GPU-hour ledger for the Phase-2b runs (approved 2026-10-20: 40 GPU-hours, at most 4 GPUs at once).

Every job is submitted through this script, which reserves gpus x walltime before calling sbatch and refuses the
job if the reservation would exceed the budget or the concurrent-GPU cap. `reconcile` replaces reservations of
finished jobs with Slurm-charged usage (sacct ElapsedRaw x GPUs).

    python phase2/budget/ledger.py submit --name NAME --gpus N --hours H -- <sbatch args...>
    python phase2/budget/ledger.py reconcile
    python phase2/budget/ledger.py status
"""

import argparse, json, re, subprocess, sys, time
from pathlib import Path

LEDGER = Path(__file__).with_name("gpu_ledger.json")
HOST = "yashas.kotre@turing.iiit.ac.in"
REMOTE_REPO = "~/anlp-project-phase2"


def ssh(cmd: str) -> str:
    return subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, cmd], capture_output=True, text=True, check=True,
                          timeout=120).stdout


def load():
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"description": "Phase-2b GPU ledger. Approved by the user on 2026-10-20: 40 GPU-hours, never more than "
                           "4 GPUs at once (running and pending jobs included).",
            "approved_gpu_hours": 40.0, "max_concurrent_gpus": 4, "jobs": []}


def save(d):
    open_ = [j for j in d["jobs"] if j["status"] in ("submitted", "running", "pending")]
    d["charged_gpu_hours"] = round(sum(j.get("charged_gpu_hours", 0) for j in d["jobs"]), 3)
    d["reserved_gpu_hours"] = round(sum(j["reserved_gpu_hours"] for j in open_), 3)
    d["remaining_gpu_hours"] = round(d["approved_gpu_hours"] - d["charged_gpu_hours"] - d["reserved_gpu_hours"], 3)
    LEDGER.write_text(json.dumps(d, indent=1) + "\n")


def reconcile(d):
    ids = [str(j["job_id"]) for j in d["jobs"] if j["status"] in ("submitted", "running", "pending")]
    if ids:
        out = ssh(f"sacct -j {','.join(ids)} -X -n -P -o JobID,State,ElapsedRaw,AllocTRES")
        for line in out.strip().splitlines():
            jid, state, el, tres = line.split("|")
            j = next(x for x in d["jobs"] if str(x["job_id"]) == jid)
            gpus = next((int(t.split("=")[1]) for t in tres.split(",") if t.startswith("gres/gpu=")), j["gpus"])
            j["elapsed_s"] = int(el or 0)
            if state in ("RUNNING",):
                j["status"] = "running"
            elif state == "PENDING":
                j["status"] = "pending"
            else:
                j["status"] = state.lower().split()[0]
                j["charged_gpu_hours"] = round(gpus * int(el or 0) / 3600, 3)
    save(d)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["submit", "reconcile", "status"])
    ap.add_argument("--name")
    ap.add_argument("--gpus", type=int)
    ap.add_argument("--hours", type=float)
    argv = sys.argv[1:]
    rest = argv[argv.index("--") + 1:] if "--" in argv else []
    argv = argv[:argv.index("--")] if "--" in argv else argv
    a = ap.parse_args(argv)
    a.rest = rest
    d = reconcile(load())
    if a.cmd == "submit":
        open_ = [j for j in d["jobs"] if j["status"] in ("submitted", "running", "pending")]
        reserve = a.gpus * a.hours
        if sum(j["gpus"] for j in open_) + a.gpus > d["max_concurrent_gpus"]:
            sys.exit(f"refused: {sum(j['gpus'] for j in open_)} GPUs already running/pending + {a.gpus} > {d['max_concurrent_gpus']}")
        if reserve > d["remaining_gpu_hours"]:
            sys.exit(f"refused: reservation {reserve:.2f} GPU-h > remaining {d['remaining_gpu_hours']:.2f}")
        rest = a.rest
        hh, mm = int(a.hours), int(round((a.hours - int(a.hours)) * 60))
        cmd = (f"cd {REMOTE_REPO} && mkdir -p phase2/runs && sbatch --parsable --gres=gpu:{a.gpus} "
               f"--time={hh:02d}:{mm:02d}:00 --job-name={a.name} " + " ".join(rest))
        jid = ssh(cmd).strip().split(";")[0]
        d["jobs"].append({"name": a.name, "job_id": int(jid), "gpus": a.gpus, "walltime_h": a.hours,
                          "reserved_gpu_hours": round(reserve, 3), "status": "submitted",
                          "submitted": time.strftime("%Y-%m-%dT%H:%M:%S"), "command": " ".join(rest)})
        save(d)
        print(f"submitted {jid}; reserved {reserve:.2f} GPU-h")
    print(json.dumps({k: d[k] for k in ("approved_gpu_hours", "charged_gpu_hours", "reserved_gpu_hours",
                                        "remaining_gpu_hours")}))


if __name__ == "__main__":
    main()
