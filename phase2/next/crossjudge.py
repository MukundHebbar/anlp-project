#!/usr/bin/env python3
"""C: can a model see its own mistakes? JUDGE on its own vs other models' attempts, format and length matched.

Sources (200 SOLVE dev questions x 4 attempts, all in the step format of stepformat.py):
  own        the mixed model's attempts (phase2/runs/stepformat, already judged)
  base       the untrained 2B's attempts
  9b         Qwen3.5-9B's attempts
  condensed  the mixed model's own attempts rewritten by the 9B into 5-8 short steps, keeping the reasoning and the
             final answer (kept only if the final answer is unchanged)
Judges: the JUDGE specialist and the mixed model, 4 votes each. Metric: AUROC of the share of "incorrect" votes,
wrong vs right attempts (by the answer checker), plus d' and criterion.

    python phase2/next/crossjudge.py gen --source base|9b --out DIR --model <path>
    python phase2/next/crossjudge.py condense --out DIR --model <9B path> --own DIR
    python phase2/next/crossjudge.py judge --source base|9b|condensed --out DIR --base <2B>
    python phase2/next/crossjudge.py report --out DIR --own DIR
"""

import argparse, collections, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "phase2" / "scripts")); sys.path.insert(0, str(HERE))
import hint_pilot as hp  # noqa: E402
import functional as F  # noqa: E402
import stepformat as SF  # noqa: E402

CONDENSE = ("Below is a student's solution to a mathematics problem.\n\nPROBLEM:\n{p}\n\nSTUDENT SOLUTION:\n{s}\n\n"
            "Rewrite the student's solution as 5 to 8 short numbered steps, one per line, starting with \"S1:\", "
            "\"S2:\", and so on. Each step is one claim or computation from the student's solution. Keep the student's "
            "reasoning exactly as it is, including any mistakes: do not correct, add or remove reasoning, and do not "
            "check the work. Keep the student's final answer. End with <final_answer>...</final_answer> containing the "
            "student's final answer.")


def llm(path, lora):
    from vllm import LLM
    return LLM(model=path, dtype="bfloat16", language_model_only=True, max_model_len=32768, gpu_memory_utilization=0.90,
               max_num_seqs=128 if not lora else 256, seed=0, enable_lora=lora, **({"max_lora_rank": 64} if lora else {}))


def chat(m, prompts, n, cap):
    from vllm import SamplingParams
    from anlp_project import baseline
    s = baseline.EVAL_SAMPLING
    p = SamplingParams(n=n, temperature=s["temperature"], top_p=s["top_p"], top_k=s["top_k"], max_tokens=cap, seed=0)
    return m.chat([[{"role": "user", "content": x}] for x in prompts], p, use_tqdm=False,
                  chat_template_kwargs={"enable_thinking": False})


def gen(a):
    from anlp_project import opd
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    path = out / f"attempts-{a.source}.jsonl"
    if path.exists():
        return
    rows = opd.slice_rows("solve", "dev")
    outs = chat(llm(a.model, False), [SF.solve_prompt(r) for r in rows], SF.ATTEMPTS, SF.CAP)
    atts = []
    for r, o in zip(rows, outs):
        for k, c in enumerate(o.outputs):
            resp = {"text": c.text, "finish_reason": str(c.finish_reason), "completion_tokens": len(c.token_ids)}
            sc = hp.score(r, resp); steps, parsed = SF.split_steps(c.text)
            atts.append({"uid": r["uid"], "attempt": k, "problem": r["question"], "key": r["final_answer"], "steps": steps,
                         "step_format": parsed, "tokens": len(c.token_ids), "finish_reason": resp["finish_reason"],
                         "answer": sc["extracted_answer"], "correct": sc["correct_strict"]})
    hp.write_jsonl(path, atts)


def condense(a):
    from anlp_project import baseline
    out = Path(a.out); path = out / "attempts-condensed.jsonl"
    if path.exists():
        return
    own = hp.read_jsonl(sorted(Path(a.own).glob("judged-shard*.jsonl")))
    own = [x for x in own if x["answer"] and x["finish_reason"] == "stop"]
    outs = chat(llm(a.model, False), [CONDENSE.format(p=x["problem"], s=x["text"]) for x in own], 1, 4096)
    kept = []
    for x, o in zip(own, outs):
        t = o.outputs[0].text
        ans = baseline.extract_solve_answer(t)[0]
        if not F.same_answer(ans, x["answer"]):
            continue
        steps, parsed = SF.split_steps(t)
        if not parsed or not 3 <= len(steps) <= 10:
            continue
        kept.append({k: x[k] for k in ("uid", "attempt", "problem", "key", "answer", "correct")} |
                    {"steps": steps, "tokens": len(o.outputs[0].token_ids), "step_format": True})
    hp.write_jsonl(path, kept)
    print("condensed kept", len(kept), "of", len(own), flush=True)


def judge(a):
    out = Path(a.out); path = out / f"judged-{a.source}.jsonl"
    if path.exists():
        return
    atts = hp.read_jsonl([out / f"attempts-{a.source}.jsonl"])
    eng = hp.Engine(a.base, Path(a.adapters), 32768)
    for name, adapter in (("spec", "judge"), ("mixed", "mixed")):
        jt = F.gen(eng, [F.judge_prompt(x["problem"], x["steps"]) for x in atts], adapter, SF.VOTES, SF.JUDGE_CAP)
        for x, texts in zip(atts, jt):
            v = F.judge_vote(texts)
            x[f"{name}_judge"] = v
            x[f"{name}_p_incorrect"] = sum(d == "incorrect" for d, _ in v["votes"]) / SF.VOTES
    hp.write_jsonl(path, atts)


def report(a):
    from sdt import sdt
    out = Path(a.out)
    srcs = {"own (mixed, step format)": hp.read_jsonl(sorted(Path(a.own).glob("judged-shard*.jsonl")))}
    for s, nm in (("base", "untrained 2B"), ("9b", "Qwen3.5-9B"), ("condensed", "own, condensed by 9B")):
        p = out / f"judged-{s}.jsonl"
        if p.exists():
            srcs[nm] = hp.read_jsonl([p])
    res = {}
    for nm, atts in srcs.items():
        atts = [x for x in atts if x.get("answer")]
        w = [x for x in atts if not x["correct"]]; r_ = [x for x in atts if x["correct"]]
        row = {"attempts": len(atts), "accuracy": round(100 * len(r_) / len(atts), 1),
               "mean_tokens": round(sum(x["tokens"] for x in atts) / len(atts)),
               "mean_steps": round(sum(len(x["steps"]) for x in atts) / len(atts), 1)}
        for j in ("spec", "mixed"):
            row[f"{j}_auroc"] = round(F.auroc([x[f"{j}_p_incorrect"] for x in w], [x[f"{j}_p_incorrect"] for x in r_]), 3)
            h = sum(x[f"{j}_judge"]["verdict"] == "incorrect" for x in w) / len(w)
            f = sum(x[f"{j}_judge"]["verdict"] == "incorrect" for x in r_) / len(r_)
            row[f"{j}_d_prime"], row[f"{j}_criterion"] = sdt(h, f, len(w), len(r_))
        res[nm] = row
    (out / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["gen", "condense", "judge", "report"])
    ap.add_argument("--source", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="")
    ap.add_argument("--base", default="")
    ap.add_argument("--own", default="phase2/runs/stepformat")
    ap.add_argument("--adapters", default=str(Path.home() / "anlp-final-adapters"))
    a = ap.parse_args()
    {"gen": gen, "condense": condense, "judge": judge, "report": report}[a.stage](a)
