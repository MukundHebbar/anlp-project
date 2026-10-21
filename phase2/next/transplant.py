#!/usr/bin/env python3
"""B: where does the checking skill live? Layer transplants between the SOLVE and JUDGE adapters.

Hybrid adapters take the SOLVE adapter and replace the LoRA weights of one band of layers with the JUDGE adapter's.
Every adapter is evaluated on (a) the JUDGE task: ProcessBench GSM8K + MATH (1,400) and the synthetic JUDGE test set
(400), same prompt and scoring as processbench_eval.py, and (b) SOLVE: the 200 dev questions x 2 samples.

    python phase2/next/transplant.py build --hybrids DIR
    python phase2/next/transplant.py run --hybrids DIR --out DIR --base <2B> --names a,b,c
    python phase2/next/transplant.py report --out DIR
"""

import argparse, collections, json, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "phase2" / "scripts")); sys.path.insert(0, str(HERE))
import hint_pilot as hp  # noqa: E402
import processbench_eval as pe  # noqa: E402

BANDS = {"J0-5": range(0, 6), "J6-11": range(6, 12), "J12-17": range(12, 18), "J18-23": range(18, 24)}
ADAPTERS = Path.home() / "anlp-final-adapters"
SOLVE_SAMPLES = 2  # overridden by --solve-samples


SRC = {"S": "solve-step66", "J": "judge-step26", "R": "reconstruct-step104", "M": "mixed-step75"}
BASES = {"solve": "S", "judge": "J", "reconstruct": "R", "mixed": "M"}


def parse(name):
    """'solve' -> pure adapter; 'solve+J0-5' -> SOLVE adapter with layers 0..5 from JUDGE; '+J3-3' a single layer;
    several donors: 'solve+J0-5+R6-8'."""
    parts = name.split("+")
    swaps = []
    for p in parts[1:]:
        lo, hi = p[1:].split("-")
        swaps.append((p[0], range(int(lo), int(hi) + 1)))
    return BASES[parts[0]], swaps


def build(a):
    from safetensors.torch import load_file, save_file
    out = Path(a.hybrids); out.mkdir(parents=True, exist_ok=True)
    w = {k: load_file(ADAPTERS / v / "adapter_model.safetensors") for k, v in SRC.items()}
    names = a.names.split(",") if a.names else ["solve", "judge", "mixed"] + [f"solve+{b}" for b in BANDS]
    for name in names:
        base, swaps = parse(name)
        h = dict(w[base])
        import re as _re
        for donor, layers in swaps:
            for k in list(h):
                m = _re.search(r"\.layers\.(\d+)\.", k)
                if not m or int(m.group(1)) not in layers:
                    continue
                if donor == "Z":  # remove the update: LoRA B = 0 keeps the base model's weights in these layers
                    h[k] = w["S"][k] * 0 if "lora_B" in k else h[k]
                elif donor == "X":  # JUDGE weights from 16 layers later (same layer types and statistics, wrong location)
                    src = k.replace(f".layers.{m.group(1)}.", f".layers.{int(m.group(1)) + 16}.")
                    h[k] = w["J"][src]
                else:
                    h[k] = w[donor][k]
        (out / name).mkdir(exist_ok=True)
        save_file(h, str(out / name / "adapter_model.safetensors"))
        shutil.copy(ADAPTERS / SRC[base] / "adapter_config.json", out / name / "adapter_config.json")
    print(sorted(p.name for p in out.iterdir()))


