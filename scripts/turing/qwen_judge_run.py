#!/usr/bin/env python3
"""Serve Qwen3.8-27B with vLLM and answer judge requests ({key, state, questions} per line) with QwenJudge.

    python scripts/turing/qwen_judge_run.py --requests <requests.jsonl> --out <answers.jsonl>
    python scripts/turing/qwen_judge_run.py --eval-dir test:<eval dir>/s0 ... --out <log dir>/answers.jsonl

--eval-dir SPLIT:DIR judges every JUDGE and RECONSTRUCT answer in DIR/responses.jsonl with jev_judging's
pipeline (gates, staged shortcut check, questions) and this model, writing the raw records to
DIR/judgments.qwen.jsonl. Calibrated scores are computed afterwards, offline
(scripts/qwen_judge_calibration.py score).

Uses every visible GPU for tensor parallelism (2 L40S fit the 27B). Answers are appended as they finish;
a restart skips keys already answered.
"""

import argparse
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from anlp_project.opd_train import serve, wait_ready  # noqa: E402
from anlp_project.qwen_judging import MODEL, QwenJudge  # noqa: E402


def judge_eval_dir(judge, split: str, d: str, workers: int) -> None:
    from anlp_project import jev_judging as jj
    from anlp_project.baseline import rows_for
    from anlp_project.opd import slice_rows

    d = Path(d)
    rows = ({r["uid"]: r for r in rows_for("test", ("judge", "reconstruct"))} if split == "test" else
            {r["uid"]: r for t in ("judge", "reconstruct") for r in slice_rows(t, "dev")})
    path = d / "judgments.qwen.jsonl"
    done = {json.loads(l)["uid"] for l in path.open() if json.loads(l).get("ok")} if path.exists() else set()
    todo = [x for x in map(json.loads, (d / "responses.jsonl").open()) if x["uid"] in rows and x["uid"] not in done]
    lock = threading.Lock()

    def work(x):
        row = rows[x["uid"]]
        rec = {"uid": x["uid"], "model": MODEL, "judge": "qwen27b-eval-v1"}
        try:
            fn = jj.judge_answer if row["task"] == "judge" else jj.reconstruct_answer
            rec.update(fn(row, x["text"], judge, None), ok=True)
        except Exception as e:
            rec.update(ok=False, error=f"{type(e).__name__}: {e}"[:300])
        with lock, path.open("a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec["ok"]

    with ThreadPoolExecutor(max_workers=workers) as pool:
        ok = list(pool.map(work, todo))
    print(f"{d}: {sum(ok)}/{len(ok)} judged, {len(done)} previously", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", default="")
    ap.add_argument("--eval-dir", action="append", default=[], metavar="SPLIT:DIR")
    ap.add_argument("--out", required=True)
    ap.add_argument("--port", type=int, default=0,
                    help="server port; 0 picks a free one (two sessions on one node with a fixed port silently shared one server)")
    ap.add_argument("--workers", type=int, default=32)
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["key"] for l in out.open() if json.loads(l).get("ok")} if out.exists() else set()
    todo = [r for r in map(json.loads, open(a.requests)) if r["key"] not in done] if a.requests else []
    from huggingface_hub import snapshot_download

    if not a.port:
        import socket
        with socket.socket() as sk:
            sk.bind(("127.0.0.1", 0))
            a.port = sk.getsockname()[1]
    path = snapshot_download(MODEL, local_files_only=True)
    gpus = os.environ.get("CUDA_VISIBLE_DEVICES", "0,1")
    proc = serve(path, "judge", a.port, gpus, ["--tensor-parallel-size", str(len(gpus.split(","))),
                                               "--max-model-len", "40960", "--gpu-memory-utilization", "0.90",
                                               "--max-logprobs", "20", "--enable-prefix-caching"], out.parent, {})
    try:
        print(f"judge ready in {wait_ready(a.port, proc, 'judge', out.parent)} s; {len(todo)} requests", flush=True)
        judge, lock = QwenJudge(path, a.port), threading.Lock()

        def work(r):
            rec = {"key": r["key"]}
            try:
                rec.update(ok=True, response=judge.call(r["state"], r["questions"]))
            except Exception as e:
                rec.update(ok=False, error=f"{type(e).__name__}: {e}"[:300])
            with lock, out.open("a") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return rec["ok"]

        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            ok = list(pool.map(work, todo))
        print(f"requests: {sum(ok)}/{len(ok)} ok; prompt tokens {judge.tokens:,}", flush=True)
        for spec in a.eval_dir:
            judge_eval_dir(judge, *spec.split(":", 1), a.workers)
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
