#!/usr/bin/env python3
"""Direction 3 pilot: does a step-split solution format make JUDGE useful on the model's own attempts?

The mixed model solves the 200 SOLVE dev questions 4 times with an extra instruction to write numbered short steps
("S1: ..."). JUDGE (the JUDGE specialist and the mixed model, 4 votes each) checks every attempt in its native
format. Compared with the unstructured attempts of phase2/scripts/functional.py (drift run): accuracy, JUDGE's
AUROC on own attempts, and answer selection over the 4 attempts (majority vote vs JUDGE-weighted vote).

    python phase2/next/stepformat.py run --out DIR --base <2B path>     (1 GPU)
    python phase2/next/stepformat.py report --out DIR [--free-form <drift dir>]
"""

import argparse, collections, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "phase2" / "scripts"))
import hint_pilot as hp  # noqa: E402
import functional as F  # noqa: E402
from anlp_project import opd  # noqa: E402

ATTEMPTS, CAP, VOTES, JUDGE_CAP = 4, 16384, 4, 6144
STEP_FORMAT = ("\n\nFormat: write the solution as numbered steps, each on its own line and starting with \"S1:\", "
               "\"S2:\", and so on. Use at most 10 steps. Each step states one claim or computation and its "
               "justification in one to three sentences. After the last step, give the final-answer tag.")
STEP_RE = re.compile(r"(?m)^\s*\**S(\d+)\**\s*[:.]\s*\**\s*")


def solve_prompt(row):
    return hp.solve_prompt(row).replace("Return only the solution and the required final-answer tag.",
                                        "Return only the solution and the required final-answer tag." + STEP_FORMAT)


def split_steps(text):
    body = hp.FINAL_TAG.sub(lambda m: f"Final answer: {m.group(1)}", text.strip())
    marks = list(STEP_RE.finditer(body))
    if len(marks) >= 2:
        parts = [body[m.end(): (marks[i + 1].start() if i + 1 < len(marks) else len(body))].strip()
                 for i, m in enumerate(marks)]
        return [p for p in parts if p], True
    return hp.to_steps(text), False


def run(a):
    """One shard of the dev questions; each stage is saved before the next starts, and a rerun skips finished ones."""
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    gen_path, done = out / f"attempts-shard{a.shard}.jsonl", out / f"judged-shard{a.shard}.jsonl"
    if done.exists():
        return
    rows = opd.slice_rows("solve", "dev")[a.shard::a.nshards]
    eng = hp.Engine(a.base, Path(a.adapters), 32768)
    if gen_path.exists():
        atts = hp.read_jsonl([gen_path])
    else:
        outs = eng.chat([solve_prompt(r) for r in rows], "mixed", ATTEMPTS, CAP)
        atts = []
        for r, samples in zip(rows, outs, strict=True):
            for k, s in enumerate(samples):
                sc = hp.score(r, s)
                steps, parsed = split_steps(s["text"])
                atts.append({"uid": r["uid"], "attempt": k, "problem": r["question"], "key": r["final_answer"],
                             "text": s["text"], "finish_reason": s["finish_reason"], "tokens": s["completion_tokens"],
                             "steps": steps, "step_format": parsed, "answer": sc["extracted_answer"],
                             "correct": sc["correct_strict"]})
        hp.write_jsonl(gen_path, atts)
        print("generated", len(atts), flush=True)
    for name, adapter in (("spec", "judge"), ("mixed", "mixed")):
        jt = F.gen(eng, [F.judge_prompt(x["problem"], x["steps"]) for x in atts], adapter, VOTES, JUDGE_CAP)
        for x, texts in zip(atts, jt, strict=True):
            v = F.judge_vote(texts)
            x[f"{name}_judge"] = v
            x[f"{name}_p_incorrect"] = sum(d == "incorrect" for d, _ in v["votes"]) / VOTES
        print("judged", name, flush=True)
    hp.write_jsonl(done, atts)


def select(by, weight):
    acc = 0
    for xs in by.values():
        groups = []
        for x in xs:
            if not x["answer"]:
                continue
            g = next((g for g in groups if F.same_answer(g[0]["answer"], x["answer"])), None)
            g.append(x) if g else groups.append([x])
        if groups:
            best = max(groups, key=lambda g: sum(weight(x) for x in g))
            acc += best[0]["correct"]
    return 100 * acc / len(by)


def report(a):
    out = Path(a.out)
    atts = hp.read_jsonl(sorted(out.glob("judged-shard*.jsonl")))
    by = collections.defaultdict(list)
    for x in atts:
        by[x["uid"]].append(x)
    wrong = [x for x in atts if not x["correct"]]; right = [x for x in atts if x["correct"]]
    s = {"attempts": len(atts), "pass@1": round(100 * len(right) / len(atts), 2),
         "pass@4": round(100 * sum(any(x["correct"] for x in xs) for xs in by.values()) / len(by), 2),
         "step_format_parsed": round(100 * sum(x["step_format"] for x in atts) / len(atts), 1),
         "mean_tokens": round(sum(x["tokens"] for x in atts) / len(atts)),
         "majority_vote": round(select(by, lambda x: 1.0), 2)}
    for name in ("spec", "mixed"):
        s[name] = {"auroc_own_attempts": round(F.auroc([x[f"{name}_p_incorrect"] for x in wrong],
                                                       [x[f"{name}_p_incorrect"] for x in right]), 3),
                   "flags_wrong": round(100 * sum(x[f"{name}_judge"]["verdict"] == "incorrect" for x in wrong) / len(wrong), 1),
                   "flags_correct": round(100 * sum(x[f"{name}_judge"]["verdict"] == "incorrect" for x in right) / len(right), 1),
                   "vote_weighted_by_p_correct": round(select(by, lambda x: 1 - x[f"{name}_p_incorrect"] + 1e-3), 2),
                   "vote_drop_judged_incorrect": round(select(by, lambda x: 0.0 if x[f"{name}_judge"]["verdict"] == "incorrect" else 1.0), 2)}
    (out / "summary.json").write_text(json.dumps(s, indent=1) + "\n")
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run", "report"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default="")
    ap.add_argument("--adapters", default=str(Path.home() / "anlp-final-adapters"))
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    a = ap.parse_args()
    {"run": run, "report": report}[a.stage](a)
