#!/usr/bin/env python3
"""Score saved Qwen3-4B JUDGE/RECONSTRUCT responses with Jev and compare with DeepSeek.

Jev (TypeSafe System One) returns typed judgments, not text, so each rubric dimension
is one Score question with descriptive levels; code applies the rubric's gating,
shortcut override and 6.25 * sum aggregation, exactly as the DeepSeek pipelines do.

    python3 scripts/compare_jev_judges.py run --task judge --limit 1   # smoke test
    python3 scripts/compare_jev_judges.py run --task all
    python3 scripts/compare_jev_judges.py report

Requires JEV_KEY in .env. Raw requests and responses are saved, and finished items are
never re-requested.
"""

from __future__ import annotations

import argparse
import json
import math
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "jev-agreement-v1"
JUDGE_SRC = ROOT / "artifacts/qwen3-4b/judge/high-confidence-78/results.jsonl"
RECON_SRC = ROOT / "artifacts/reconstruct/valid-100-recovery-v1/questions-answers.jsonl"
API = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"  # pinned; jev-latest is an alias that can move
PRICE_PER_TOKEN = 0.042 / 1_000_000
V4_CUTOFFS = (18.75, 43.75, 56.25, 75.0)


def api_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("JEV_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit("JEV_KEY missing from .env")


def rating_v4(score: float) -> int:
    return 1 + sum(score >= c for c in V4_CUTOFFS)


def score_q(instructions, levels):
    return {"type": "score", "instructions": instructions, "criteria": levels}


def noul_q(instructions, true, false):
    return {"type": "noul", "instructions": instructions, "criteria": {"true": true, "false": false}}


def choice_q(instructions, options):
    return {"type": "choice", "instructions": instructions, "criteria": options}


# ---------------------------------------------------------------- JUDGE questions
# Levels paraphrase data/prompts/judge/judge_eval_p1.md as concrete situations.

def judge_questions(item) -> dict:
    steps = [s["step_id"] for s in item["proposed_solution"]]
    q = {
        "decision": choice_q(
            "In `student_response`, what final decision does the student state about whether "
            "the proposed solution is correct? If the student states one decision but then argues "
            "the opposite, choose `contradictory`.",
            {"correct": "The student says the proposed solution is correct.",
             "incorrect": "The student says the proposed solution is incorrect.",
             "contradictory": "The student's stated decision and its argument disagree.",
             "missing": "The student gives no decision."}),
        "named_step": choice_q(
            "Which step of the proposed solution does `student_response` name as the FIRST wrong step?",
            {**{s: f"The student names step {s} as the first wrong step." for s in steps},
             "none": "The student says no step is wrong.",
             "missing": "The student names no step."}),
        "M": score_q(
            "Are the mathematical claims that the student makes in `student_response` true? Judge only "
            "the student's own assertions, regardless of whether its final decision matches the key.",
            ["The student's explanation is essentially false or circular, or makes no substantive mathematical claim.",
             "Most of the student's mathematical reasoning is false.",
             "The student makes at least one false mathematical claim alongside some correct reasoning.",
             "The student's claims are true except for a minor inaccuracy that does not affect the judgment.",
             "Every mathematical claim the student makes is true."]),
    }
    if item["key_label"] == "incorrect":
        q["L"] = score_q(
            "The answer key says the first wrong step is `answer_key.first_wrong_step`. Which step does "
            "`student_response` identify as the first wrong step, relative to the key?",
            ["The student names a different step than the key's (an earlier sound step, an unrelated step), or says no step is wrong, or names none.",
             "The student names a later step whose flaw is a direct consequence of the same error as the key's first wrong step.",
             "The student names exactly the key's first wrong step."])
        q["E"] = score_q(
            "How well does `student_response` explain the mathematical error described in "
            "`answer_key.explanation`? A different but mathematically valid account of the SAME error counts.",
            ["The student explains a different error, gives no explanation, or gives an explanation unrelated to the key's error.",
             "The student points at the right step but for a wrong or irrelevant reason.",
             "The student's explanation is partly related to the key's error but misses its essence.",
             "The student explains the same error as the key, with a minor imprecision or omission.",
             "The student explains precisely the same mathematical error as the key."])
    else:
        q["L"] = score_q(
            "The answer key says the proposed solution is correct, so no step is wrong. Does "
            "`student_response` say that no step is wrong?",
            ["The student flags at least one step as wrong.",
             "The student says no step is wrong."])
        q["E"] = score_q(
            "The answer key says the proposed solution is correct. How well does `student_response` "
            "justify that the solution holds?",
            ["The student gives no justification or an invalid reason.",
             "The student gives only a vague justification such as 'all steps are fine', which is not wrong but not concrete.",
             "The student gives a concrete, valid reason the solution holds, such as checking the decisive step or the answer."])
    return q


def judge_state(item) -> dict:
    return {
        "problem": item["problem"],
        "proposed_solution": [{"step": s["step_id"], "text": s["text"]} for s in item["proposed_solution"]],
        "answer_key": {"label": item["key_label"], "first_wrong_step": item["key_first_wrong_step"],
                       "explanation": item["key_explanation"]},
        "student_response": item["qwen_response"],
    }


def judge_dims(item, ans) -> dict:
    """Map Jev answers to V/L/E/M on the DeepSeek rubric's 0-4 scale, with its gating."""
    decision = ans["decision"]["choice"]
    V = 4 if decision == item["key_label"] else 0
    Lraw, Eraw = ans["L"], ans["E"]
    if item["key_label"] == "incorrect":
        L_arg = {0: 0, 1: 2, 2: 4}[argmax(Lraw)]
        L_w = 2 * Lraw["score"]
        E_arg, E_w = argmax(Eraw), Eraw["score"]
    else:
        L_arg, L_w = 4 * argmax(Lraw), 4 * Lraw["score"]
        E_arg, E_w = {0: 0, 1: 2, 2: 4}[argmax(Eraw)], 2 * Eraw["score"]
    if V == 0:
        L_arg = L_w = E_arg = E_w = 0
    M_arg, M_w = argmax(ans["M"]), ans["M"]["score"]
    dims = {"V": V, "L": L_arg, "E": E_arg, "M": M_arg}
    weighted = {"V": V, "L": L_w, "E": E_w, "M": M_w}
    return {"decision": decision, "named_step": ans["named_step"]["choice"], "dims": dims,
            "dims_weighted": weighted, "score_100": 6.25 * sum(dims.values()),
            "score_100_weighted": 6.25 * sum(weighted.values())}


# ---------------------------------------------------------- RECONSTRUCT questions
# Levels paraphrase data/prompts/reconstruct/partial_credit_v4/judge_{fidelity,validity}.md.

FIDELITY_Q = {
    "P": score_q(
        "Compare the premises of `candidate_question` with those of `original_question`: objects, "
        "given conditions, parameters, domains and quantifiers. Cosmetic renaming and "
        "reparameterizations with a valid correspondence count as equivalent. The candidate must state "
        "its own premises; do not assume conditions it leaves out.",
        ["The candidate's setup has no meaningful correspondence with the original's.",
         "The candidate shares objects or topic with the original, but its essential setup is largely different.",
         "The candidate keeps important structure of the original, but at least one essential premise or parameter is missing or changed.",
         "The candidate keeps most of the original setup, with one localized material error or omission.",
         "The candidate's objects, premises, parameters, domains and quantifiers are equivalent to the original's."]),
    "T": score_q(
        "Compare what `candidate_question` asks to find with what `original_question` asks to find. "
        "Judge only the requested quantity, event or direction; missing input parameters are judged "
        "elsewhere. Asking for a different unknown is not equivalent even if an inverse calculation links them.",
        ["The candidate asks for nothing identifiable, or for something unrelated to the original's target.",
         "The candidate asks about related objects but a fundamentally different result.",
         "The candidate asks for a quantity of the same family as the original but a different quantity, event or direction.",
         "The candidate asks for the same quantity as the original with a limited material error in scope or qualification.",
         "The candidate asks for a mathematically equivalent target to the original's."]),
    "equivalent": noul_q(
        "Do `candidate_question` and `original_question` pose the same mathematical problem, up to "
        "renaming and equivalent reformulation, with the same essential premises AND the same requested target?",
        "Same essential premises and same requested target.",
        "Some essential premise or the requested target differs."),
}

VALIDITY_E = score_q(
    "Consider each numbered item in `observations`. How well does the student's reconstructed question "
    "(`response.question`) and explanation fit and use ALL of the observations? Mentioning an observation "
    "is not the same as grounding it.",
    ["The response ignores the observations or predominantly contradicts them.",
     "The response mentions observations without any usable connection to its question.",
     "The response substantively uses some observations but leaves important gaps or conflicts.",
     "Every observation is connected to the reconstruction, with one limited unsupported link.",
     "Every observation substantively fits one coherent reconstruction, and the links are explained."])

VALIDITY_M = score_q(
    "Is `response.question`, read on its own, a well-posed mathematical question whose answer is exactly "
    "`final_answer`, and does `response.justification` soundly verify that? Premises that appear only in "
    "the assumptions or justification do not count as part of the question. A correct final value does not "
    "excuse a false claim. A justification that only restates the supplied answer is not verification.",
    ["There is no meaningful verification, or the justification only restates the answer or is circular.",
     "The attempt is substantive but the answer is wrong for the question, the question is ill-posed or underdetermined, or an essential mathematical claim is false.",
     "The reasoning is plausible but an essential step of the proof or calculation is missing, so correctness is not established.",
     "The question is well posed, its answer is the supplied answer, and the argument is sound except for a minor omitted step.",
     "The question is well posed, its answer is the supplied answer, and the verification is complete and sound."])

SHORTCUT_Q = noul_q(
    "Is `response.question` a shortcut? A shortcut is exactly one of: (a) the question explicitly states "
    "the value of the same quantity it asks to find; (b) it merely asks to repeat the supplied final answer; "
    "(c) there is no identifiable mathematical request at all. Asking for a different unknown, missing "
    "parameters, wrong targets or arithmetic mistakes are NOT shortcuts.",
    "The question is one of the three shortcut types.",
    "The question is a substantive mathematical request, even if flawed.")


def recon_response(item) -> dict:
    q = item.get("qwen") or {}
    return {"assumptions": q.get("assumptions"), "question": q.get("question"),
            "justification": q.get("justification")}


def recon_requests(item) -> dict:
    resp = recon_response(item)
    public = {"final_answer": item["source_final_answer"],
              "observations": [f"{i}. {c}" for i, c in enumerate(item["clues"], 1)],
              "response": resp}
    return {
        "fidelity": ({"original_question": item["source_question"], "candidate_question": resp["question"]},
                     FIDELITY_Q),
        "validity": (public, {"E": VALIDITY_E, "M": VALIDITY_M, "shortcut": SHORTCUT_Q}),
        # Variant B (not in the DeepSeek design): validity judge also sees the source.
        "validity_ref": ({**public, "reference": {"original_question": item["source_question"],
                                                  "reference_solution": item["source_reference_solution"],
                                                  "note": "The student did not see this. A different question that is valid for the observations and answer can still deserve full credit."}},
                         {"E": VALIDITY_E, "M": VALIDITY_M, "shortcut": SHORTCUT_Q}),
    }


def recon_dims(ans: dict, validity_key: str) -> dict:
    f, v = ans["fidelity"], ans[validity_key]
    dims = {"P": argmax(f["P"]), "T": argmax(f["T"]), "E": argmax(v["E"]), "M": argmax(v["M"])}
    weighted = {"P": f["P"]["score"], "T": f["T"]["score"], "E": v["E"]["score"], "M": v["M"]["score"]}
    shortcut = v["shortcut"]["noul"] > 0.5
    raw = 6.25 * sum(dims.values())
    return {"dims": dims, "dims_weighted": weighted, "shortcut": shortcut,
            "shortcut_p": v["shortcut"]["noul"], "equivalent_p": f["equivalent"]["noul"],
            "score_100": 0.0 if shortcut else raw,
            "score_100_weighted": 0.0 if shortcut else 6.25 * sum(weighted.values())}


# -------------------------------------------------------------------- transport

def argmax(score_answer) -> int:
    p = score_answer["probabilities"]
    return int(max(p, key=lambda k: p[k]))


class Jev:
    def __init__(self):
        self.key = api_key()
        self.lock = threading.Lock()
        self.tokens = 0

    def call(self, state, questions) -> dict:
        body = json.dumps({"model": MODEL, "state": state, "questions": questions}).encode()
        for attempt in range(6):
            req = urllib.request.Request(API, data=body, method="POST", headers={
                "Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    out = json.loads(r.read())
                with self.lock:
                    self.tokens += out.get("usage", {}).get("input_tokens", 0)
                return out
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:500]
                if e.code in (429, 500, 502, 503, 520, 529) and attempt < 5:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"HTTP {e.code}: {detail}") from None
            except (urllib.error.URLError, TimeoutError):
                if attempt < 5:
                    time.sleep(2 ** attempt)
                    continue
                raise


def load_done(path: Path) -> dict:
    if not path.exists():
        return {}
    return {r["id"]: r for r in map(json.loads, path.read_text().splitlines()) if r.get("ok")}


def cmd_run(args):
    OUT.mkdir(parents=True, exist_ok=True)
    jev = Jev()
    tasks = ["judge", "reconstruct"] if args.task == "all" else [args.task]
    for task in tasks:
        path = OUT / f"{task}-jev.jsonl"
        done = load_done(path)
        if task == "judge":
            items = [json.loads(l) for l in JUDGE_SRC.open()]
            items = [(x["judge_id"], x) for x in items]
        else:
            items = [json.loads(l) for l in RECON_SRC.open()]
            items = [(f"recon-{x['source_index']}", x) for x in items]
        todo = [(i, x) for i, x in items if i not in done][: args.limit or None]
        lock = threading.Lock()

        def work(pair):
            iid, x = pair
            rec = {"id": iid, "task": task, "model": MODEL}
            try:
                if task == "judge":
                    state, qs = judge_state(x), judge_questions(x)
                    out = jev.call(state, qs)
                    rec.update(ok=True, request={"state": state, "questions": qs}, response=out)
                else:
                    rec["request"], rec["response"] = {}, {}
                    for name, (state, qs) in recon_requests(x).items():
                        rec["request"][name] = {"state": state, "questions": qs}
                        rec["response"][name] = jev.call(state, qs)
                    rec["ok"] = True
            except Exception as e:  # keep the failure, never guess a score
                rec.update(ok=False, error=str(e))
            with lock, path.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return rec["ok"]

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(work, todo))
        print(f"{task}: {sum(results)}/{len(todo)} ok, {len(done)} previously done")
    print(f"input tokens this run: {jev.tokens:,}  cost ≈ ${jev.tokens * PRICE_PER_TOKEN:.4f}")


