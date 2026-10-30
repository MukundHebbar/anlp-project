"""Sampling experiments T2 and T3 (vLLM, Qwen3.5-2B + mixed adapter). Resumable by chunk.

    python phase3/sampling_gen.py resample --set test --attempts <root>/attempts --graded phase3/runs/graded --out <root>/samp
    python phase3/sampling_gen.py temp --config hot --set test --out <root>/samp

resample (T2, lock-in curve): on questions where the right answer was sampled and the solver also has an attractor (its
    most common wrong answer, >= 2 attempts), take the first finished attractor attempt and the first right attempt,
    cut each at 25 / 50 / 75 % of its characters (moved back to the nearest paragraph break, before the answer tag),
    and sample 4 continuations from each prefix (T 1.0, the 16k total cap). This is the proposal of block
    Metropolis-Hastings power sampling; here it measures when the attractor is locked in.
temp (T3, temperature as a decorrelator): 8 fresh attempts per question with
    t07  T 0.7
    t13  T 1.3, min-p 0.05
    hot  T 1.3, min-p 0.05 for the first 512 tokens, then T 0.8 to the 16k cap (two-stage)
Answers are extracted and grouped on CPU afterwards.
"""

import argparse
import json
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import common
from evidence import CHUNK, chat_text, load_attempts, lora, make_llm

CUTS = (0.25, 0.5, 0.75)
CONFIGS = {"t07": dict(temperature=0.7), "t13": dict(temperature=1.3, min_p=0.05),
           "hot": dict(temperature=1.3, min_p=0.05)}
HOT_TOKENS, HOT_REST_T = 512, 0.8
_TAG = re.compile(r"<final_answer>", re.IGNORECASE)


def targets(graded: Path, split: str):
    """uid -> (attractor k, right k) for questions with a right attempt and an attractor wrong group (>= 2)."""
    by_q = defaultdict(list)
    for line in (graded / f"{split}.jsonl").open():
        r = json.loads(line)
        by_q[r["uid"]].append(r)
    out = {}
    for u, rs in by_q.items():
        rs.sort(key=lambda r: r["k"])
        right = [r for r in rs if r["answer_matches"] and r["finish_reason"] == "stop"]
        wrong = Counter(r["group"] for r in rs if r["group"] >= 0 and not r["answer_matches"])
        if not right or not wrong:
            continue
        g, c = wrong.most_common(1)[0]
        if c < 2:
            continue
        att = next(r for r in rs if r["group"] == g)
        out[u] = (att["k"], right[0]["k"], g)
    return out


def cut(text, frac):
    m = _TAG.search(text)
    body = text[: m.start()] if m else text
    pos = int(len(body) * frac)
    br = body.rfind("\n\n", 0, pos)
    return body[: br + 2] if br > 0 else body[:pos]


def run_resample(llm, tok, chunk, a, rows, atts, tg):
    from vllm import SamplingParams
    from vllm.inputs import TokensPrompt
    s = common.SOLVE_SAMPLING
    items = []
    for u in chunk:
        if u not in tg:
            continue
        ka, kr, g = tg[u]
        head = len(tok.encode(chat_text(tok, common.solve_prompt(rows[u])), add_special_tokens=False))
        for role, k in (("attractor", ka), ("right", kr)):
            for f in CUTS:
                prefix = cut(atts[(u, k)]["text"], f)
                ids = tok.encode(chat_text(tok, common.solve_prompt(rows[u]), prefix), add_special_tokens=False)
                items.append(({"uid": u, "role": role, "k": k, "attractor_group": g, "cut": f,
                               "prefix_chars": len(prefix), "prefix_tokens": len(ids) - head}, ids))
    if not items:
        return []
    # same total budget as the original attempts: prefix + continuation <= the 16k cap
    params = [SamplingParams(n=4, temperature=1.0, top_p=1.0, max_tokens=max(256, s["max_tokens"] - m["prefix_tokens"]))
              for m, _ in items]
    outs = llm.generate([TokensPrompt(prompt_token_ids=ids) for _, ids in items], params, lora_request=lora(),
                        use_tqdm=False)
    res = []
    for (m, _), o in zip(items, outs, strict=True):
        res.append(dict(m, outputs=[{"text": c.text, "finish_reason": str(c.finish_reason), "tokens": len(c.token_ids)}
                                    for c in o.outputs]))
    return res


