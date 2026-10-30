"""Direct verdict probability only (no reasoning chain; one prefill per attempt) with any adapter, or none.

    python phase3/direct_score.py --set test --attempts <root>/attempts --adapter <dir or "none"> --out <root>/direct-<name>

Same prompt and scoring as judge.py's pass 0. Writes <out>/<set>/<chunk>.jsonl: {uid, k, p_direct}. Resumable by chunk.
"""

import argparse
import json
import os
import time
from pathlib import Path

import common
from judge import answered


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--attempts", required=True)
    ap.add_argument("--adapter", required=True, help='LoRA dir, or "none" for the untrained model')
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = common.rows_by_uid()
    src, out = Path(a.attempts) / a.set, Path(a.out) / a.set
    out.mkdir(parents=True, exist_ok=True)
    todo = [f for f in sorted(src.glob("[0-9][0-9][0-9].jsonl")) if not (out / f.name).exists()]
    print(f"{a.set}: {len(todo)} chunks to score", flush=True)
    if not todo:
        return
    os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt
    from vllm.lora.request import LoRARequest

    use_lora = a.adapter != "none"
    llm = LLM(model=common.STUDENT, dtype="bfloat16", language_model_only=True, max_model_len=32768,
              gpu_memory_utilization=0.90, max_num_seqs=512, enable_lora=use_lora, max_lora_rank=64,
              enable_prefix_caching=True)
    tok = llm.get_tokenizer()
    lora = LoRARequest("a", 1, str(Path(a.adapter).resolve())) if use_lora else None
    params = SamplingParams(temperature=1.0, max_tokens=4, logprobs=20)
    for f in todo:
        t0 = time.time()
        items = []
        for line in f.open():
            att = json.loads(line)
            ans = answered(att)
            if ans is not None:
                items.append((att, common.judge_prompt(rows[att["uid"]]["question"], att["text"], ans)))
        prompts = [TokensPrompt(prompt_token_ids=tok.encode(
            tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True,
                                    enable_thinking=False) + common.VERDICT_LABEL, add_special_tokens=False))
            for _, p in items]
        outs = llm.generate(prompts, params, lora_request=lora, use_tqdm=False)
        tmp = out / (f.name + ".tmp")
        with tmp.open("w") as fh:
            for (att, _), o in zip(items, outs, strict=True):
                pos = [{tok.decode([tid]): float(x.logprob) for tid, x in d.items()} for d in (o.outputs[0].logprobs or [])]
                fh.write(json.dumps({"uid": att["uid"], "k": att["k"], "p_direct": common.verdict_probability(pos)[0]}) + "\n")
        os.replace(tmp, out / f.name)
        print(f"{a.set} {f.name}: {len(items)} attempts, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
