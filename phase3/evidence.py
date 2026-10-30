"""Phase 3b evidence rows on the cached attempts (vLLM, Qwen3.5-2B + mixed adapter). Resumable by chunk.

    python phase3/evidence.py <kind> --set test --attempts <root>/attempts --graded phase3/runs/graded --out <root>/ev

kind      unit                         what is written per unit
logprob   every finished attempt       T1/E-H: log p(attempt | prompt) under the solver, top-1 confidence stats
answer    every answer group           E-A: P(Yes) to "is this final answer correct?", no trace
pairwise  top-2 groups (>= 2 groups)   E-B: P(A) to "which final answer is correct, A or B?", <= 3 pairs, both orders
backward  top-2 groups (>= 2 groups)   E-C: mask a number in the problem, give the answer, sample the masked number
program   top-3 groups                 E-D: 3 Python programs checking the answer (CORRECT / INCORRECT / UNCHECKABLE)
pot       every question               program-of-thought: 4 programs computing the answer (PROVE baseline, decorrelation)

Programs are executed inside the same job (sandbox.py). Groups come from grade.py's output (--graded). Every output
line carries its raw text; scores and answer matching are computed on CPU afterwards.
"""

import argparse
import json
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import common
from judge import answered

A = "final-adapters/mixed-step75"
CHUNK = 50  # questions per output file


def load_groups(graded: Path, split: str):
    """uid -> list of (group id, [attempt k...], answer) sorted by size (desc), then first k."""
    by_q = defaultdict(lambda: defaultdict(list))
    ans = {}
    for line in (graded / f"{split}.jsonl").open():
        r = json.loads(line)
        if r["group"] >= 0:
            by_q[r["uid"]][r["group"]].append(r["k"])
            ans.setdefault((r["uid"], r["group"]), r["answer"])
    return {u: sorted(((g, sorted(ks), ans[(u, g)]) for g, ks in gs.items()), key=lambda x: (-len(x[1]), x[1][0]))
            for u, gs in by_q.items()}


def load_attempts(root: Path, split: str):
    out = {}
    for f in sorted((root / split).glob("[0-9][0-9][0-9].jsonl")):
        for line in f.open():
            r = json.loads(line)
            out[(r["uid"], r["k"])] = r
    return out


# ------------------------------------------------------------------ prompts

def answer_prompt(q, ans):
    return (f"Problem:\n{q}\n\nProposed final answer: {ans}\n\n"
            "Is the proposed final answer correct? Reply with Yes or No.")


def pairwise_prompt(q, a_text, b_text):
    return (f"Problem:\n{q}\n\nTwo solutions to this problem reach different final answers. At most one of them is "
            f"correct.\n\nSolution A:\n{a_text}\n\nSolution B:\n{b_text}\n\n"
            "Which solution has the correct final answer? Reply with A or B.")


def program_prompt(q, ans):
    return (f"Problem:\n{q}\n\nProposed final answer: {ans}\n\n"
            "Write one self-contained Python 3 program that checks the proposed final answer independently, by "
            "computation: for example evaluate the expression numerically, substitute the answer back into the "
            "conditions, simulate, or brute-force small cases. You may use math, fractions, itertools, sympy and "
            "numpy. Do not simply print the proposed answer. The last line the program prints must be exactly CORRECT "
            "or INCORRECT. If the answer cannot be checked by computation at all, the program prints only "
            "UNCHECKABLE. Keep the program short (at most 40 lines, few comments). Reply with the program in a single "
            "```python code block.")


def pot_prompt(q):
    return (f"Problem:\n{q}\n\nWrite one self-contained Python 3 program that computes the answer to this problem. "
            "You may use math, fractions, itertools, sympy and numpy. The last line the program prints must be the "
            "final answer only, in exact simplest form where possible (for example 3/4, sqrt(2), pi/6, 12). "
            "Keep the program short (at most 40 lines, few comments). Reply with the program in a single "
            "```python code block.")


# numbers that stand alone in the text (not exponents/subscripts, not inside a LaTeX command name)
_NUM = re.compile(r"(?<![\w^_.{\\])(\d+(?:\.\d+)?)(?![\w.}])")


def masks(q, k=2):
    """Up to k (masked question, masked value, symbol): numbers that occur exactly once, largest first."""
    sym = next((s for s in ("X", "Q", "W", "Z") if not re.search(rf"\b{s}\b", q)), None)
    if sym is None:
        return []
    found = _NUM.findall(q)
    once = [n for n, c in Counter(found).items() if c == 1 and float(n) not in (0.0, 1.0)]
    once.sort(key=lambda n: -float(n))
    out = []
    for n in once[:k]:
        m = _NUM.sub(lambda mt: sym if mt.group(1) == n else mt.group(0), q, count=0)
        out.append((m, n, sym))
    return out


def backward_question(masked, sym, ans):
    return (f"{masked}\n\nIn the problem above, one given number was replaced by the unknown {sym}. Suppose the final "
            f"answer to the problem is {ans}. What is the value of {sym}?")