# ----------------------------------------------------------------------- report

def qwk(a, b, k=5):
    """Quadratic weighted kappa on integer levels 0..k-1."""
    n = len(a)
    if n == 0:
        return float("nan")
    O = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        O[x][y] += 1
    ha = [sum(r) for r in O]
    hb = [sum(O[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = (i - j) ** 2 / (k - 1) ** 2
            num += w * O[i][j]
            den += w * ha[i] * hb[j] / n
    return 1 - num / den if den else float("nan")


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for t in range(i, j + 1):
            r[order[t]] = (i + j) / 2
        i = j + 1
    return r


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else float("nan")


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def agreement(name, ds, jv, jv_w, k=5):
    n = len(ds)
    exact = sum(a == b for a, b in zip(ds, jv)) / n
    within1 = sum(abs(a - b) <= 1 for a, b in zip(ds, jv)) / n
    mode = max(set(ds), key=ds.count)
    base = ds.count(mode) / n
    return {"dimension": name, "n": n, "exact": exact, "within_1": within1,
            "mode_baseline_exact": base, "qwk": qwk(ds, jv, k), "spearman_weighted": spearman(ds, jv_w),
            "mae": sum(abs(a - b) for a, b in zip(ds, jv)) / n,
            "deepseek_mean": sum(ds) / n, "jev_mean": sum(jv) / n}


def cmd_report(_args):
    summary, lines = {}, ["# Jev vs DeepSeek agreement on saved Qwen3-4B responses", ""]
    lines += [f"Jev model `{MODEL}`. DeepSeek V4.1 Flash scores are the existing saved ratings, not ground truth.",
              "Exact/within-1 use Jev's most probable level; Spearman uses Jev's probability-weighted score.", ""]

    # JUDGE
    items = {x["judge_id"]: x for x in map(json.loads, JUDGE_SRC.open())}
    rows = []
    for r in load_done(OUT / "judge-jev.jsonl").values():
        x = items[r["id"]]
        rows.append((x, judge_dims(x, r["response"]["answers"])))
    if rows:
        s = {"n": len(rows)}
        dims = []
        for d in "VLEM":
            ds = [x["dimensions"][d] for x, _ in rows]
            jv = [j["dims"][d] for _, j in rows]
            jw = [j["dims_weighted"][d] for _, j in rows]
            dims.append(agreement(d, ds, jv, jw))
        s["dimensions"] = dims
        ds_tot = [x["score_100"] for x, _ in rows]
        jv_tot = [j["score_100"] for _, j in rows]
        jw_tot = [j["score_100_weighted"] for _, j in rows]
        s["total"] = {"pearson": pearson(ds_tot, jv_tot), "spearman_weighted": spearman(ds_tot, jw_tot),
                      "mae": sum(abs(a - b) for a, b in zip(ds_tot, jv_tot)) / len(rows),
                      "deepseek_mean": sum(ds_tot) / len(rows), "jev_mean": sum(jv_tot) / len(rows)}
        s["rating_exact"] = sum(rating_v4(a) == rating_v4(b) for a, b in zip(ds_tot, jv_tot)) / len(rows)
        s["decision_vs_parser"] = sum(j["decision"] == x["qwen_decision"] for x, j in rows) / len(rows)
        s["step_vs_parser"] = sum(j["named_step"] == (x["qwen_first_wrong_step"] or "missing") for x, j in rows) / len(rows)
        s["verdict_accuracy"] = {"parser": sum(x["parsed_verdict_correct"] for x, _ in rows) / len(rows),
                                 "deepseek_V4": sum(x["dimensions"]["V"] == 4 for x, _ in rows) / len(rows),
                                 "jev_V4": sum(j["dims"]["V"] == 4 for _, j in rows) / len(rows)}
        summary["judge"] = s
        lines += table(f"JUDGE ({len(rows)} items)", s)
        lines += [f"- Jev's read of the student's decision matches the regex parser on "
                  f"{s['decision_vs_parser']:.1%}; named step matches on {s['step_vs_parser']:.1%}.",
                  f"- Verdict accuracy: parser {s['verdict_accuracy']['parser']:.1%}, "
                  f"DeepSeek {s['verdict_accuracy']['deepseek_V4']:.1%}, Jev {s['verdict_accuracy']['jev_V4']:.1%}.", ""]

    # RECONSTRUCT
    items = {f"recon-{x['source_index']}": x for x in map(json.loads, RECON_SRC.open())}
    done = load_done(OUT / "reconstruct-jev.jsonl")
    keymap = {"P": "premise_fidelity", "T": "target_fidelity", "E": "evidence_integration", "M": "mathematical_validity"}
    for variant, vkey in (("A: source-blind validity (same as DeepSeek)", "validity"),
                          ("B: validity judge also sees the source", "validity_ref")):
        rows = [(items[r["id"]], recon_dims({k: v["answers"] for k, v in r["response"].items()}, vkey))
                for r in done.values()]
        if not rows:
            continue
        s = {"n": len(rows), "dimensions": []}
        for d in "PTEM":
            if vkey == "validity_ref" and d in "PT":
                continue
            ds = [x["score"]["dimensions"][keymap[d]] for x, _ in rows]
            s["dimensions"].append(agreement(d, ds, [j["dims"][d] for _, j in rows],
                                             [j["dims_weighted"][d] for _, j in rows]))
        ds_tot = [x["score"]["score_100"] for x, _ in rows]
        jv_tot = [j["score_100"] for _, j in rows]
        jw_tot = [j["score_100_weighted"] for _, j in rows]
        s["total"] = {"pearson": pearson(ds_tot, jv_tot), "spearman_weighted": spearman(ds_tot, jw_tot),
                      "mae": sum(abs(a - b) for a, b in zip(ds_tot, jv_tot)) / len(rows),
                      "deepseek_mean": sum(ds_tot) / len(rows), "jev_mean": sum(jv_tot) / len(rows)}
        s["rating_exact"] = sum(rating_v4(a) == rating_v4(b) for a, b in zip(ds_tot, jv_tot)) / len(rows)
        sc = [(bool(x["score"]["shortcut"]), j["shortcut"]) for x, j in rows]
        s["shortcut"] = {"deepseek_true": sum(a for a, _ in sc), "jev_true": sum(b for _, b in sc),
                         "both_true": sum(a and b for a, b in sc), "agree": sum(a == b for a, b in sc) / len(sc)}
        eq = [(bool(x.get("semantic_equivalent")), j["equivalent_p"] > 0.5,
               j["dims"]["P"] == 4 and j["dims"]["T"] == 4) for x, j in rows]
        s["equivalence"] = {"deepseek_true": sum(a for a, _, _ in eq), "jev_true": sum(b for _, b, _ in eq),
                            "both_true": sum(a and b for a, b, _ in eq),
                            "jev_p4t4_true": sum(c for _, _, c in eq), "both_p4t4": sum(a and c for a, _, c in eq)}
        summary["reconstruct_" + vkey] = s
        lines += table(f"RECONSTRUCT {variant} ({len(rows)} items)", s)
        lines += [f"- Shortcut flags: DeepSeek {s['shortcut']['deepseek_true']}, Jev {s['shortcut']['jev_true']}, "
                  f"both {s['shortcut']['both_true']}; agreement {s['shortcut']['agree']:.1%}.",
                  f"- Semantic equivalence: DeepSeek {s['equivalence']['deepseek_true']}; Jev yes/no question "
                  f"{s['equivalence']['jev_true']} (both {s['equivalence']['both_true']}); Jev P4 and T4 "
                  f"{s['equivalence']['jev_p4t4_true']} (both {s['equivalence']['both_p4t4']}).", ""]

    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    (OUT / "report.md").write_text("\n".join(lines))
    print("\n".join(lines))


def table(title, s):
    out = [f"## {title}", "", "| Dim | Exact | Mode baseline | Within 1 | Weighted κ | Spearman | MAE | DeepSeek mean | Jev mean |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for d in s["dimensions"]:
        out.append(f"| {d['dimension']} | {d['exact']:.0%} | {d['mode_baseline_exact']:.0%} | {d['within_1']:.0%} | "
                   f"{d['qwk']:.2f} | {d['spearman_weighted']:.2f} | {d['mae']:.2f} | {d['deepseek_mean']:.2f} | {d['jev_mean']:.2f} |")
    t = s["total"]
    out += ["", f"- Total 0–100: Pearson {t['pearson']:.2f}, Spearman (weighted) {t['spearman_weighted']:.2f}, "
            f"MAE {t['mae']:.1f}; means DeepSeek {t['deepseek_mean']:.1f} vs Jev {t['jev_mean']:.1f}. "
            f"1–5 rating (v4) exact agreement {s['rating_exact']:.0%}."]
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--task", choices=["judge", "reconstruct", "all"], default="all")
    r.add_argument("--limit", type=int, default=0)
    r.add_argument("--workers", type=int, default=8)
    sub.add_parser("report")
    args = p.parse_args()
    {"run": cmd_run, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
