"""Judge own attempts with the mixed adapter and read the verdict-token probability. Resumable by chunk.

    python phase3/judge.py --set test --attempts runs/attempts --adapter final-adapters/mixed-step75 --out runs/judge

For every finished, answered attempt:
  pass 1  sample a judge reasoning chain (T 1.0, 8,192 cap) that stops at "Decision:" (the v2 prompt's verdict label)
  pass 2  append "Decision:" to the chain (also when the chain was cut off or never reached a verdict) and read the
          top-20 next-token logprobs for up to 4 forced tokens -> P(incorrect) at the first verdict position
  pass 0  "Decision:" right after the prompt with no reasoning (P(True)-style) -> p_direct, one per attempt
Chains per attempt: --chains-first (default 4) for attempts k < --first-k (default 4) of the test set, else 1.
Writes <out>/<set>/<chunk>.jsonl: one line per chain {uid, k, chain, reached_label, chain_tokens, p_incorrect, ...}.
"""

import argparse
import json
import os
import time
from pathlib import Path

import common


def answered(att: dict) -> str | None:
    if att["finish_reason"] != "stop":
        return None
    return common.baseline.extract_solve_answer(att["text"])[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--attempts", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chains-first", type=int, default=4)
    ap.add_argument("--first-k", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--part", default="0/1", help="i/n: this job takes every n-th chunk starting at i")
    a = ap.parse_args()

    rows = common.rows_by_uid()
    src = Path(a.attempts) / a.set
    out = Path(a.out) / a.set
    out.mkdir(parents=True, exist_ok=True)
    chunk_files = sorted(src.glob("[0-9][0-9][0-9].jsonl"))
    todo = [f for f in chunk_files if not (out / f.name).exists()]
    pi, pn = map(int, a.part.split("/"))
    todo = [f for f in todo if int(f.stem) % pn == pi]
    print(f"{a.set}: {len(chunk_files)} attempt chunks, {len(todo)} to judge", flush=True)
    if not todo:
        return

    # FlashInfer's sampling kernels need a newer CUDA runtime than Turing's 575 driver: use vLLM's own sampler
    os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt
    from vllm.lora.request import LoRARequest

    s = common.JUDGE_SAMPLING
    llm = LLM(model=common.STUDENT, dtype="bfloat16", language_model_only=True, max_model_len=32768,
              gpu_memory_utilization=0.90, max_num_seqs=512, seed=a.seed, enable_lora=True, max_lora_rank=64,
              enable_prefix_caching=True)
    tok = llm.get_tokenizer()
    lora = LoRARequest("mixed", 1, str(Path(a.adapter).resolve()))

    for f in todo:
        t0 = time.time()
        atts = [json.loads(line) for line in f.open()]
        items = []  # (attempt, prompt text, n chains)
        for att in atts:
            ans = answered(att)
            if ans is None:
                continue
            n = a.chains_first if (a.set == "test" and att["k"] < a.first_k) else 1
            prompt = common.judge_prompt(rows[att["uid"]]["question"], att["text"], ans)
            items.append((att, prompt, n))
        templated = [tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False,
                                             add_generation_prompt=True, enable_thinking=False)
                     for _, p, _ in items]
        prompt_len = [len(tok.encode(t, add_special_tokens=False)) for t in templated]
        # pass 1: reasoning chains, grouped by chain count so n can be set per request
        chains = {}
        for n in sorted({n for *_, n in items}):
            idx = [i for i, (_, _, m) in enumerate(items) if m == n]
            params = SamplingParams(n=n, temperature=s["temperature"], top_p=s["top_p"], top_k=s["top_k"],
                                    max_tokens=s["max_tokens"], stop=[common.VERDICT_LABEL])
            outs = llm.generate([TokensPrompt(prompt_token_ids=tok.encode(templated[i], add_special_tokens=False))
                                 for i in idx], params, lora_request=lora, use_tqdm=False)
            for i, o in zip(idx, outs, strict=True):
                # stop_reason is the stop string when "Decision:" ended the chain (an EOS stop gives a token id)
                chains[i] = [(c.text, str(c.finish_reason), len(c.token_ids), c.stop_reason == common.VERDICT_LABEL)
                             for c in o.outputs]
        # pass 2: forced verdict, top-20 logprobs for 4 tokens
        flat = [(i, j) for i in range(len(items)) for j in range(len(chains[i]))]
        forced = [TokensPrompt(prompt_token_ids=tok.encode(templated[i] + chains[i][j][0] + common.VERDICT_LABEL,
                                                           add_special_tokens=False)) for i, j in flat]
        p2 = SamplingParams(temperature=1.0, max_tokens=4, logprobs=20)
        outs2 = llm.generate(forced, p2, lora_request=lora, use_tqdm=False)
        # pass 0 (P(True)-style): "Decision:" right after the prompt, no reasoning; one prefill per attempt
        direct = llm.generate([TokensPrompt(prompt_token_ids=tok.encode(t + common.VERDICT_LABEL, add_special_tokens=False))
                               for t in templated], p2, lora_request=lora, use_tqdm=False)
        p_direct = []
        for o in direct:
            pos = [{tok.decode([tid]): float(x.logprob) for tid, x in d.items()} for d in (o.outputs[0].logprobs or [])]
            p_direct.append(common.verdict_probability(pos)[0])
        tmp = out / (f.name + ".tmp")
        dec_tok = 0
        with tmp.open("w") as fh:
            for (i, j), o in zip(flat, outs2, strict=True):
                att = items[i][0]
                text, finish, ntok, reached = chains[i][j]
                dec_tok += ntok
                lp = o.outputs[0].logprobs or []
                positions = [{tok.decode([tid]): float(x.logprob) for tid, x in pos.items()} for pos in lp]
                p, at = common.verdict_probability(positions)
                fh.write(json.dumps({"uid": att["uid"], "k": att["k"], "chain": j, "reached_label": reached,
                                     "chain_finish": finish, "chain_tokens": ntok, "p_incorrect": p,
                                     "p_direct": p_direct[i], "prompt_tokens": prompt_len[i],
                                     "verdict_position": at, "forced_text": o.outputs[0].text,
                                     "chain_tail": text[-300:]}, ensure_ascii=False) + "\n")
        os.replace(tmp, out / f.name)
        dt = time.time() - t0
        print(f"{a.set} {f.name}: {len(items)} attempts, {len(flat)} chains, {dec_tok} chain tokens, {dt:.0f}s",
              flush=True)


if __name__ == "__main__":
    main()
