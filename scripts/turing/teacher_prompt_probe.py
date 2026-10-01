#!/usr/bin/env python3
"""Does an anti-repetition instruction in the teacher's context change its log-probs on loop tokens?

    python scripts/turing/teacher_prompt_probe.py --responses <responses.jsonl> --out <dir> [--n 60]

Scores the same student answers with the teacher twice: under the task prompt (as in OPD) and
with TEACHER_SYSTEM added as a system message. Tokens are split into "loop" (the 32-token span
ending at the token already appeared earlier in the answer) and "other". A large drop on loop
tokens with little change on other tokens means the instruction would turn the loop tokens'
OPD advantage negative.
"""

import argparse
import json
import statistics as st
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from anlp_project import baseline, opd  # noqa: E402

TEACHER_SYSTEM = opd.TEACHER_INSTRUCTIONS["anti_repetition"]
SPAN = 32
MAX_TOKENS = 6144


def loop_flags(ids):
    seen, flags = set(), []
    for t in range(len(ids)):
        if t + 1 >= SPAN:
            g = tuple(ids[t + 1 - SPAN:t + 1])
            flags.append(g in seen)
            seen.add(g)
        else:
            flags.append(False)
    return flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=60, help="answers per group (looping / normal)")
    ap.add_argument("--task", default="reconstruct")
    ap.add_argument("--system", default=TEACHER_SYSTEM, help="the teacher-only instruction to test")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = {r["uid"]: r for r in opd.slice_rows(a.task, "dev")}
    resp = [json.loads(l) for l in open(a.responses)]
    looping = [x for x in resp if x["finish_reason"] == "length"][: a.n]
    normal = [x for x in resp if x["finish_reason"] == "stop"][: a.n]

    from huggingface_hub import snapshot_download
    from vllm import LLM, SamplingParams

    llm = LLM(model=snapshot_download(opd.TRIAL_CONFIG["teacher"], local_files_only=True), dtype="bfloat16",
              language_model_only=True, tensor_parallel_size=2, max_model_len=MAX_TOKENS + 4096,
              gpu_memory_utilization=0.90, max_num_seqs=32, max_num_batched_tokens=4096, seed=0)
    tok = llm.get_tokenizer()

    def prompt_ids(user, system):
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
        return tok(tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False),
                   add_special_tokens=False)["input_ids"]

    items = []
    for group, xs in (("looping", looping), ("normal", normal)):
        for x in xs:
            ids = tok(x["text"], add_special_tokens=False)["input_ids"][:MAX_TOKENS]
            items.append({"uid": x["uid"], "group": group, "ids": ids, "user": baseline.render_prompt(rows[x["uid"]])})
    params = SamplingParams(max_tokens=1, temperature=0.0, prompt_logprobs=0)
    t0 = time.time()
    scores = {}
    for cond, system in (("task_prompt", None), ("anti_repetition", a.system)):
        reqs, offs = [], []
        for it in items:
            p = prompt_ids(it["user"], system)
            reqs.append({"prompt_token_ids": p + it["ids"]})
            offs.append(len(p))
        outs = llm.generate(reqs, params, use_tqdm=True)
        for it, o, off in zip(items, outs, offs):
            lps = []
            for entry, t in zip(o.prompt_logprobs[off:], it["ids"]):
                lps.append(entry[t].logprob)
            scores[(it["uid"], cond)] = lps
    t1 = time.time()

    per = []
    for it in items:
        flags = loop_flags(it["ids"])
        a_lp, b_lp = scores[(it["uid"], "task_prompt")], scores[(it["uid"], "anti_repetition")]
        rec = {"uid": it["uid"], "group": it["group"], "tokens": len(it["ids"]), "loop_tokens": sum(flags)}
        for name, sel in (("loop", [f for f in flags]), ("other", [not f for f in flags])):
            ia = [x for x, s in zip(a_lp, sel) if s]
            ib = [x for x, s in zip(b_lp, sel) if s]
            if ia:
                rec[f"{name}_lp_task"] = st.mean(ia)
                rec[f"{name}_lp_anti"] = st.mean(ib)
        per.append(rec)
    with (out / "per_answer.jsonl").open("w") as fh:
        for r in per:
            fh.write(json.dumps(r) + "\n")

    summary = {"teacher_system": a.system, "span": SPAN, "max_tokens": MAX_TOKENS, "seconds": round(t1 - t0)}
    for group in ("looping", "normal"):
        g = [r for r in per if r["group"] == group]
        summary[group] = {"answers": len(g), "loop_token_share": sum(r["loop_tokens"] for r in g) / max(1, sum(r["tokens"] for r in g))}
        for name in ("loop", "other"):
            have = [r for r in g if f"{name}_lp_task" in r]
            if have:
                summary[group][f"{name}_tokens_mean_teacher_lp"] = {
                    "task_prompt": round(st.mean(r[f"{name}_lp_task"] for r in have), 4),
                    "anti_repetition": round(st.mean(r[f"{name}_lp_anti"] for r in have), 4),
                    "answers": len(have)}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
