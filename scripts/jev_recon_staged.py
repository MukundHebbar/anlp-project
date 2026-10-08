#!/usr/bin/env python3
"""RECONSTRUCT with Jev in stages: a dedicated few-shot shortcut check first, then P/T/E/M, then the score.

    python3 scripts/jev_recon_staged.py run --limit 3     # smoke test
    python3 scripts/jev_recon_staged.py run
    python3 scripts/jev_recon_staged.py report

Stage 1 (new): one request whose state is only `final_answer` and the reconstructed `question`. It asks a
Choice over DeepSeek's three shortcut types (plus none) and one yes/no "is this a shortcut", both carrying the
PC-v4 shortcut definitions and synthetic labelled examples in structured instructions. Stage 2: only when
stage 1 finds no shortcut, the P/T (fidelity) and E/M (validity) requests. They are identical to v1, so this
check reuses the saved v1 answers. Final score: 0 for a shortcut, else 6.25 * (P + T + E + M).

The examples are written for this script (rectangle cases from the PC-v4 rubric plus made-up cases of the
patterns v1 missed); none is taken from the test set. Checked on artifacts/jev-recon-v2/sample.json (506
answers) against the saved DeepSeek scores.
"""

from __future__ import annotations

import argparse
import json
import statistics as st
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import compare_jev_judges as cj  # noqa: E402
import jev_recon_v2 as v2  # noqa: E402

OUT = ROOT / "artifacts" / "jev-recon-v2"

DEFINITIONS = {
    "answer-copy tautology": "`question` explicitly states the value of the SAME quantity it asks to find. This "
                             "includes a line such as 'Answer: X' inside the question. Merely containing the number "
                             "somewhere is not enough, and using it as an input for a DIFFERENT unknown is not a shortcut.",
    "copy-only restatement": "`question` is a direct request to repeat `final_answer`, with nothing to work out.",
    "no usable question": "`question` contains no identifiable mathematical request at all, for example it is only "
                          "the writer's musing, drafts or self-corrections that never settle on a request.",
    "not a shortcut": "Everything else, including questions that are wrong, underdetermined, ask for a different "
                      "unknown, or are surrounded by some commentary but still contain a clear mathematical request.",
}

EXAMPLES = [
    {"final_answer": "6", "question": "A rectangle has longer side 6. What is its longer side?",
     "label": "answer-copy tautology", "why": "It gives the longer side as 6 and asks for the longer side."},
    {"final_answer": "13", "question": "Find the remainder when 2^100 is divided by 17.\nAnswer: 13.",
     "label": "answer-copy tautology", "why": "The question field itself states the answer to its own request."},
    {"final_answer": "24", "question": "Let N = 24 be the number of arrangements. How many arrangements are there?",
     "label": "answer-copy tautology", "why": "It states the requested count as a premise."},
    {"final_answer": "x^2 + 1", "question": "What is x^2 + 1?",
     "label": "copy-only restatement", "why": "It only asks to repeat the supplied expression."},
    {"final_answer": "2", "question": "Maybe it is an integral? No. Perhaps a sum of roots... the observations "
     "mention 0.8, so maybe a probability. Hard to say; the answer is probably 2.",
     "label": "no usable question", "why": "It never settles on a mathematical request."},
    {"final_answer": "6", "question": "A rectangle has perimeter 20 and longer side 6. Find its area.",
     "label": "not a shortcut", "why": "6 is an input for a different unknown (the area, 24)."},
    {"final_answer": "6", "question": "A rectangle has perimeter 20. Find its longer side.",
     "label": "not a shortcut", "why": "Underdetermined, but it does not state the requested value."},
    {"final_answer": "43", "question": "Find the last two digits of 7^343.",
     "label": "not a shortcut", "why": "A substantive request; containing no answer, it must be worked out."},
    {"final_answer": "5", "question": "I think the clues point to modular arithmetic, so let me pose it this way. "
     "Find the smallest positive integer n such that 3^n leaves remainder 5 when divided by 7.",
     "label": "not a shortcut", "why": "Some commentary, but a clear request that does not state its answer."},
    {"final_answer": "Yes", "question": "Is every group of prime order cyclic?",
     "label": "not a shortcut", "why": "A yes/no request that must be decided; it does not state the answer."},
]

