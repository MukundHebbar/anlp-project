#!/usr/bin/env python3
"""B3: the SOLVE + JUDGE-early-layers composite on harder ProcessBench, on the model's own attempts, and on the SOLVE
test set, against the plain adapters.

    python phase2/next/transplant3.py run --hybrids DIR --out DIR --base <2B> --names a,b --parts hard,own,test
    python phase2/next/transplant3.py report --out DIR
"""
import argparse, collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "phase2" / "scripts")); sys.path.insert(0, str(HERE))
import hint_pilot as hp  # noqa: E402
import functional as F  # noqa: E402
import processbench_eval as pe  # noqa: E402

RUNS = REPO / "phase2" / "runs"
VOTES = 4


def own_sources():
    return {"own-step": hp.read_jsonl(sorted((RUNS / "stepformat").glob("judged-shard*.jsonl"))),
            "condensed": hp.read_jsonl([RUNS / "crossjudge" / "attempts-condensed.jsonl"])}


def run(a):
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest
    from anlp_project import baseline
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    names = a.names.split(","); parts = a.parts.split(",")
    s = baseline.EVAL_SAMPLING
    llm = LLM(model=a.base, dtype="bfloat16", language_model_only=True, max_model_len=32768, gpu_memory_utilization=0.90,
              max_num_seqs=256, seed=0, enable_lora=True, max_lora_rank=64, max_loras=len(names))
    sp = lambda n, cap: SamplingParams(n=n, temperature=s["temperature"], top_p=s["top_p"], top_k=s["top_k"],  # noqa: E731
                                       max_tokens=cap, seed=0)
    chat = lambda prompts, p, lora: llm.chat([[{"role": "user", "content": x}] for x in prompts], p, lora_request=lora,  # noqa: E731
                                             use_tqdm=False, chat_template_kwargs={"enable_thinking": False})
    hard = [x for x in hp.read_jsonl([RUNS / "transplant" / "items.jsonl"]) if x["subset"] in ("olympiadbench", "omnimath")]
    test_rows = baseline.load_rows("solve", "test")
    for n, name in enumerate(names):
        lora = LoRARequest(name, n + 1, str(Path(a.hybrids) / name))
        if "hard" in parts and not (out / f"hard-{name}.jsonl").exists():
            o = chat([pe.judge_prompt(x) for x in hard], sp(1, pe.CAP), lora)
            hp.write_jsonl(out / f"hard-{name}.jsonl", [{"uid": x["uid"], "subset": x["subset"], "label": x["label"],
                           "pred": pe.predict(r.outputs[0].text, str(r.outputs[0].finish_reason))} for x, r in zip(hard, o)])
        if "own" in parts and not (out / f"own-{name}.jsonl").exists():
            recs = []
            for src, atts in own_sources().items():
                atts = [x for x in atts if x.get("answer")]
                o = chat([F.judge_prompt(x["problem"], x["steps"]) for x in atts], sp(VOTES, 6144), lora)
                for x, r in zip(atts, o):
                    v = F.judge_vote([c.text for c in r.outputs])
                    recs.append({"source": src, "uid": x["uid"], "attempt": x["attempt"], "correct": x["correct"],
                                 "p_incorrect": sum(d == "incorrect" for d, _ in v["votes"]) / VOTES})
            hp.write_jsonl(out / f"own-{name}.jsonl", recs)
        if "test" in parts and not (out / f"test-{name}.jsonl").exists():
            o = chat([hp.solve_prompt(r) for r in test_rows], sp(4, 16384), lora)
            hp.write_jsonl(out / f"test-{name}.jsonl", [{"uid": r["uid"], "sample": k, **hp.score(r, {
                "text": c.text, "finish_reason": str(c.finish_reason), "completion_tokens": len(c.token_ids)})}
                for r, x in zip(test_rows, o) for k, c in enumerate(x.outputs)])
        print("done", name, flush=True)


def report(a):
    out = Path(a.out); res = {}
    for p in sorted(out.glob("*-*.jsonl")):
        part, name = p.stem.split("-", 1)
        recs = hp.read_jsonl([p]); r = res.setdefault(name, {})
        if part == "hard":
            for sub in ("olympiadbench", "omnimath"):
                g = [{**x, "finish_reason": "stop"} for x in recs if x["subset"] == sub]
                sc = pe.scores(g); r[f"{sub}_f1"] = sc["f1"]
                err = [x for x in g if x["label"] >= 0 and x["pred"] is not None]
                r[f"{sub}_exact_given_verdict"] = round(100 * sum(x["pred"] == x["label"] for x in err) / max(1, len(err)), 1)
        elif part == "own":
            for src in ("own-step", "condensed"):
                g = [x for x in recs if x["source"] == src]
                r[f"{src}_auroc"] = round(F.auroc([x["p_incorrect"] for x in g if not x["correct"]],
                                                  [x["p_incorrect"] for x in g if x["correct"]]), 3)
        elif part == "test":
            r["solve_test_acc"] = round(100 * sum(x["correct_strict"] for x in recs) / len(recs), 2)
            q = collections.defaultdict(list)
            for x in recs:
                q[x["uid"]].append(x["correct_strict"])
            r["solve_test_pass@4"] = round(100 * sum(any(v) for v in q.values()) / len(q), 2)
    (out / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run", "report"])
    ap.add_argument("--hybrids", default=""); ap.add_argument("--out", required=True); ap.add_argument("--base", default="")
    ap.add_argument("--names", default=""); ap.add_argument("--parts", default="hard,own,test")
    a = ap.parse_args()
    {"run": run, "report": report}[a.stage](a)
