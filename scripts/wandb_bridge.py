#!/usr/bin/env python3
"""Mirror Turing run metrics to Weights & Biases and print notable events (runs on the laptop).

    .venv/bin/python scripts/wandb_bridge.py --project anlp-transfer --group matrix-v1 --runs 'opd-*,sft-*,gen-*,eval-*'

Every --interval seconds: rsync the small files (metrics, events, configs, summaries) of
~/anlp-project/runs-out/<run>/ from Turing into local/turing-mirror/, log new metric rows to one
W&B run per Turing run (resumed by name), log eval summaries once, and print one line per notable
event: every 8th OPD step, errors, auto-stops and Slurm job state changes. Training never depends
on this process; metrics.jsonl on Turing stays the source of truth.
"""

import argparse
import fnmatch
import json
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MIRROR = REPO / "local" / "turing-mirror"
INCLUDE = ["metrics.jsonl", "events.log", "config.json", "filter.json", "summary.json", "metadata.json",
           "timing-*.json", "result-*.json", "run.log", "judged-summary.json"]


def flat(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flat(v, key + "/"))
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out[key] = v
        elif isinstance(v, bool):
            out[key] = int(v)
    return out


def sync(host):
    args = ["rsync", "-az", "--prune-empty-dirs", "--include", "*/"]
    for pat in INCLUDE:
        args += ["--include", pat]
    args += ["--exclude", "*", f"{host}:anlp-project/runs-out/", str(MIRROR) + "/"]
    subprocess.run(args, capture_output=True, timeout=600)


def squeue(host):
    r = subprocess.run(["ssh", host, "squeue -u $USER -h -o '%i|%j|%T|%M|%N'"], capture_output=True, text=True, timeout=60)
    return {l.split("|")[0]: l.split("|")[1:] for l in r.stdout.strip().splitlines() if l}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="turing")
    ap.add_argument("--project", default="anlp-transfer")
    ap.add_argument("--group", default="matrix-v1")
    ap.add_argument("--runs", default="*", help="comma-separated glob patterns of run names")
    ap.add_argument("--interval", type=int, default=60)
    a = ap.parse_args()
    import wandb

    MIRROR.mkdir(parents=True, exist_ok=True)
    state_path = MIRROR / ".bridge-state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"rows": {}, "events": {}, "evals": []}
    runs, jobs = {}, {}
    pats = a.runs.split(",")
    while True:
        try:
            sync(a.host)
            now = squeue(a.host)
        except Exception as e:  # network trouble: retry next round
            print(f"bridge: sync failed ({type(e).__name__})", flush=True)
            time.sleep(a.interval)
            continue
        for jid, (name, st, el, node) in now.items():
            if jobs.get(jid, [None, None])[1] != st:
                print(f"job {jid} {name}: {st} on {node} ({el})", flush=True)
        for jid, (name, st, *_ ) in jobs.items():
            if jid not in now:
                print(f"job {jid} {name}: left the queue (finished, failed or cancelled)", flush=True)
        jobs = now
        for d in sorted(p for p in MIRROR.iterdir() if p.is_dir()):
            name = d.name
            if not any(fnmatch.fnmatch(name, p) for p in pats):
                continue
            for m in [d / "metrics.jsonl", *d.glob("*/metrics.jsonl")]:  # opd_shared runs nest one level
                if not m.exists():
                    continue
                rname = m.parent.name if m.parent != d else name
                key = str(m.relative_to(MIRROR))
                rows = [json.loads(l) for l in m.open() if l.strip()]
                done = state["rows"].get(key, 0)
                if len(rows) <= done:
                    continue
                if key not in runs:
                    cfg_path = m.parent / "config.json"
                    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
                    cfg = {k: v for k, v in cfg.items() if not isinstance(v, str) or len(v) < 300}
                    kind = rname.split("-")[0]
                    task = cfg.get("task") or next((t for t in ("solve", "judge", "reconstruct") if t in rname), "")
                    try:
                        runs[key] = wandb.init(project=a.project, group=a.group, name=rname, id="m2-" + str(m.parent.relative_to(MIRROR)).replace("/", "__")[:120],
                                               resume="allow", job_type=kind, config=cfg, reinit="create_new",
                                               tags=[t for t in (kind, task) if t])
                    except Exception as e:  # one bad run must not stop the bridge
                        print(f"bridge: wandb init failed for {rname}: {e}", flush=True)
                        continue
                for r in rows[done:]:
                    step = r.get("step", 0)
                    runs[key].log(flat({k: v for k, v in r.items() if k != "gpu_memory"}), step=step)
                    if "rollouts_used" in r and (step % 8 == 0 or step <= 3):
                        print(f"{rname} step {step}: len {r['mean_len']:.0f} trunc {r['truncation_rate']:.2f} "
                              f"rep {r['repetition']:.2f} rkl {r['reverse_kl']:.3f} gap {r['mean_abs_logprob_gap']:.3f} "
                              f"time {sum(r['seconds'].values()):.0f}s {r['seconds']}", flush=True)
                state["rows"][key] = len(rows)
            for ev in [d / "events.log", *d.glob("*/events.log")]:
                if not ev.exists():
                    continue
                key = str(ev.relative_to(MIRROR))
                lines = ev.read_text(errors="replace").splitlines()
                for line in lines[state["events"].get(key, 0):]:
                    if any(w in line for w in ("AUTO-STOP", "ERROR", "Traceback", "ran out", "ready in", "trainer loaded")):
                        print(f"{ev.parent.name}: {line[:400]}", flush=True)
                state["events"][key] = len(lines)
            summ = d / "summary.json"
            if (d / "metadata.json").exists() and summ.exists() and name not in state["evals"]:
                run = wandb.init(project=a.project, group=a.group, name=name, id=name, resume="allow", job_type="eval",
                                 config=json.loads((d / "metadata.json").read_text()), reinit="create_new")
                run.summary.update(flat(json.loads(summ.read_text())))
                run.finish()
                state["evals"].append(name)
                print(f"eval {name} logged", flush=True)
        state_path.write_text(json.dumps(state))
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