# ------------------------------------------------------------------ vLLM helpers

def make_llm(max_len, max_seqs=256, batched=None):
    os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
    from vllm import LLM
    kw = {"max_num_batched_tokens": batched} if batched else {}
    return LLM(model=common.STUDENT, dtype="bfloat16", language_model_only=True, max_model_len=max_len,
               gpu_memory_utilization=0.90, max_num_seqs=max_seqs, enable_lora=True, max_lora_rank=64,
               enable_prefix_caching=True, **kw)


def lora():
    from vllm.lora.request import LoRARequest
    return LoRARequest("mixed", 1, str(Path(A).resolve()))


def chat_text(tok, user, prefix=""):
    return tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True,
                                   enable_thinking=False) + prefix


def two_way(llm, tok, prompts, labels):
    """P(labels[0]) / (P(labels[0]) + P(labels[1])) at the first of 4 forced positions showing either label."""
    from vllm import SamplingParams
    from vllm.inputs import TokensPrompt
    ps = [TokensPrompt(prompt_token_ids=tok.encode(p, add_special_tokens=False)) for p in prompts]
    outs = llm.generate(ps, SamplingParams(temperature=1.0, max_tokens=4, logprobs=20), lora_request=lora(),
                        use_tqdm=False)
    res = []
    for o in outs:
        val = None
        for d in o.outputs[0].logprobs or []:
            p = [0.0, 0.0]
            for tid, x in d.items():
                t = tok.decode([tid]).strip().strip("*_`:.").strip().lower()
                for i, lab in enumerate(labels):
                    if t == lab.lower():
                        p[i] += pow(2.718281828459045, x.logprob)
            if p[0] + p[1] > 0:
                val = p[0] / (p[0] + p[1])
                break
        res.append(val)
    return res


def tail_tokens(tok, text, n):
    ids = tok.encode(text, add_special_tokens=False)
    return text if len(ids) <= n else "[... earlier part omitted ...]\n" + tok.decode(ids[-n:])


# ------------------------------------------------------------------ kinds

