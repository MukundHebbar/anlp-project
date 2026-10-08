#!/usr/bin/env python3
"""Generate the student's dev-slice answers (protocol v2) and write the usual eval folder.

    python scripts/turing/dev_generate.py --task reconstruct --out <eval dir> [--adapter <lora dir>]

Writes responses.jsonl, scores.jsonl and summary.json (deterministic scores, cap rate, length,
repetition). DeepSeek judging runs separately (scripts/judge_baseline.py --split dev).
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from anlp_project import baseline, opd  # noqa: E402
from anlp_project.opd_monitor import repetition_score  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="reconstruct")
    ap.add_argument("--out", required=True)
    ap.add_argument("--adapter", default="")
    ap.add_argument("--prompts", default="v2", choices=["v1", "v2"], help="student prompt version (baseline.PROMPT_VERSIONS); v1 reproduces earlier runs")
    ap.add_argument("--questions", default="dev", choices=["dev", "extra200"],
                    help="dev slice, or the first 200 of opd-extra-<task>.json (held out from every trial)")
    a = ap.parse_args()
    out = Path(a.out)
    if (out / "responses.jsonl").exists():
        raise SystemExit(f"{out} already has responses")
    out.mkdir(parents=True, exist_ok=True)
    rows = opd.slice_rows(a.task, "dev") if a.questions == "dev" else opd.extra_rows(a.task, 200)
    prompts = [baseline.render_prompt(r, a.prompts) for r in rows]
    s = dict(baseline.EVAL_SAMPLING)  # protocol v2: T 1.0, top_p 1.0, top_k off, 32k, seed 0

    from huggingface_hub import snapshot_download
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    t0 = time.time()
    llm = LLM(model=snapshot_download(opd.TRIAL_CONFIG["student"], local_files_only=True), dtype="bfloat16",
              language_model_only=True, max_model_len=s["max_tokens"] + 8192, gpu_memory_utilization=0.90,
              max_num_seqs=256, seed=s["seed"], enable_lora=bool(a.adapter), max_lora_rank=64)
    lora = LoRARequest("trained", 1, a.adapter) if a.adapter else None
    params = SamplingParams(temperature=s["temperature"], top_p=s["top_p"], top_k=s["top_k"],
                            max_tokens=s["max_tokens"], seed=s["seed"])
    t1 = time.time()
    outs = llm.chat([[{"role": "user", "content": p}] for p in prompts], params, lora_request=lora, use_tqdm=False,
                    chat_template_kwargs={"enable_thinking": False})
    t2 = time.time()
    results = [{"text": str(o.outputs[0].text), "finish_reason": str(o.outputs[0].finish_reason),
                "completion_tokens": len(o.outputs[0].token_ids)} for o in outs]
    reps = [repetition_score(list(o.outputs[0].token_ids)) for o in outs]
    scores = [baseline.score_response(r, x) for r, x in zip(rows, results, strict=True)]
    with (out / "responses.jsonl").open("w") as fh:
        for r, x in zip(rows, results):
            fh.write(json.dumps({"uid": r["uid"], **x}, ensure_ascii=False) + "\n")
    with (out / "scores.jsonl").open("w") as fh:
        for sc in scores:
            fh.write(json.dumps(sc, ensure_ascii=False) + "\n")
    summary = baseline.summarize(scores)
    n = len(results)
    loop_check = {"cap_hits": sum(x["finish_reason"] == "length" for x in results),
                  "cap_rate": sum(x["finish_reason"] == "length" for x in results) / n,
                  "mean_tokens": sum(x["completion_tokens"] for x in results) / n,
                  "mean_repetition": sum(reps) / n, "repetition_above_0.5": sum(r > 0.5 for r in reps),
                  "seconds": {"load": round(t1 - t0), "generate": round(t2 - t1)}}
    (out / "summary.json").write_text(json.dumps({"adapter": a.adapter or None, "prompts": a.prompts, "sampling": s, "loop_check": loop_check,
                                                  **summary}, indent=1))
    print(json.dumps({"loop_check": loop_check, **summary}, indent=1))


if __name__ == "__main__":
    main()
