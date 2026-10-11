#!/usr/bin/env python3
"""Synthetic vs natural errors: the JUDGE task on ProcessBench and on the FINAL-v3 JUDGE test set, same protocol.

ProcessBench (Zheng et al., 2024; huggingface.co/datasets/Qwen/ProcessBench) holds 3,400 solutions written by other
models to GSM8K, MATH, OlympiadBench and Omni-MATH problems, each labelled with the index of its first wrong step
(0-based) or -1 if correct. The FINAL-v3 JUDGE test set holds 400 solutions with one injected error (or none). Both
are rendered in the JUDGE student format ("Problem / Proposed solution / S1: ... / Decide ...") and answered with the
JUDGE prompt v2, one sample, protocol-v2 sampling, a 16k-token cap.

Prediction: "Decision: correct" -> -1; "Decision: incorrect" with "First wrong step: Sk" -> k-1; anything else
(unparsed, gated, capped) counts as wrong. Metrics as in ProcessBench: accuracy on erroneous solutions (exact first
error), accuracy on correct solutions, and their harmonic mean (F1), per subset.

    python scripts/phase2/processbench_eval.py prepare --pb-dir <dir with gsm8k.json ...> --out <dir>
    python scripts/phase2/processbench_eval.py run --out <dir> --models judge,mixed --base <2B path> [--big9 <9B path>]
    python scripts/phase2/processbench_eval.py report --out <dir>
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE))
import hint_pilot as hp  # noqa: E402
from anlp_project import baseline  # noqa: E402
from anlp_project.strict_gates import judge_gate  # noqa: E402

PB_SUBSETS = ("gsm8k", "math", "olympiadbench", "omnimath")
ADAPTERS = {"solve": "solve-step66", "judge": "judge-step26", "reconstruct": "reconstruct-step104", "mixed": "mixed-step75"}
MODELS = ("base", "solve", "judge", "reconstruct", "mixed", "qwen3.5-9b")
CAP = 16384
# Reference: JUDGE error-finding on the same test set in the GRPO report (1 sample, 32k two-pass protocol).
REPORT_ERROR_FINDING = {"base": 34.8, "solve": 43.5, "judge": 52.0, "reconstruct": 49.0, "mixed": 67.0, "qwen3.5-9b": 87.9}


def prepare(a) -> None:
    items = []
    for sub in PB_SUBSETS:
        for x in json.load(open(Path(a.pb_dir) / f"{sub}.json")):
            items.append({"uid": f"pb-{x['id']}", "subset": sub, "generator": x["generator"], "problem": x["problem"],
                          "steps": x["steps"], "label": x["label"]})
    for r in baseline.load_rows("judge", "test"):
        p = r["private"]
        items.append({"uid": r["uid"], "subset": "synthetic", "generator": "deepseek-injected",
                      "problem": r["public"]["problem"], "steps": [s["text"] for s in r["public"]["proposed_solution"]],
                      "label": -1 if p["label"] == "correct" else int(p["first_error_step_id"][1:]) - 1})
    hp.write_jsonl(Path(a.out) / "items.jsonl", items)
    print(collections.Counter(x["subset"] for x in items))


def judge_prompt(x: dict) -> str:
    tmpl = baseline.PROMPT_FILES["judge"].read_text(encoding="utf-8").strip()
    body = (f"Problem:\n{x['problem']}\n\nProposed solution:\n"
            + "\n".join(f"S{i}: {s}" for i, s in enumerate(x["steps"], 1)) + f"\n\n{hp.JUDGE_INSTRUCTION}")
    return hp.render_template(tmpl, {"JUDGE_INPUT": body})


def predict(text: str, finish: str) -> int | None:
    if finish != "stop" or judge_gate(text):
        return None
    decision, step = baseline.parse_judge_response(text)
    if decision == "correct" and step in (None, "none"):
        return -1
    if decision == "incorrect" and step and step != "none":
        return int(step[1:]) - 1
    return None


def run(a) -> None:
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    out = Path(a.out)
    items = hp.read_jsonl([out / "items.jsonl"])
    prompts = [judge_prompt(x) for x in items]
    s = baseline.EVAL_SAMPLING
    params = SamplingParams(n=1, temperature=s["temperature"], top_p=s["top_p"], top_k=s["top_k"], max_tokens=CAP,
                            seed=s["seed"])
    small = [m for m in a.models.split(",") if m != "qwen3.5-9b"]
    jobs = []
    if small:
        llm = LLM(model=a.base, dtype="bfloat16", language_model_only=True, max_model_len=CAP + 12288,
                  gpu_memory_utilization=0.90, max_num_seqs=256, seed=0, enable_lora=True, max_lora_rank=64, max_loras=4)
        for m in small:
            lora = LoRARequest(m, list(ADAPTERS).index(m) + 1, str(Path(a.adapters) / ADAPTERS[m])) if m != "base" else None
            jobs.append((m, llm, lora))
        for m, llm_, lora in jobs:
            write(out, m, items, llm_.chat([[{"role": "user", "content": p}] for p in prompts], params, lora_request=lora,
                                           use_tqdm=False, chat_template_kwargs={"enable_thinking": False}))
        del llm
    if "qwen3.5-9b" in a.models.split(","):
        import gc
        gc.collect()
        llm = LLM(model=a.big9, dtype="bfloat16", language_model_only=True, max_model_len=CAP + 12288,
                  gpu_memory_utilization=0.90, max_num_seqs=128, seed=0)
        write(out, "qwen3.5-9b", items, llm.chat([[{"role": "user", "content": p}] for p in prompts], params,
                                                use_tqdm=False, chat_template_kwargs={"enable_thinking": False}))


def write(out: Path, model: str, items: list[dict], outs) -> None:
    recs = []
    for x, o in zip(items, outs, strict=True):
        c = o.outputs[0]
        pred = predict(c.text, str(c.finish_reason))
        recs.append({"uid": x["uid"], "subset": x["subset"], "label": x["label"], "pred": pred,
                     "finish_reason": str(c.finish_reason), "completion_tokens": len(c.token_ids), "text": c.text})
    hp.write_jsonl(out / f"pred-{model}.jsonl", recs)


def scores(recs: list[dict]) -> dict:
    err = [r for r in recs if r["label"] >= 0]
    cor = [r for r in recs if r["label"] < 0]
    acc_e = sum(r["pred"] == r["label"] for r in err) / len(err) if err else 0.0
    acc_c = sum(r["pred"] == -1 for r in cor) / len(cor) if cor else 0.0
    f1 = 2 * acc_e * acc_c / (acc_e + acc_c) if acc_e + acc_c else 0.0
    return {"n": len(recs), "acc_error": round(100 * acc_e, 1), "acc_correct": round(100 * acc_c, 1),
            "f1": round(100 * f1, 1), "verdict_on_error": round(100 * sum(r["pred"] is not None and r["pred"] >= 0 for r in err)
                                                                 / max(1, len(err)), 1),
            "no_verdict": round(100 * sum(r["pred"] is None for r in recs) / len(recs), 1),
            "capped": round(100 * sum(r["finish_reason"] == "length" for r in recs) / len(recs), 1)}


def report(a) -> None:
    out = Path(a.out)
    table = {}
    for m in MODELS:
        p = out / f"pred-{m}.jsonl"
        if not p.exists():
            continue
        recs = hp.read_jsonl([p])
        by = collections.defaultdict(list)
        for r in recs:
            by[r["subset"]].append(r)
        row = {sub: scores(by[sub]) for sub in ("synthetic",) + PB_SUBSETS}
        row["processbench_avg_f1"] = round(sum(row[s]["f1"] for s in PB_SUBSETS) / len(PB_SUBSETS), 1)
        table[m] = row
    (out / "summary.json").write_text(json.dumps(table, indent=1) + "\n")
    lines = ["# JUDGE on synthetic vs natural errors", "",
             "F1 = harmonic mean of exact-first-error accuracy on wrong solutions and accuracy on correct ones.", "",
             "| Model | Synthetic F1 | GSM8K F1 | MATH F1 | OlympiadBench F1 | Omni-MATH F1 | ProcessBench avg F1 |",
             "|---|---|---|---|---|---|---|"]
    for m, r in table.items():
        lines.append(f"| {m} | {r['synthetic']['f1']} | " + " | ".join(str(r[s]['f1']) for s in PB_SUBSETS)
                     + f" | **{r['processbench_avg_f1']}** |")
    lines += ["", "| Model | Subset | Exact first error (wrong solutions) | Says correct (correct solutions) | "
              "Says incorrect (wrong solutions) | No verdict | Capped |", "|---|---|---|---|---|---|---|"]
    for m, r in table.items():
        for s in ("synthetic",) + PB_SUBSETS:
            x = r[s]
            lines.append(f"| {m} | {s} | {x['acc_error']} | {x['acc_correct']} | {x['verdict_on_error']} | "
                         f"{x['no_verdict']} | {x['capped']} |")
    (out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["prepare", "run", "report"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--pb-dir", default="")
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--base", default="")
    ap.add_argument("--big9", default="")
    ap.add_argument("--adapters", default=str(Path.home() / "anlp-final-adapters"))
    a = ap.parse_args()
    {"prepare": prepare, "run": run, "report": report}[a.stage](a)


if __name__ == "__main__":
    main()