GUIDE = {"definitions": DEFINITIONS, "labelled_examples": EXAMPLES}

SHORTCUT_QUESTIONS = {
    "shortcut_type": cj.choice_q(
        {**GUIDE, "question": "Which label from `definitions` applies to `question`, given `final_answer`? "
                              "Judge only the question field. Follow the labelled examples."},
        {"not a shortcut": DEFINITIONS["not a shortcut"],
         "answer-copy tautology": DEFINITIONS["answer-copy tautology"],
         "copy-only restatement": DEFINITIONS["copy-only restatement"],
         "no usable question": DEFINITIONS["no usable question"]}),
    "is_shortcut": cj.noul_q(
        {**GUIDE, "question": "Is `question` a shortcut, that is, an answer-copy tautology, a copy-only restatement "
                              "or no usable question, as defined in `definitions`? Follow the labelled examples."},
        "One of the three shortcut types applies.",
        "Not a shortcut: the question contains a real mathematical request that does not state its own answer."),
    # The two precise checks from jev_recon_v2 (19 catches, 1 false flag there), worded for this state.
    "states_value": cj.noul_q(
        "Does `question` itself already state the value of the quantity it asks to find, for example a line such as "
        "'Answer: ...' or a premise that gives the requested value directly?",
        "The question states the value of the very quantity it asks for.",
        "The question does not state the value it asks for."),
    "repeats_answer": cj.noul_q(
        "Does `question` merely ask to repeat or restate `final_answer`, for example 'What is X?' where X is written "
        "exactly as `final_answer`, with nothing to compute?",
        "The question only asks to repeat the supplied answer.",
        "The question asks for something that has to be worked out."),
}


def stage1_state(old_rec: dict) -> dict:
    val = old_rec["request"]["validity"]["state"]
    return {"final_answer": val["final_answer"], "question": val["response"].get("question") or ""}


def cmd_run(a):
    path = OUT / "staged-shortcut-final.jsonl"
    done = {(r["arm"], r["id"]) for r in map(json.loads, path.open()) if r.get("ok")} if path.exists() else set()
    old = v2.v1_records()
    todo = [k for k in v2.sample_items() if k in old and k not in done][: a.limit or None]
    jev, lock = cj.Jev(), threading.Lock()

    def work(key):
        rec = {"arm": key[0], "id": key[1], "model": cj.MODEL}
        try:
            rec.update(ok=True, response=jev.call(stage1_state(old[key]), SHORTCUT_QUESTIONS))
        except Exception as e:
            rec.update(ok=False, error=str(e)[:500])
        with lock, path.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec["ok"]

    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        ok = list(pool.map(work, todo))
    print(f"{sum(ok)}/{len(todo)} ok, {len(done)} previously done; input tokens {jev.tokens:,}, "
          f"cost ≈ ${jev.tokens * cj.PRICE_PER_TOKEN:.4f}")


def final_score(stage1: dict | None, v1_answers: dict, rule: str) -> tuple[bool, float, float]:
    """(shortcut, score_100, probability-weighted score_100) for one answer."""
    if rule == "v1":
        sc = v1_answers["validity"]["shortcut"]["noul"] > 0.5
    elif rule == "choice":
        sc = stage1["shortcut_type"]["probabilities"]["not a shortcut"] < 0.5
    elif rule == "noul":
        sc = stage1["is_shortcut"]["noul"] > 0.5
    elif rule == "final":  # the few-shot Choice or either precise check
        sc = (stage1["shortcut_type"]["probabilities"]["not a shortcut"] < 0.5 or stage1["states_value"]["noul"] > 0.5
              or stage1["repeats_answer"]["noul"] > 0.5)
    else:  # both stage-1 questions agree that it is a shortcut
        sc = (stage1["shortcut_type"]["probabilities"]["not a shortcut"] < 0.5) and stage1["is_shortcut"]["noul"] > 0.5
    f, v = v1_answers["fidelity"], v1_answers["validity"]
    arg = sum(cj.argmax(x) for x in (f["P"], f["T"], v["E"], v["M"]))
    w = sum(x["score"] for x in (f["P"], f["T"], v["E"], v["M"]))
    return sc, 0.0 if sc else 6.25 * arg, 0.0 if sc else 6.25 * w