def run_temp(llm, tok, chunk, a, rows, atts, tg):
    from vllm import SamplingParams
    from vllm.inputs import TokensPrompt
    s = common.SOLVE_SAMPLING
    cfg = CONFIGS[a.config]
    heads = [tok.encode(chat_text(tok, common.solve_prompt(rows[u])), add_special_tokens=False) for u in chunk]
    if a.config != "hot":
        outs = llm.generate([TokensPrompt(prompt_token_ids=h) for h in heads],
                            SamplingParams(n=8, top_p=1.0, max_tokens=s["max_tokens"], **cfg), lora_request=lora(),
                            use_tqdm=False)
        return [{"uid": u, "k": k, "text": c.text, "finish_reason": str(c.finish_reason),
                 "completion_tokens": len(c.token_ids)} for u, o in zip(chunk, outs, strict=True)
                for k, c in enumerate(o.outputs)]
    first = llm.generate([TokensPrompt(prompt_token_ids=h) for h in heads],
                         SamplingParams(n=8, top_p=1.0, max_tokens=HOT_TOKENS, **cfg), lora_request=lora(),
                         use_tqdm=False)
    stage = []  # (uid, k, head ids, first token ids, first text, finish)
    for u, h, o in zip(chunk, heads, first, strict=True):
        for k, c in enumerate(o.outputs):
            stage.append((u, k, h, list(c.token_ids), c.text, str(c.finish_reason)))
    todo = [x for x in stage if x[5] == "length"]
    rest = llm.generate([TokensPrompt(prompt_token_ids=h + t) for _, _, h, t, _, _ in todo],
                        SamplingParams(n=1, temperature=HOT_REST_T, top_p=1.0, max_tokens=s["max_tokens"] - HOT_TOKENS),
                        lora_request=lora(), use_tqdm=False)
    cont = {(x[0], x[1]): o.outputs[0] for x, o in zip(todo, rest, strict=True)}
    res = []
    for u, k, _, t, text, fin in stage:
        c = cont.get((u, k))
        res.append({"uid": u, "k": k, "text": text + (c.text if c else ""),
                    "finish_reason": str(c.finish_reason) if c else fin,
                    "completion_tokens": len(t) + (len(c.token_ids) if c else 0)})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=("resample", "temp"))
    ap.add_argument("--set", required=True)
    ap.add_argument("--attempts", default="")
    ap.add_argument("--graded", default="phase3/runs/graded")
    ap.add_argument("--config", default="", choices=("",) + tuple(CONFIGS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--part", default="0/1")
    a = ap.parse_args()
    name = a.kind if a.kind == "resample" else f"temp-{a.config}"
    uids = common.load_sets()[a.set][: a.limit or None]
    out = Path(a.out) / name / a.set
    out.mkdir(parents=True, exist_ok=True)
    chunks = [uids[i:i + CHUNK] for i in range(0, len(uids), CHUNK)]
    pi, pn = map(int, a.part.split("/"))
    todo = [(i, c) for i, c in enumerate(chunks) if i % pn == pi and not (out / f"{i:03d}.jsonl").exists()]
    print(f"{name} {a.set}: {len(chunks)} chunks, {len(todo)} to do", flush=True)
    if not todo:
        return
    rows = common.rows_by_uid()
    atts = load_attempts(Path(a.attempts), a.set) if a.kind == "resample" else {}
    tg = targets(Path(a.graded), a.set) if a.kind == "resample" else {}
    llm = make_llm(common.SOLVE_SAMPLING["max_tokens"] + 4096, 512)
    tok = llm.get_tokenizer()
    fn = run_resample if a.kind == "resample" else run_temp
    for i, chunk in todo:
        t0 = time.time()
        res = fn(llm, tok, chunk, a, rows, atts, tg)
        tmp = out / f"{i:03d}.jsonl.tmp"
        with tmp.open("w") as fh:
            for r in res:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, out / f"{i:03d}.jsonl")
        print(f"{name} {a.set} chunk {i}: {len(res)} records, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