def run_logprob(llm, tok, chunk, groups, atts, rows):
    """T1/E-H: one prefill per finished attempt; per-token log p of the sampled token and DeepConf-style confidence."""
    import numpy as np
    from vllm import SamplingParams
    from vllm.inputs import TokensPrompt
    items = [(u, k) for u in chunk for k in range(16) if atts[(u, k)]["finish_reason"] == "stop"]
    out = []
    # top-1 only: billions of Python logprob objects otherwise; confidence = -log p(top-1) (DeepConf with k = 1)
    params = SamplingParams(temperature=1.0, max_tokens=1, prompt_logprobs=1, detokenize=False)
    for i in range(0, len(items), 64):
        batch = items[i:i + 64]
        ps, bounds = [], []
        for u, k in batch:
            head = tok.encode(chat_text(tok, common.solve_prompt(rows[u])), add_special_tokens=False)
            body = tok.encode(atts[(u, k)]["text"], add_special_tokens=False)
            ps.append(TokensPrompt(prompt_token_ids=head + body))
            bounds.append(len(head))
        outs = llm.generate(ps, params, lora_request=lora(), use_tqdm=False)
        for (u, k), o, b, p in zip(batch, outs, bounds, ps, strict=True):
            ids = p["prompt_token_ids"]
            lp, conf = [], []
            for j in range(b, len(ids)):
                d = o.prompt_logprobs[j]
                lp.append(d[ids[j]].logprob)
                conf.append(-max(x.logprob for x in d.values()))
            # unc = -log p(top-1): DeepConf's token confidence with k = 1, sign flipped (higher = less sure)
            lp, unc = np.array(lp), np.array(conf)
            win = np.convolve(unc, np.ones(1024) / 1024, mode="valid") if len(unc) >= 1024 else np.array([unc.mean()])
            out.append({"uid": u, "k": k, "n_tokens": len(lp), "sum_lp": float(lp.sum()), "mean_lp": float(lp.mean()),
                        "greedy_share": float(np.mean(lp >= -unc - 1e-6)), "min_lp": float(lp.min()),
                        "mean_unc": float(unc.mean()), "max_group_unc": float(win.max()),
                        "top10_group_unc": float(np.sort(win)[-max(1, len(win) // 10):].mean()),
                        "tail_unc": float(unc[-2048:].mean()),
                        "answer_lp": float(lp[-64:].sum())})
    return out


def run_answer(llm, tok, chunk, groups, atts, rows):
    items = [(u, g, a) for u in chunk for g, _, a in groups.get(u, [])]
    prompts = [chat_text(tok, answer_prompt(rows[u]["question"], a), "Answer:") for u, _, a in items]
    p = two_way(llm, tok, prompts, ("Yes", "No"))
    return [{"uid": u, "group": g, "answer": a, "p_yes": v} for (u, g, a), v in zip(items, p, strict=True)]


def run_pairwise(llm, tok, chunk, groups, atts, rows):
    items = []
    for u in chunk:
        gs = groups.get(u, [])
        if len(gs) < 2:
            continue
        (g1, k1, _), (g2, k2, _) = gs[0], gs[1]
        for i in range(min(3, len(k1), len(k2))):
            t1 = tail_tokens(tok, atts[(u, k1[i])]["text"], 3000)
            t2 = tail_tokens(tok, atts[(u, k2[i])]["text"], 3000)
            q = rows[u]["question"]
            items.append((u, g1, g2, k1[i], k2[i], "12", chat_text(tok, pairwise_prompt(q, t1, t2), "Answer:")))
            items.append((u, g1, g2, k1[i], k2[i], "21", chat_text(tok, pairwise_prompt(q, t2, t1), "Answer:")))
    p = two_way(llm, tok, [x[-1] for x in items], ("A", "B"))
    # p_first = P(group g1 is the correct one) in this order
    return [{"uid": u, "g1": g1, "g2": g2, "k1": a, "k2": b, "order": o, "p_g1": (v if o == "12" or v is None else 1 - v)}
            for (u, g1, g2, a, b, o, _), v in zip(items, p, strict=True)]


def run_generate(llm, tok, items, n, temperature, max_tokens):
    """items: (meta dict, user prompt). Returns meta + list of completions."""
    from vllm import SamplingParams
    params = SamplingParams(n=n, temperature=temperature, top_p=1.0, max_tokens=max_tokens)
    msgs = [[{"role": "user", "content": p}] for _, p in items]
    outs = llm.chat(msgs, params, lora_request=lora(), use_tqdm=False, chat_template_kwargs={"enable_thinking": False})
    return [dict(m, outputs=[{"text": c.text, "finish_reason": str(c.finish_reason), "tokens": len(c.token_ids)}
                             for c in o.outputs]) for (m, _), o in zip(items, outs, strict=True)]


def run_backward(llm, tok, chunk, groups, atts, rows):
    items = []
    for u in chunk:
        gs = groups.get(u, [])
        if len(gs) < 2:
            continue
        for mi, (masked, val, sym) in enumerate(masks(rows[u]["question"])):
            for g, _, a in gs[:2]:
                row = dict(rows[u], question=backward_question(masked, sym, a))
                items.append(({"uid": u, "group": g, "answer": a, "mask": mi, "value": val}, common.solve_prompt(row)))
    if not items:
        return []
    return run_generate(llm, tok, items, n=2, temperature=1.0, max_tokens=4096)


def run_program(llm, tok, chunk, groups, atts, rows):
    import sandbox
    items = [({"uid": u, "group": g, "answer": a}, program_prompt(rows[u]["question"], a))
             for u in chunk for g, _, a in groups.get(u, [])[:3]]
    res = run_generate(llm, tok, items, n=3, temperature=0.7, max_tokens=3072)
    sandbox.execute_all(res)
    return res


def run_pot(llm, tok, chunk, groups, atts, rows):
    import sandbox
    items = [({"uid": u}, pot_prompt(rows[u]["question"])) for u in chunk]
    res = run_generate(llm, tok, items, n=4, temperature=1.0, max_tokens=3072)
    sandbox.execute_all(res)
    return res


KINDS = {"logprob": (run_logprob, 20480 + 1024, 64, 4096), "answer": (run_answer, 8192, 256, None),
         "pairwise": (run_pairwise, 12288, 128, None), "backward": (run_backward, 12288, 256, None),
         "program": (run_program, 8192, 256, None), "pot": (run_pot, 8192, 256, None)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=sorted(KINDS))
    ap.add_argument("--set", required=True)
    ap.add_argument("--attempts", required=True)
    ap.add_argument("--graded", default="phase3/runs/graded")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--part", default="0/1")
    a = ap.parse_args()

    groups = load_groups(Path(a.graded), a.set)
    uids = common.load_sets()[a.set][: a.limit or None]
    out = Path(a.out) / a.kind / a.set
    out.mkdir(parents=True, exist_ok=True)
    chunks = [uids[i:i + CHUNK] for i in range(0, len(uids), CHUNK)]
    pi, pn = map(int, a.part.split("/"))
    todo = [(i, c) for i, c in enumerate(chunks) if i % pn == pi and not (out / f"{i:03d}.jsonl").exists()]
    print(f"{a.kind} {a.set}: {len(chunks)} chunks, {len(todo)} to do", flush=True)
    if not todo:
        return
    fn, max_len, max_seqs, batched = KINDS[a.kind]
    rows = common.rows_by_uid()
    atts = load_attempts(Path(a.attempts), a.set)
    llm = make_llm(max_len, max_seqs, batched)
    tok = llm.get_tokenizer()
    for i, chunk in todo:
        t0 = time.time()
        res = fn(llm, tok, chunk, groups, atts, rows)
        tmp = out / f"{i:03d}.jsonl.tmp"
        with tmp.open("w") as fh:
            for r in res:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, out / f"{i:03d}.jsonl")
        print(f"{a.kind} {a.set} chunk {i}: {len(res)} records, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
