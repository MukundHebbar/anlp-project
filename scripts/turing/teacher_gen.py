#!/usr/bin/env python3
"""Teacher answers for the SFT warm-up, then the quality filter (no correctness filter).

    python scripts/turing/teacher_gen.py --task reconstruct --out <run dir> [--n 512 --samples 2]

Writes <out>/teacher.jsonl (every sample, with token ids), <out>/sft.jsonl (the first sample per
question that passes the filter) and <out>/filter.json (counts per rejection reason).
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from anlp_project import opd  # noqa: E402
from anlp_project.baseline import extract_reconstruction, parse_judge_response, extract_solve_answer  # noqa: E402
from anlp_project.opd_monitor import repetition_score  # noqa: E402

FILTER = {"max_tokens": 8192, "max_repetition": 0.2}


def parses(task: str, text: str) -> bool:
    if task == "reconstruct":
        return extract_reconstruction(text)[1] == "strict"  # valid JSON as returned
    if task == "judge":
        decision, step = parse_judge_response(text)
        return decision is not None
    return extract_solve_answer(text)[0] is not None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="reconstruct")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=512)
    ap.add_argument("--samples", type=int, default=2)
    ap.add_argument("--tp", type=int, default=2)
    ap.add_argument("--chunk", type=int, default=192, help="questions per saved chunk")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = opd.TRIAL_CONFIG
    cap = cfg["rollout_max_tokens"][a.task]
    prompts = opd.warmup_prompts(a.task)[: a.n]

    from huggingface_hub import snapshot_download
    from vllm import LLM, SamplingParams

    teacher = snapshot_download(cfg["teacher"], local_files_only=True)
    t0 = time.time()
    llm = LLM(model=teacher, dtype="bfloat16", language_model_only=True, tensor_parallel_size=a.tp,
              max_model_len=cap + 4096, gpu_memory_utilization=0.90, max_num_seqs=256,
              max_num_batched_tokens=8192, seed=0)  # high batching; 256 is the most the 27B fit on Modal
    t1 = time.time()
    params = SamplingParams(n=a.samples, temperature=cfg["rollout"]["temperature"], top_p=cfg["rollout"]["top_p"],
                            top_k=0, max_tokens=cap, seed=0)
    im_end = llm.get_tokenizer().convert_tokens_to_ids("<|im_end|>")
    eos = {im_end, llm.get_tokenizer().convert_tokens_to_ids("<|endoftext|>")}

    # Generate in chunks and append after each one, so a time limit loses at most one chunk;
    # a restart skips the questions already in teacher.jsonl.
    raw_path = out / "teacher.jsonl"
    done = {json.loads(l)["uid"] for l in raw_path.open()} if raw_path.exists() else set()
    todo = [p for p in prompts if p["uid"] not in done]
    for i in range(0, len(todo), a.chunk):
        chunk = todo[i:i + a.chunk]
        outs = llm.chat([[{"role": "user", "content": p["prompt"]}] for p in chunk], params, use_tqdm=True,
                        chat_template_kwargs={"enable_thinking": False})
        with raw_path.open("a") as raw:
            for p, o in zip(chunk, outs, strict=True):
                for k, c in enumerate(o.outputs):
                    ids = list(c.token_ids)
                    if c.finish_reason == "stop" and (not ids or ids[-1] not in eos):
                        ids.append(im_end)  # train on the stop token, as OPD does
                    raw.write(json.dumps({"uid": p["uid"], "sample": k, "prompt": p["prompt"], "text": c.text,
                                          "finish_reason": c.finish_reason, "response_ids": ids}) + "\n")
        print(f"chunk done: {min(i + a.chunk, len(todo))}/{len(todo)} questions, {time.time() - t1:.0f} s", flush=True)
    t2 = time.time()

    reasons = {"kept": 0, "no_passing_sample": 0}
    per_sample = {"cut_off": 0, "unparsed": 0, "repetitive": 0, "too_long": 0, "ok": 0}
    samples = {}
    for line in raw_path.open():
        x = json.loads(line)
        samples.setdefault(x["uid"], []).append(x)
    lens = []
    with (out / "sft.jsonl").open("w") as sft:
        for p in prompts:
            chosen = None
            for x in sorted(samples.get(p["uid"], []), key=lambda x: x["sample"]):
                ids = x["response_ids"]
                lens.append(len(ids))
                if x["finish_reason"] != "stop":
                    why = "cut_off"
                elif not parses(a.task, x["text"]):
                    why = "unparsed"
                elif repetition_score(ids) >= FILTER["max_repetition"]:
                    why = "repetitive"
                elif len(ids) > FILTER["max_tokens"]:
                    why = "too_long"
                else:
                    why = "ok"
                per_sample[why] += 1
                if why == "ok" and chosen is None:
                    chosen = {"uid": p["uid"], "sample": x["sample"], "prompt": p["prompt"], "response_ids": ids,
                              "text": x["text"]}
            if chosen:
                sft.write(json.dumps(chosen) + "\n")
                reasons["kept"] += 1
            else:
                reasons["no_passing_sample"] += 1
    report = {"task": a.task, "questions": len(prompts), "samples": a.samples, "filter": FILTER, **reasons,
              "per_sample": per_sample, "mean_tokens": sum(lens) / len(lens), "max_tokens": max(lens),
              "seconds": {"load": round(t1 - t0), "generate": round(t2 - t1)}, "generated_tokens": sum(lens)}
    (out / "filter.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