def run(a):
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest
    from anlp_project import baseline, opd
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    names = a.names.split(",")
    items = [x for x in hp.read_jsonl([out / "items.jsonl"]) if x["subset"] in ("gsm8k", "math", "synthetic")]
    rows = opd.slice_rows("solve", "dev")
    s = baseline.EVAL_SAMPLING
    llm = LLM(model=a.base, dtype="bfloat16", language_model_only=True, max_model_len=28672, gpu_memory_utilization=0.90,
              max_num_seqs=256, seed=0, enable_lora=True, max_lora_rank=64, max_loras=len(names))
    jp = SamplingParams(n=1, temperature=s["temperature"], top_p=s["top_p"], top_k=s["top_k"], max_tokens=pe.CAP, seed=0)
    sp = SamplingParams(n=a.solve_samples, temperature=s["temperature"], top_p=s["top_p"], top_k=s["top_k"],
                        max_tokens=16384, seed=0)
    for n, name in enumerate(names):
        want_solve = name in a.solve_names.split(",")
        if (out / f"judge-{name}.jsonl").exists() and (not want_solve or (out / f"solve-{name}.jsonl").exists()):
            continue
        lora = LoRARequest(name, n + 1, str(Path(a.hybrids) / name))
        if (out / f"judge-{name}.jsonl").exists():
            outs = None
        else:
            outs = llm.chat([[{"role": "user", "content": pe.judge_prompt(x)}] for x in items], jp, lora_request=lora,
                            use_tqdm=False, chat_template_kwargs={"enable_thinking": False})
        if outs is not None:
          hp.write_jsonl(out / f"judge-{name}.jsonl", [{"uid": x["uid"], "subset": x["subset"], "label": x["label"],
                       "pred": pe.predict(o.outputs[0].text, str(o.outputs[0].finish_reason))} for x, o in zip(items, outs)])
        if not want_solve:
            print("done", name, flush=True)
            continue
        outs = llm.chat([[{"role": "user", "content": hp.solve_prompt(r)}] for r in rows], sp, lora_request=lora,
                        use_tqdm=False, chat_template_kwargs={"enable_thinking": False})
        hp.write_jsonl(out / f"solve-{name}.jsonl", [{"uid": r["uid"], "sample": k, **hp.score(r, {
            "text": c.text, "finish_reason": str(c.finish_reason), "completion_tokens": len(c.token_ids)})}
            for r, o in zip(rows, outs) for k, c in enumerate(o.outputs)])
        print("done", name, flush=True)


def report(a):
    sys.path.insert(0, str(HERE))
    from sdt import sdt
    out = Path(a.out); res = {}
    for p in sorted(out.glob("judge-*.jsonl")):
        name = p.stem[len("judge-"):]
        recs = hp.read_jsonl([p])
        r = {}
        for grp, subs in (("processbench", ("gsm8k", "math")), ("synthetic", ("synthetic",))):
            g = [{**x, "finish_reason": x.get("finish_reason", "stop")} for x in recs if x["subset"] in subs]
            r[f"{grp}_f1"] = pe.scores(g)["f1"]
            v = [x for x in g if x["pred"] is not None]
            pos = [x for x in v if x["label"] >= 0]; neg = [x for x in v if x["label"] < 0]
            h = sum(x["pred"] >= 0 for x in pos) / len(pos); f = sum(x["pred"] >= 0 for x in neg) / len(neg)
            r[f"{grp}_d_prime"], r[f"{grp}_criterion"] = sdt(h, f, len(pos), len(neg))
        sv = hp.read_jsonl([out / f"solve-{name}.jsonl"]) if (out / f"solve-{name}.jsonl").exists() else []
        r["solve_dev_acc"] = round(100 * sum(x["correct_strict"] for x in sv) / max(1, len(sv)), 1)
        res[name] = r
    (out / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
    print(f"{'adapter':16s} {'PB F1':>6s} {'PB dprime':>9s} {'PB c':>6s} {'syn F1':>6s} {'syn dprime':>10s} {'SOLVE':>6s}")
    for k, r in res.items():
        print(f"{k:16s} {r['processbench_f1']:6.1f} {r['processbench_d_prime']:9.3f} {r['processbench_criterion']:6.2f} "
              f"{r['synthetic_f1']:6.1f} {r['synthetic_d_prime']:10.3f} {r['solve_dev_acc']:6.1f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["build", "run", "report"])
    ap.add_argument("--hybrids", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--base", default="")
    ap.add_argument("--names", default="")
    ap.add_argument("--solve-names", default="", help="adapters that also get the SOLVE dev evaluation")
    ap.add_argument("--solve-samples", type=int, default=2)
    a = ap.parse_args()
    {"build": build, "run": run, "report": report}[a.stage](a)
