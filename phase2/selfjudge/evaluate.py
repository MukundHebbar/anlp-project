#!/usr/bin/env python3
"""Evaluate judge adapters on the mixed model's own attempts and as an answer picker.

Attempts: phase2/runs/select/<split>/attempts.jsonl (FINAL-v3 SOLVE dev slice 200 x 4, test 400 x 4), shown in the
JUDGE format exactly as in training (the attempt split into numbered steps). Each adapter gives 4 verdicts per attempt.
Reports AUROC (wrong vs right attempts) and the accuracy of picking 1 answer out of 4: majority vote vs votes weighted
by the judge's P(correct), with a paired bootstrap against majority.

    python phase2/selfjudge/evaluate.py run --split dev --base <2B> --adapters name=path,...
    python phase2/selfjudge/evaluate.py report --split dev
"""
import argparse, collections, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "phase2" / "scripts"))
import hint_pilot as hp  # noqa: E402
import functional as F  # noqa: E402

RUNS = REPO / "phase2" / "runs"
VOTES = 4


def run(a):
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest
    from anlp_project import baseline
    atts = [x for x in hp.read_jsonl([RUNS / "select" / a.split / "attempts.jsonl"]) if x.get("answer")]
    out = RUNS / "selfjudge" / "eval" / a.split; out.mkdir(parents=True, exist_ok=True)
    named = [kv.split("=", 1) for kv in a.adapters.split(",")]
    llm = LLM(model=a.base, dtype="bfloat16", language_model_only=True, max_model_len=32768, gpu_memory_utilization=0.90,
              max_num_seqs=256, seed=0, enable_lora=True, max_lora_rank=64, max_loras=len(named))
    s = baseline.EVAL_SAMPLING
    sp = SamplingParams(n=VOTES, temperature=s["temperature"], top_p=s["top_p"], top_k=s["top_k"], max_tokens=8192, seed=0)
    prompts = [[{"role": "user", "content": F.judge_prompt(x["problem"], x["steps"])}] for x in atts]
    for i, (name, path) in enumerate(named):
        if (out / f"{name}.jsonl").exists():
            continue
        o = llm.chat(prompts, sp, lora_request=LoRARequest(name, i + 1, path), use_tqdm=False,
                     chat_template_kwargs={"enable_thinking": False})
        recs = []
        for x, r in zip(atts, o):
            v = F.judge_vote([c.text for c in r.outputs])["votes"]
            recs.append({"uid": x["uid"], "attempt": x["attempt"], "correct": x["correct"],
                         "p_incorrect": sum(d == "incorrect" for d, _ in v) / VOTES,
                         "no_verdict": sum(d is None for d, _ in v) / VOTES})
        hp.write_jsonl(out / f"{name}.jsonl", recs)
        print("done", name, flush=True)


def report(a):
    atts = hp.read_jsonl([RUNS / "select" / a.split / "attempts.jsonl"])
    by = collections.defaultdict(list)
    for x in atts:
        by[x["uid"]].append(x)
    qs = sorted(by)

    def clusters(xs):
        cl = []
        for x in xs:
            if not x.get("answer"):
                continue
            c = next((c for c in cl if F.same_answer(c[0]["answer"], x["answer"])), None)
            c.append(x) if c else cl.append([x])
        return sorted(cl, key=len, reverse=True)
    cl = {u: clusters(by[u]) for u in qs}
    maj = {u: float(cl[u][0][0]["correct"]) if cl[u] else 0.0 for u in qs}
    res = {"problems": len(qs), "one attempt": round(100 * sum(x["correct"] for x in atts) / len(atts), 1),
           "best possible": round(100 * sum(any(x["correct"] for x in by[u]) for u in qs) / len(qs), 1),
           "majority": round(100 * sum(maj.values()) / len(qs), 1)}
    rng = random.Random(0)
    for p in sorted((RUNS / "selfjudge" / "eval" / a.split).glob("*.jsonl")):
        rec = {(r["uid"], r["attempt"]): r for r in hp.read_jsonl([p])}
        w = [r for r in rec.values()]
        auroc = F.auroc([r["p_incorrect"] for r in w if not r["correct"]], [r["p_incorrect"] for r in w if r["correct"]])
        pick = {}
        for u in qs:
            if not cl[u]:
                pick[u] = 0.0
                continue
            best = max(cl[u], key=lambda c: sum(1 - rec[(x["uid"], x["attempt"])]["p_incorrect"] + 1e-3 for x in c))
            pick[u] = float(best[0]["correct"])
        d = [pick[u] - maj[u] for u in qs]
        bs = sorted(100 * sum(d[rng.randrange(len(qs))] for _ in qs) / len(qs) for _ in range(2000))
        res[p.stem] = {"auroc_own_attempts": round(auroc, 3),
                       "no_verdict_share": round(100 * sum(r["no_verdict"] for r in w) / len(w), 1),
                       "pick_1_of_4": round(100 * sum(pick.values()) / len(qs), 1),
                       "vs_majority": f"{100 * sum(d) / len(qs):+.1f} [{bs[50]:+.1f}, {bs[1949]:+.1f}]"}
    (RUNS / "selfjudge" / "eval" / f"{a.split}-summary.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run", "report"])
    ap.add_argument("--split", default="dev"); ap.add_argument("--base", default=""); ap.add_argument("--adapters", default="")
    a = ap.parse_args()
    {"run": run, "report": report}[a.stage](a)
