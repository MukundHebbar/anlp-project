"""Wait for the authorized baseline job, back up outputs, validate them and build its report."""
import argparse
import gzip
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HOST = "mukund.hebbar@turing.iiit.ac.in"
REMOTE = "/scratch/node08/mukund.hebbar/ministral-baseline"
LOCAL = ROOT / "local/ministral-baseline"


def ssh(command, **kwargs):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST,
                           command], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-id", type=int, required=True)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    LOCAL.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 4 * 3600
    failures = 0
    while True:
        try:
            status = ssh(f"sacct -j {args.job_id} -X -n -P -o State,ElapsedRaw,AllocTRES",
                         capture_output=True, text=True).stdout.strip().splitlines()
            failures = 0
        except subprocess.CalledProcessError:
            failures += 1
            if failures >= 5 or not args.watch:
                raise
            time.sleep(30)
            continue
        state = status[0].split("|")[0] if status else "UNKNOWN"
        print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), state, flush=True)
        if state not in ("PENDING", "RUNNING", "COMPLETING", "UNKNOWN", "REQUEUED", "SUSPENDED"):
            break
        if not args.watch or time.monotonic() >= deadline:
            raise SystemExit("Job still active; run collection again when it finishes.")
        time.sleep(45)

    for folder in ("smoke-dev", "test"):
        subprocess.run(["rsync", "-az", "--exclude=responses*.jsonl",
                        f"{HOST}:{REMOTE}/{folder}/", str(LOCAL / folder) + "/"], check=True)
    for name in (f"slurm-{args.job_id}.out", "slurm-52279.out", "runtime-freeze.txt", "model-source.json"):
        subprocess.run(["scp", "-q", f"{HOST}:{REMOTE}/{name}", str(LOCAL / name)], check=True)
    (LOCAL / "job-accounting.txt").write_text("\n".join(status) + "\n")
    if state != "COMPLETED":
        raise SystemExit(f"Job {args.job_id} ended as {state}; logs backed up, no completed result reported.")

    destination = LOCAL / "test/responses-solve.jsonl.gz"
    with destination.open("wb") as output:
        ssh("gzip -c " + shlex.quote(REMOTE + "/test/responses-solve.jsonl"), stdout=output)
    sys.path.insert(0, str(ROOT / "src"))
    from anlp_project import baseline
    rows = baseline.rows_for("test", ["solve"])
    prompts = {row["uid"]: baseline.render_prompt(row) for row in rows}
    seen = set()
    with gzip.open(destination, "rt") as handle:
        for line in handle:
            response = json.loads(line)
            assert response["prompt"] == prompts[response["uid"]]
            assert response["task"] == "solve" and response["sample"] in range(4)
            key = (response["uid"], response["sample"])
            assert key not in seen
            seen.add(key)
    assert len(seen) == 1600 and len(prompts) == 400
    assert (LOCAL / "test/done").read_text().strip() == "ok"
    subprocess.run([sys.executable, str(ROOT / "phase2/ministral_baseline/report.py")],
                   cwd=ROOT, check=True)
    ssh("cd /home/mukund.hebbar/anlp-project-grpo && python3 scripts/turing/launch.py reconcile",
        stdout=(LOCAL / "budget-reconciled.txt").open("w"))
    print("Collected and validated 400 questions x 4 samples; report saved.", flush=True)


if __name__ == "__main__":
    main()
