#!/usr/bin/env python3
"""Several OPD runs on one node sharing one teacher: teacher on two GPUs, each run on one GPU.

    python scripts/turing/opd_shared.py --teacher-gpus 2,3 \
        --run "0|<out solve>|--task solve --config matrix --steps 156 --init-adapter <sft>/adapter" \
        --run "1|<out judge>|--task judge --config matrix --steps 156 --init-adapter <sft>/adapter"

Each --run is "<gpu>|<out dir>|<opd_run.py arguments>". The teacher is the same server and settings
as in a single run (opd_train.serve_teacher), with twice the concurrent sequences. The script exits
non-zero if any run fails; the teacher stops when every run has finished.
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from anlp_project import opd  # noqa: E402
from anlp_project.opd_train import serve_teacher, wait_ready  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--teacher-gpus", required=True)
    ap.add_argument("--teacher-port", type=int, default=8001)
    ap.add_argument("--log-dir", required=True)
    ap.add_argument("--run", action="append", required=True)
    ap.add_argument("--wait-for", action="append", default=[],
                    help="keep the teacher up until this file exists (a remote run's result file)")
    ap.add_argument("--cap", type=int, default=0, help="rollout cap of the runs (sets the teacher's context length)")
    ap.add_argument("--config", default="matrix", choices=["matrix", "opd9b"], help="opd9b: the Qwen3.5-9B teacher")
    ap.add_argument("--teacher-tp", type=int, default=0, help="tensor parallel size (default: 1 for opd9b, else 2)")
    a = ap.parse_args()
    from huggingface_hub import snapshot_download

    log_dir = Path(a.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    cfg = opd.OPD9B_CONFIG if a.config == "opd9b" else opd.MATRIX_CONFIG
    cap = a.cap or max(cfg["rollout_max_tokens"].values())
    teacher = serve_teacher(snapshot_download(cfg["teacher"], local_files_only=True), a.teacher_port, a.teacher_gpus,
                            a.teacher_tp or (1 if a.config == "opd9b" else 2),
                            0.90, cap + 4096, cfg, log_dir,
                            max_seqs=cfg["prompts_per_step"] * (len(a.run) + len(a.wait_for)))
    print(f"teacher ready in {wait_ready(a.teacher_port, teacher, 'teacher', log_dir)} s", flush=True)
    procs = []
    try:
        for k, spec in enumerate(a.run):
            gpu, out, args = spec.split("|", 2)
            Path(out).mkdir(parents=True, exist_ok=True)
            cmd = [sys.executable, str(Path(__file__).with_name("opd_run.py")), "--out", out, *shlex.split(args),
                   "--external-teacher", "--teacher-port", str(a.teacher_port), "--student-port", str(8100 + k)]
            env = {**os.environ, "CUDA_VISIBLE_DEVICES": gpu}
            procs.append((out, subprocess.Popen(cmd, env=env, stdout=open(Path(out) / "run.log", "a"),
                                                stderr=subprocess.STDOUT)))
            print(f"started run {k} on GPU {gpu}: {out}", flush=True)
        (log_dir / "teacher-host").write_text(os.uname().nodename + "\n")
        codes = {}
        while len(codes) < len(procs) or not all(Path(w).exists() for w in a.wait_for):
            for out, p in procs:
                if out not in codes and p.poll() is not None:
                    codes[out] = p.returncode
                    print(f"{out} exited {p.returncode}", flush=True)
            if teacher.poll() is not None:
                raise SystemExit("teacher server died")
            time.sleep(20)
    finally:
        for _, p in procs:
            if p.poll() is None:
                p.terminate()
        teacher.terminate()
    print(json.dumps(codes, indent=1))
    raise SystemExit(0 if all(c == 0 for c in codes.values()) else 1)


if __name__ == "__main__":
    main()
