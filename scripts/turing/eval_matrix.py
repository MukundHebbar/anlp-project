#!/usr/bin/env python3
"""Evaluate the student (optionally with a LoRA adapter) on SOLVE, JUDGE and RECONSTRUCT.

    python scripts/turing/eval_matrix.py --name opd-solve-s104 --adapter <run>/adapters/step104 --out <dir>

Protocol v2 sampling (T 1.0, top_p 1.0, top_k off, seed 0), in two passes:
  1. generate up to --first-cap tokens (16k);
  2. answers that hit that cap are continued from their own tokens up to --max-cap (32k).
Continuing a sample from its own prefix gives the same distribution as one 32k pass, so the result
matches protocol v2 while most of the batch finishes at 16k.

With several GPUs visible, each task runs in its own process on its own GPU. --samples K draws K samples per
question in one pass (pass@K); sample k is written to <out>/s<k>/ in the baseline layout (responses.jsonl,
scores.jsonl with the strict gates, summary.json, metadata.json). Judging runs separately per sample folder.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from anlp_project import baseline, opd  # noqa: E402
from anlp_project.opd_monitor import repetition_score  # noqa: E402


UIDS_FILE = ""  # --uids-file, for --split uids
ROWS_FILE = ""  # --rows-file: answer-key rows for --split uids outside the train split


def rows_for(split: str, task: str) -> list[dict]:
    if split == "test":
        return baseline.rows_for("test", [task])
    if split == "uids":  # chosen train-split questions, in the file's order (e.g. a failure buffer's halves)
        wanted = json.loads(Path(UIDS_FILE).read_text())
        if ROWS_FILE:  # e.g. the failure-driven pool's SOLVE rows (phase2/failure_driven/data/solve_rows.jsonl)
            by_uid = {r["uid"]: r for r in map(json.loads, open(ROWS_FILE)) if r["task"] == task}
        else:
            by_uid = {r["uid"]: r for r in baseline.load_rows(task, "train")}
        missing = [u for u in wanted if u not in by_uid]
        if missing:
            raise SystemExit(f"{len(missing)} uids not in the {task} rows, e.g. {missing[:3]}")
        return [by_uid[u] for u in wanted]
    return opd.slice_rows(task, "dev")


def run_task(a, task: str, out: Path) -> None:
    rows = rows_for(a.split, task)[: a.limit or None]
    prompts = [baseline.render_prompt(r) for r in rows]
    s = dict(baseline.EVAL_SAMPLING)

    from huggingface_hub import snapshot_download
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt
    from vllm.lora.request import LoRARequest

    t0 = time.time()
    llm = LLM(model=snapshot_download(a.model or opd.TRIAL_CONFIG["student"], local_files_only=True), dtype="bfloat16",
              language_model_only=True, max_model_len=a.max_cap + 8192, gpu_memory_utilization=0.90,
              max_num_seqs=256, seed=s["seed"], enable_lora=bool(a.adapter), max_lora_rank=64)
    tok = llm.get_tokenizer()
    lora = LoRARequest("trained", 1, a.adapter) if a.adapter else None
    n = a.samples if task in a.samples_tasks.split(",") else 1
    first = SamplingParams(n=n, temperature=s["temperature"], top_p=s["top_p"], top_k=s["top_k"],
                           max_tokens=a.first_cap, seed=s["seed"])
    t1 = time.time()
    outs = llm.chat([[{"role": "user", "content": p}] for p in prompts], first, lora_request=lora, use_tqdm=False,
                    chat_template_kwargs={"enable_thinking": False})
    t2 = time.time()
    # One entry per (question, sample); each sample hitting first_cap is continued on its own.
    ids = {(i, k): list(c.token_ids) for i, o in enumerate(outs) for k, c in enumerate(o.outputs)}
    finish = {(i, k): str(c.finish_reason) for i, o in enumerate(outs) for k, c in enumerate(o.outputs)}
    capped = [ik for ik, f in finish.items() if f == "length"]
    if capped and a.max_cap > a.first_cap:
        more = SamplingParams(temperature=s["temperature"], top_p=s["top_p"], top_k=s["top_k"],
                              max_tokens=a.max_cap - a.first_cap, seed=s["seed"] + 1)
        conts = llm.generate([TokensPrompt(prompt_token_ids=list(outs[i].prompt_token_ids) + ids[(i, k)])
                              for i, k in capped], more, lora_request=lora, use_tqdm=False)
        for ik, c in zip(capped, conts, strict=True):
            ids[ik] += list(c.outputs[0].token_ids)
            finish[ik] = str(c.outputs[0].finish_reason)
    t3 = time.time()
    responses = []
    continued = set(capped) if a.max_cap > a.first_cap else set()
    for i, (r, p, o) in enumerate(zip(rows, prompts, outs, strict=True)):
        for k in range(n):
            x = ids[(i, k)]
            responses.append({"uid": r["uid"], "task": task, "sample": k, "prompt": p,
                              "text": tok.decode(x, skip_special_tokens=True), "finish_reason": finish[(i, k)],
                              "prompt_tokens": len(o.prompt_token_ids), "completion_tokens": len(x),
                              "continued": (i, k) in continued})
    out.mkdir(parents=True, exist_ok=True)
    with (out / f"responses-{task}.jsonl").open("w") as fh:
        for x in responses:
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    reps = [repetition_score(x) for x in ids.values()]
    (out / f"timing-{task}.json").write_text(json.dumps({
        "task": task, "n": len(rows), "samples": n, "continued": len(capped),
        "cap_hits_final": sum(f == "length" for f in finish.values()),
        "mean_repetition": sum(reps) / len(reps),
        "seconds": {"load": round(t1 - t0), "first_pass": round(t2 - t1), "continuation": round(t3 - t2)}}, indent=1))


def merge(a, out: Path, tasks: list[str]) -> None:
    """Sample k of every question goes to out/s<k>/ in the usual one-answer-per-question layout
    (responses.jsonl, scores.jsonl with the strict gates, summary.json, metadata.json), so the scoring and
    judging tools run on each sample unchanged; pass@k is computed across the s<k> folders."""
    parts, timing = {}, {}
    for task in tasks:
        rows = {r["uid"]: r for r in rows_for(a.split, task)}
        for x in map(json.loads, (out / f"responses-{task}.jsonl").open()):
            parts.setdefault(x.get("sample", 0), []).append((rows[x["uid"]], x))
        timing[task] = json.loads((out / f"timing-{task}.json").read_text())
    for k, items in sorted(parts.items()):
        d = out / f"s{k}"
        d.mkdir(parents=True, exist_ok=True)
        scores = [baseline.score_response_strict(r, x) for r, x in items]
        with (d / "responses.jsonl").open("w") as fh:
            for _, x in items:
                fh.write(json.dumps(x, ensure_ascii=False) + "\n")
        with (d / "scores.jsonl").open("w") as fh:
            for x in scores:
                fh.write(json.dumps(x, ensure_ascii=False) + "\n")
        summary = baseline.summarize(scores)
        (d / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
        print(f"sample {k}:", json.dumps({t: {m: v for m, v in summary[t].items() if m in (
            "accuracy", "verdict_accuracy", "parse_rate", "token_cap_rate", "mean_completion_tokens")} for t in summary}))
    meta = {"name": a.name, "adapter": a.adapter or None, "split": a.split,
            "model": a.model or opd.TRIAL_CONFIG["student"], "prompts": "v2", "samples": a.samples,
            "samples_tasks": a.samples_tasks,
            "limit": a.limit or None, "sampling": {**baseline.EVAL_SAMPLING, "max_tokens": a.max_cap},
            "two_pass": {"first_cap": a.first_cap, "max_cap": a.max_cap,
                         "rule": "samples capped at first_cap are continued from their own tokens to max_cap"},
            "platform": "turing-l40s", "timing": timing}
    for k in parts:
        (out / f"s{k}" / "metadata.json").write_text(json.dumps({**meta, "sample": k}, indent=1) + "\n")
    (out / "metadata.json").write_text(json.dumps(meta, indent=1) + "\n")
    (out / "done").write_text("ok\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--adapter", default="")
    ap.add_argument("--model", default="", help="model to evaluate (default: the student, opd.TRIAL_CONFIG)")
    ap.add_argument("--split", default="test", choices=["test", "dev", "uids"])
    ap.add_argument("--uids-file", default="", help="--split uids: JSON list of train-split uids to evaluate")
    ap.add_argument("--rows-file", default="", help="--split uids: jsonl rows to take them from (default: train split)")
    ap.add_argument("--tasks", default="solve,judge,reconstruct")
    ap.add_argument("--first-cap", type=int, default=16384)
    ap.add_argument("--max-cap", type=int, default=32768)
    ap.add_argument("--samples", type=int, default=1, help="samples per question (pass@k); each goes to out/s<k>/")
    ap.add_argument("--samples-tasks", default="solve,judge,reconstruct",
                    help="tasks that get --samples; the others get 1 (2026-10-06: trained checkpoints use 4 for SOLVE only)")
    ap.add_argument("--limit", type=int, default=0, help="only the first N questions per task (smoke test)")
    ap.add_argument("--worker", default="", help=argparse.SUPPRESS)
    a = ap.parse_args()
    global UIDS_FILE, ROWS_FILE
    UIDS_FILE, ROWS_FILE = a.uids_file, a.rows_file
    if a.split == "uids" and not a.uids_file:
        raise SystemExit("--split uids needs --uids-file")
    out = Path(a.out)
    tasks = a.tasks.split(",")
    if a.worker:
        run_task(a, a.worker, out)
        return
    if (out / "done").exists():
        raise SystemExit(f"{out} is already finished")
    gpus = [g for g in os.environ.get("CUDA_VISIBLE_DEVICES", "0").split(",") if g]
    todo = [t for t in tasks if not (out / f"responses-{t}.jsonl").exists()]  # a restart keeps finished tasks
    # One process per task, spread over the visible GPUs; tasks beyond the GPU count queue on them.
    pending = list(todo)
    running = {}
    while pending or running:
        for g in gpus:
            if g not in running and pending:
                t = pending.pop(0)
                cmd = [sys.executable, __file__, "--name", a.name, "--out", str(out), "--adapter", a.adapter,
                       "--model", a.model, "--samples", str(a.samples), "--samples-tasks", a.samples_tasks,
                       "--limit", str(a.limit),
                       "--split", a.split, "--uids-file", a.uids_file, "--rows-file", a.rows_file, "--tasks", a.tasks, "--first-cap", str(a.first_cap), "--max-cap",
                       str(a.max_cap), "--worker", t]
                out.mkdir(parents=True, exist_ok=True)
                running[g] = (t, subprocess.Popen(cmd, env={**os.environ, "CUDA_VISIBLE_DEVICES": g},
                                                  stdout=open(out / f"worker-{t}.log", "w"), stderr=subprocess.STDOUT))
                print(f"{t} on GPU {g}", flush=True)
        for g, (t, p) in list(running.items()):
            if p.poll() is not None:
                if p.returncode != 0:
                    raise SystemExit(f"{t} failed; see {out}/worker-{t}.log")
                print(f"{t} done", flush=True)
                del running[g]
        time.sleep(10)
    merge(a, out, tasks)


if __name__ == "__main__":
    main()