def cmd_report(_a):
    old = v2.v1_records()
    s1 = {(r["arm"], r["id"]): r["response"]["answers"] for r in map(json.loads, (OUT / "staged-shortcut-final.jsonl").open()) if r.get("ok")}
    ds = {}
    for arm in {a for a, _ in v2.sample_items()}:
        for x in map(json.loads, (v2.v1.TEST / f"matrix-{arm}" / "judged-scores.jsonl").open()):
            ds[(arm, x["uid"])] = x
    keys = [k for k in v2.sample_items() if k in s1 and k in old]
    dt = [ds[k]["score_100"] for k in keys]
    dsc = [bool(ds[k]["shortcut"]) for k in keys]
    L = ["# RECONSTRUCT with Jev in stages: few-shot shortcut check, then P/T/E/M", "",
         f"{len(keys)} answers to {len({k[1] for k in keys})} test questions (artifacts/jev-recon-v2/sample.json). "
         f"DeepSeek flags {sum(dsc)} shortcuts. P/T/E/M are the v1 answers in every row; only the shortcut "
         "decision differs.", "",
         "| Shortcut decision | Caught | False flags | Pearson | Rating exact | MAE | Pairs same / opposite | Close pairs same / opposite |",
         "|---|---:|---:|---:|---:|---:|---|---|"]
    for rule, name in (("v1", "v1 (one question inside the validity request)"), ("choice", "stage 1 Choice (type)"),
                       ("noul", "stage 1 yes/no"), ("both", "stage 1, Choice and yes/no agree"),
                       ("final", "**final: stage 1 Choice or a precise check**")):
        rows = [final_score(s1[k], {n: v["answers"] for n, v in old[k]["response"].items()}, rule) for k in keys]
        sc = [r[0] for r in rows]
        jt = [r[1] for r in rows]
        pw, pwc, npairs, nclose = v2.pairwise(list(zip([k[1] for k in keys], dt, [r[2] for r in rows])))
        L.append(f"| {name} | {sum(a and b for a, b in zip(dsc, sc))} / {sum(dsc)} | {sum(b and not a for a, b in zip(dsc, sc))} | "
                 f"{cj.pearson(dt, jt):.2f} | {st.mean(cj.rating_v4(a) == cj.rating_v4(b) for a, b in zip(dt, jt)):.0%} | "
                 f"{st.mean(abs(a - b) for a, b in zip(dt, jt)):.1f} | {pw.rsplit(' / ', 1)[0]} | {pwc.rsplit(' / ', 1)[0]} |")
    types = {}
    for k, a in zip(keys, dsc):
        p = s1[k]["shortcut_type"]["probabilities"]
        t = max(p, key=p.get)
        types.setdefault(t, [0, 0])[0 if a else 1] += 1
    L += ["", "Stage 1 Choice, most probable label (DeepSeek shortcut / not):"]
    L += [f"- {t}: {v[0]} / {v[1]}" for t, v in sorted(types.items())]
    L += ["", f"Pairs: answers to the same question that DeepSeek scored differently ({npairs}; close = within 12.5 "
          f"points, {nclose}), ordered by the probability-weighted score."]
    (OUT / "staged-report.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--limit", type=int, default=0)
    r.add_argument("--workers", type=int, default=16)
    sub.add_parser("report")
    a = ap.parse_args()
    {"run": cmd_run, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()
