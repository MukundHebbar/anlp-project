#!/usr/bin/env python3
"""Error-feature follow-ups: score solution steps with the crosscoder features (base + mixed adapter on one model).

`steps` reads solutions from several sources, runs the JUDGE-prompt rendering through the model twice (mixed adapter
on and off, as in crosscoder.py), encodes each step's tokens with the trained crosscoders and saves step-level mean
activations of every latent (layers 12 and 18). Normalization uses the scale of the crosscoder's own training data.

Sources (name: file, step labels):
  pb-easy     ProcessBench GSM8K + MATH (the crosscoder's own data; checks the pipeline)       first-error step
  pb-hard     ProcessBench OlympiadBench + Omni-MATH (unseen)                                    first-error step
  own-free    the mixed model's 800 normal-format dev attempts (functional.py drift run)         answer correct?
  own-step    the mixed model's 800 step-format dev attempts (stepformat.py)                     answer correct?
  base-step, 9b-step, condensed   attempts from crossjudge.py, when present                      answer correct?

    python phase2/next/errfeat.py steps --acts <crosscoder acts dir> --out DIR --base <2B> --sources a,b
"""

import argparse, json, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "phase2" / "scripts")); sys.path.insert(0, str(HERE))
import hint_pilot as hp  # noqa: E402

LAYERS = (12, 18)
TOPK = 32
RUNS = REPO / "phase2" / "runs"


def load_source(name):
    if name in ("pb-easy", "pb-hard"):
        subs = ("gsm8k", "math") if name == "pb-easy" else ("olympiadbench", "omnimath")
        out = []
        for sub in subs:
            for x in json.load(open(REPO / "phase2" / "data" / "processbench" / f"{sub}.json")):
                out.append({"uid": f"pb-{x['id']}", "subset": sub, "problem": x["problem"], "steps": x["steps"],
                            "label": x["label"]})
        return out
    if name == "synthetic":  # FINAL-v3 JUDGE test set: DeepMath problems, one injected first error or none
        from anlp_project import baseline
        out = []
        for r in baseline.load_rows("judge", "test"):
            p = r["private"]
            out.append({"uid": r["uid"], "subset": "synthetic", "problem": r["public"]["problem"],
                        "steps": [s["text"] for s in r["public"]["proposed_solution"]],
                        "label": -1 if p["label"] == "correct" else int(p["first_error_step_id"][1:]) - 1})
        return out
    files = {"own-free": sorted((REPO / "runs-out" / "functional" / "drift").glob("attempts-shard*.jsonl")),
             "own-step": sorted((RUNS / "stepformat").glob("judged-shard*.jsonl")),
             "base-step": [RUNS / "crossjudge" / "attempts-base.jsonl"],
             "9b-step": [RUNS / "crossjudge" / "attempts-9b.jsonl"],
             "condensed": [RUNS / "crossjudge" / "attempts-condensed.jsonl"]}[name]
    files = [f for f in files if f.exists()]
    if not files:
        return []
    out = []
    for x in hp.read_jsonl(files):
        if not x.get("answer") or not x.get("steps"):
            continue
        out.append({"uid": f"{x['uid']}#{x['attempt']}", "question": x["uid"], "attempt": x["attempt"],
                    "problem": x["problem"], "steps": x["steps"], "correct": bool(x["correct"]), "answer": x["answer"]})
    return out


def steps(a):
    import torch
    from peft import PeftModel
    from transformers import AutoTokenizer, Qwen3_5ForConditionalGeneration
    import functional as F

    acts = Path(a.acts)
    scale = {}
    for m in ("base", "mixed"):
        for L in LAYERS:
            x = np.load(acts / f"{m}-L{L}.npy", mmap_mode="r")
            norms = np.concatenate([np.linalg.norm(np.asarray(x[s:s + 65536], dtype=np.float32), axis=1)
                                    for s in range(0, len(x), 65536)])
            scale[(m, L)] = float(norms.mean()) / (x.shape[1] ** 0.5 / 10)
    cc = {L: {k: v.cuda() for k, v in torch.load(acts / f"crosscoder-L{L}.pt").items()} for L in LAYERS}
    tok = AutoTokenizer.from_pretrained(a.base)
    model = Qwen3_5ForConditionalGeneration.from_pretrained(a.base, dtype=torch.bfloat16).to("cuda").eval()
    model = PeftModel.from_pretrained(model, str(Path(a.adapters) / "mixed-step75")).eval()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for src in a.sources.split(","):
        if (out / f"{src}.npz").exists():
            continue
        items = load_source(src)
        if not items:
            print("skip", src, "(no data)", flush=True)
            continue
        feats = {L: [] for L in LAYERS}
        meta = []
        for i, it in enumerate(items):
            user = F.judge_prompt(it["problem"], it["steps"])
            text = tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False,
                                           add_generation_prompt=True, enable_thinking=False)
            enc = tok(text, return_offsets_mapping=True, return_tensors="pt", truncation=True, max_length=30000)
            offs = enc.pop("offset_mapping")[0].tolist()
            spans, pos = [], 0
            for j, s in enumerate(it["steps"], 1):
                k = text.find(f"S{j}: {s}", pos)
                if k < 0:
                    break
                spans.append((k, k + len(f"S{j}: {s}"))); pos = k + 1
            if not spans:
                continue
            tstep = np.array([next((j for j, (s0, s1) in enumerate(spans) if s0 <= o0 < s1), -1) for o0, _ in offs])
            ids = enc["input_ids"].to("cuda")
            with torch.no_grad():
                hm = model(input_ids=ids, output_hidden_states=True).hidden_states
                with model.disable_adapter():
                    hb = model(input_ids=ids, output_hidden_states=True).hidden_states
                for L in LAYERS:
                    sel = torch.from_numpy(np.flatnonzero(tstep >= 0)).cuda()
                    xb = hb[L][0, sel].float() / scale[("base", L)]
                    xm = hm[L][0, sel].float() / scale[("mixed", L)]
                    w = cc[L]
                    pre = torch.relu(torch.cat([xb, xm], 1) @ w["W_enc"] + w["b_enc"])
                    v, ix = pre.topk(TOPK, dim=1)
                    z = torch.zeros_like(pre).scatter_(1, ix, v)
                    st = torch.from_numpy(tstep[tstep >= 0]).cuda()
                    n = len(spans)
                    sums = torch.zeros(n, z.shape[1], device="cuda").index_add_(0, st, z)
                    cnt = torch.zeros(n, device="cuda").index_add_(0, st, torch.ones(len(st), device="cuda"))
                    feats[L].append((sums / cnt.clamp(min=1).unsqueeze(1)).half().cpu().numpy())
            meta += [(i, j) for j in range(len(spans))]
            if i % 200 == 0:
                print(src, i, len(items), flush=True)
        np.savez(out / f"{src}.npz", meta=np.array(meta, dtype=np.int32),
                 **{f"L{L}": np.concatenate(feats[L]) for L in LAYERS})
        json.dump(items, open(out / f"{src}-items.json", "w"))
        print("saved", src, len(meta), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["steps"])
    ap.add_argument("--acts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default="")
    ap.add_argument("--sources", default="pb-easy,pb-hard,own-free,own-step,base-step,9b-step,condensed")
    ap.add_argument("--adapters", default=str(Path.home() / "anlp-final-adapters"))
    a = ap.parse_args()
    steps(a)
