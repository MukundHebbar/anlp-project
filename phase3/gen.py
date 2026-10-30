"""Sample N SOLVE attempts per question with the mixed adapter (vLLM). Resumable by chunk.

    python phase3/gen.py --set test --adapter final-adapters/mixed-step75 --out runs/attempts [--n 16] [--limit 10]

Writes <out>/<set>/<chunk>.jsonl: one line per attempt {uid, k, text, finish_reason, completion_tokens}.
"""

import argparse
import json
import os
import time
from pathlib import Path

import common


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--chunk", type=int, default=100, help="questions per chunk")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--part", default="0/1", help="i/n: this job takes every n-th chunk starting at i")
    a = ap.parse_args()

    uids = common.load_sets()[a.set][: a.limit or None]
    rows = common.rows_by_uid()
    out = Path(a.out) / a.set
    out.mkdir(parents=True, exist_ok=True)
    chunks = [uids[i:i + a.chunk] for i in range(0, len(uids), a.chunk)]
    todo = [(i, c) for i, c in enumerate(chunks) if not (out / f"{i:03d}.jsonl").exists()]
    pi, pn = map(int, a.part.split("/"))
    todo = [(i, c) for i, c in todo if i % pn == pi]
    print(f"{a.set}: {len(uids)} questions, {len(chunks)} chunks, {len(todo)} to do", flush=True)
    if not todo:
        return

    # FlashInfer's sampling kernels need a newer CUDA runtime than Turing's 575 driver: use vLLM's own sampler
    os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    s = common.SOLVE_SAMPLING
    llm = LLM(model=common.STUDENT, dtype="bfloat16", language_model_only=True, max_model_len=s["max_tokens"] + 4096,
              gpu_memory_utilization=0.90, max_num_seqs=512, seed=a.seed, enable_lora=True, max_lora_rank=64,
              enable_prefix_caching=True)
    lora = LoRARequest("mixed", 1, str(Path(a.adapter).resolve()))
    for i, chunk in todo:
        t0 = time.time()
        # no per-request seed: with n > 1 some vLLM versions reuse one seed for every sample
        params = SamplingParams(n=a.n, temperature=s["temperature"], top_p=s["top_p"], top_k=s["top_k"],
                                max_tokens=s["max_tokens"])
        msgs = [[{"role": "user", "content": common.solve_prompt(rows[u])}] for u in chunk]
        outs = llm.chat(msgs, params, lora_request=lora, use_tqdm=False,
                        chat_template_kwargs={"enable_thinking": False})
        tmp = out / f"{i:03d}.jsonl.tmp"
        ntok = 0
        with tmp.open("w") as fh:
            for u, o in zip(chunk, outs, strict=True):
                for k, c in enumerate(o.outputs):
                    ntok += len(c.token_ids)
                    fh.write(json.dumps({"uid": u, "k": k, "text": c.text, "finish_reason": str(c.finish_reason),
                                         "completion_tokens": len(c.token_ids)}, ensure_ascii=False) + "\n")
        os.replace(tmp, out / f"{i:03d}.jsonl")
        dt = time.time() - t0
        print(f"{a.set} chunk {i}: {len(chunk)} q x {a.n}, {ntok} tokens, {dt:.0f}s, {ntok/dt:.0f} tok/s", flush=True)


if __name__ == "__main__":
    main()
