#!/usr/bin/env python3
"""Fixes for the Jev judge, each checked on a fixed 500-answer sample against the saved DeepSeek scores.

    python3 scripts/jev_judge_fixes.py run --task judge         # 500 JUDGE answers (judge-sample.json)
    python3 scripts/jev_judge_fixes.py run --task reconstruct   # 506 RECONSTRUCT answers (sample.json)
    python3 scripts/jev_judge_fixes.py report

Answers that fail a strict gate (src/anlp_project/strict_gates.py) score 0 and are never sent to Jev.
JUDGE: V and L come from the parser (exact once hedged answers are gated); E stays the v1 Jev question; M is
re-asked with the rubric's level text, the teacher's reference solution in the state (DeepSeek sees it; v1
left it out), and three yes/no checks combined in code: no substantive claim -> 0, a false claim -> at most 2.
RECONSTRUCT: P and T stay v1; E and M are re-asked with the PC-v4 level text and anchors; shortcuts come from
the gate plus the few-shot stage-1 check (jev_recon_staged.py).
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
import jev_vs_deepseek as v1  # noqa: E402
from anlp_project.baseline import rows_for  # noqa: E402
from anlp_project.strict_gates import judge_gate, reconstruct_gate  # noqa: E402

OUT = ROOT / "artifacts" / "jev-recon-v2"
score, noul = cj.score_q, cj.noul_q

# ------------------------------------------------------------------------- JUDGE M

JUDGE_M = {
    "M": score(
        "Score M (mathematical soundness) of `student_response`: are the student's OWN mathematical claims true? "
        "Check each claim against `answer_key.explanation` and `answer_key.reference_response`, which are correct. "
        "Score what the student asserts, independently of whether its decision is right. A correct decision does "
        "not excuse a false explanation. Saying only 'step S3 is wrong' with no mathematical content is not a "
        "substantive claim.",
        ["Essentially false, circular, or no substantive mathematical claim.",
         "Mostly false reasoning.",
         "A false claim alongside some correct reasoning.",
         "A minor inaccuracy that does not affect the judgment.",
         "No false claims."]),
    "false_claim": noul(
        "Does `student_response` state at least one mathematical claim that is false, such as a wrong calculation, "
        "a wrong value, a wrong formula or theorem, or calling a wrong step correct? Use `answer_key` as the truth.",
        "At least one claim the student makes is mathematically false.",
        "Every mathematical claim the student makes is true."),
    "contradicts_key": noul(
        "Does `student_response` assert something about the solution that `answer_key.explanation` or "
        "`answer_key.reference_response` shows to be false?",
        "The student asserts something the answer key shows is false.",
        "Nothing the student asserts conflicts with the answer key."),
    "substantive": noul(
        "Does `student_response` make at least one concrete mathematical claim (a calculation, a value, a property, "
        "or a reason a step fails or holds), beyond only naming a decision and a step?",
        "The student makes at least one concrete mathematical claim.",
        "The student only states a decision and a step, or gives no mathematical content."),
}


def judge_state(row, text):
    item = v1.judge_item(row, v1.clip(text or "(empty response)")[0])
    state = cj.judge_state(item)
    key = row["private"]
    state["answer_key"]["error_type"] = key["error_type"]
    state["answer_key"]["reference_response"] = key["teacher_target_response"]
    return state


def judge_M(ans, rule):
    if rule == "v1":
        return None
    m, mw = cj.argmax(ans["M"]), ans["M"]["score"]
    if rule == "rubric":
        return m, mw
    if ans["substantive"]["noul"] <= 0.5:
        return 0, 0.0
    false = max(ans["false_claim"]["noul"], ans["contradicts_key"]["noul"])
    if rule == "rubric+checks" and false > 0.5:
        return min(m, 2), min(mw, 2.0)
    return m, mw


# ------------------------------------------------------------------- RECONSTRUCT E/M

RECON_EM = {
    "E": score(
        "Score E (evidence integration): how well do `response.question` and `response.justification` use EVERY "
        "numbered item in `observations`? Check each observation in turn. Mentioning an observation is not grounding "
        "it. Example (answer 6; observations: sides sum to 10, the requested quantity is the larger side, an "
        "unreported area K with x(10 - x) = K): 'perimeter 20, area 24, find the longer side' scores 4; the same "
        "setup asking for the shorter side scores 3; 'perimeter 20, find the longer side' with the area only in "
        "the justification scores 2.",
        ["The observations are ignored or predominantly contradicted.",
         "Observations are mentioned without usable connections.",
         "Some substantive use, but important gaps or conflicts.",
         "All observations are connected, with one limited unsupported link.",
         "Every observation substantively fits one coherent reconstruction, and the links are explained."]),
    "M": score(
        "Score M (mathematical validity). Read `response.question` alone: assumptions and justification do not "
        "supply missing premises. Check that its answer is exactly `final_answer`, then check "
        "`response.justification`. A correct final value does not excuse a false claim. A justification that only "
        "repeats the supplied value scores 0, even when the question is fine. Examples (answer 6): 'sides with sum 10 "
        "and product 24, find the larger side', justified by (t - 4)(t - 6) = 0, scores 4; the same question "
        "justified with 'the roots are 3 and 6' scores 1; 'perimeter 20, find the longer side' scores 1 because two "
        "rectangles (3, 7 and 4, 6) fit; the same shorter-side question correctly computing 4 scores 1 because 4 is "
        "not the supplied answer.",
        ["No meaningful verification, or only circular assertions or a restatement of the answer.",
         "A substantive attempt, but the answer is wrong for the question, the question is ill-posed or underdetermined, or an essential claim is false.",
         "Plausible reasoning with an essential unresolved gap in the proof or calculation.",
         "Correct answer and sound argument, with a minor omitted step.",
         "A well-posed question, the supplied answer is correct, and the verification is sufficient and sound."]),
}


# ---------------------------------------------------------------------------- run

def items(task):
    if task == "judge":
        return [tuple(k) for k in json.loads((OUT / "judge-sample.json").read_text())["items"]]
    return v2.sample_items()


def cmd_run(a):
    path = OUT / f"fixes-{a.task}.jsonl"
    done = {(r["arm"], r["id"]) for r in map(json.loads, path.open()) if r.get("ok")} if path.exists() else set()
    rows = {r["uid"]: r for r in rows_for("test", (a.task,))}
    old = v2.v1_records() if a.task == "reconstruct" else None
    resp = {}
    todo = []
    for arm, uid in items(a.task):
        if (arm, uid) in done:
            continue
        if arm not in resp:
            resp[arm] = {x["uid"]: x for x in map(json.loads, (v1.TEST / f"matrix-{arm}" / "responses.jsonl").open())}
        text = resp[arm][uid]["text"]
        if a.task == "judge":
            if judge_gate(text):
                continue
            todo.append(((arm, uid), judge_state(rows[uid], text), JUDGE_M))
        else:
            if (arm, uid) not in old:  # no v1 record (e.g. an empty question field); the gate zeroes it
                continue
            state = old[(arm, uid)]["request"]["validity"]["state"]
            if reconstruct_gate(state["final_answer"], state["response"]["question"]):
                continue
            todo.append(((arm, uid), state, RECON_EM))
    todo = todo[: a.limit or None]
    jev, lock = cj.Jev(), threading.Lock()

    def work(job):
        (arm, uid), state, qs = job
        rec = {"arm": arm, "id": uid, "model": cj.MODEL}
        try:
            rec.update(ok=True, response=jev.call(state, qs))
        except Exception as e:
            rec.update(ok=False, error=str(e)[:500])
        with lock, path.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec["ok"]

    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        ok = list(pool.map(work, todo))
    print(f"{a.task}: {sum(ok)}/{len(todo)} ok, {len(done)} previously done; input tokens {jev.tokens:,}, "
          f"cost ≈ ${jev.tokens * cj.PRICE_PER_TOKEN:.4f}")


# ------------------------------------------------------------------------- report

def load_fixes(task):
    p = OUT / f"fixes-{task}.jsonl"
    return {(r["arm"], r["id"]): r["response"]["answers"] for r in map(json.loads, p.open()) if r.get("ok")} if p.exists() else {}


def summarize(name, keys, ds_dims, ds_tot, ours, dims, uids):
    """One table row: κ per dimension, total r / rating / MAE, mean, and same-question pair ordering."""
    kap = {d: cj.qwk([ds_dims[k][d] for k in keys], [ours[k][0][d] for k in keys]) for d in dims}
    dt = [ds_tot[k] for k in keys]
    jt = [6.25 * sum(ours[k][0].values()) for k in keys]
    jw = [6.25 * sum(ours[k][1].values()) for k in keys]
    pw, pwc, *_ = v2.pairwise(list(zip(uids, dt, jw)))
    means = " ".join(f"{d} {st.mean(ds_dims[k][d] for k in keys):.2f}/{st.mean(ours[k][0][d] for k in keys):.2f}" for d in dims)
    return (f"| {name} | " + " | ".join(f"{kap[d]:.2f}" for d in dims) +
            f" | {cj.pearson(dt, jt):.2f} | {st.mean(cj.rating_v4(a) == cj.rating_v4(b) for a, b in zip(dt, jt)):.0%} | "
            f"{st.mean(abs(a - b) for a, b in zip(dt, jt)):.1f} | {means} | {pw.rsplit(' / ', 1)[0]} | {pwc.rsplit(' / ', 1)[0]} |")


def report_judge(L):
    rows = {r["uid"]: r for r in rows_for("test", ("judge",))}
    fx = load_fixes("judge")
    keys_all = items("judge")
    arms = {a for a, _ in keys_all}
    resp = {a: {x["uid"]: x for x in map(json.loads, (v1.TEST / f"matrix-{a}" / "responses.jsonl").open())} for a in arms}
    det = {a: {x["uid"]: x for x in map(json.loads, (v1.TEST / f"matrix-{a}" / "scores.jsonl").open())} for a in arms}
    ds = {a: {x["uid"]: x for x in map(json.loads, (v1.TEST / f"matrix-{a}" / "judged-scores.jsonl").open())} for a in arms}
    jv = {a: v1.jev_scores(a, rows) for a in arms}
    gated = [k for k in keys_all if judge_gate(resp[k[0]][k[1]]["text"])]
    keys = [k for k in keys_all if k in fx and ds[k[0]].get(k[1], {}).get("score_100") is not None and k[1] in jv[k[0]]]
    L += ["## JUDGE", "", f"500 answers: {len(gated)} fail the strict gate (score 0, not judged); {len(keys)} compared "
          "with DeepSeek. V and L come from the parser in every row except v1.", "",
          "| Version | κ V | κ L | κ E | κ M | Pearson | Rating exact | MAE | Means DeepSeek/Jev | Pairs same / opposite | Close pairs |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|"]
    ds_dims = {k: ds[k[0]][k[1]]["dimensions"] for k in keys}
    ds_tot = {k: ds[k[0]][k[1]]["score_100"] for k in keys}
    uids = [k[1] for k in keys]
    for rule, name in (("v1", "v1 (Jev V/L/E/M)"), ("rubric", "parser V/L + rubric M"),
                       ("rubric+substantive", "… + no-claim check"), ("rubric+checks", "**… + false-claim cap**")):
        ours = {}
        for k in keys:
            j = jv[k[0]][k[1]]
            if rule == "v1":
                ours[k] = (j["dims"], j["dims_weighted"])
                continue
            s = det[k[0]][k[1]]
            V = 4 if s["verdict_correct"] else 0
            L_ = 0 if not V else (4 if s["label"] == "correct" or s["step_correct"] else 0)
            m, mw = judge_M(fx[k], rule)
            ours[k] = ({"V": V, "L": L_, "E": j["dims"]["E"] if V else 0, "M": m},
                       {"V": V, "L": L_, "E": j["dims_weighted"]["E"] if V else 0, "M": mw})
        L.append(summarize(name, keys, ds_dims, ds_tot, ours, "VLEM", uids))
    g = [ds[k[0]][k[1]] for k in gated if ds[k[0]].get(k[1], {}).get("score_100") is not None]
    L += ["", f"DeepSeek scored the {len(g)} gated (hedged or contradictory) answers {st.mean(x['score_100'] for x in g):.1f} "
          f"on average and gave {sum(x['dimensions']['V'] == 4 for x in g)} of them full verdict credit; the gate scores them 0.", ""]


def report_recon(L):
    fx = load_fixes("reconstruct")
    old = v2.v1_records()
    s1 = {(r["arm"], r["id"]): r["response"]["answers"] for r in map(json.loads, (OUT / "staged-shortcut-final.jsonl").open()) if r.get("ok")}
    ds = {}
    for arm in {a for a, _ in v2.sample_items()}:
        for x in map(json.loads, (v1.TEST / f"matrix-{arm}" / "judged-scores.jsonl").open()):
            ds[(arm, x["uid"])] = x
    keys_all = [k for k in v2.sample_items() if k in old]
    gate = {k: reconstruct_gate(old[k]["request"]["validity"]["state"]["final_answer"],
                                old[k]["request"]["validity"]["state"]["response"]["question"]) for k in keys_all}
    keys = [k for k in keys_all if k in s1 and (gate[k] or k in fx)]
    dsk = {"P": "premise_fidelity", "T": "target_fidelity", "E": "evidence_integration", "M": "mathematical_validity"}
    ds_dims = {k: {d: ds[k]["dimensions"][dsk[d]] for d in "PTEM"} for k in keys}
    ds_tot = {k: ds[k]["score_100"] for k in keys}
    uids = [k[1] for k in keys]
    sc_ds = sum(bool(ds[k]["shortcut"]) for k in keys)
    L += ["## RECONSTRUCT", "", f"{len(keys)} answers; {sum(bool(gate[k]) for k in keys)} fail the strict gate. DeepSeek "
          f"flags {sc_ds} shortcuts. Zeroed answers keep their dimension scores for κ but score 0 in total.", "",
          "| Version | κ P | κ T | κ E | κ M | Pearson | Rating exact | MAE | Means DeepSeek/Jev | Pairs same / opposite | Close pairs |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|"]

    def stage1(k):
        a = s1[k]
        return (a["shortcut_type"]["probabilities"]["not a shortcut"] < 0.5 or a["states_value"]["noul"] > 0.5
                or a["repeats_answer"]["noul"] > 0.5)

    for name, use_gate, use_stage1, new_em in (("v1", False, False, False), ("gate + stage 1, v1 E/M", True, True, False),
                                               ("**gate + stage 1 + rubric E/M**", True, True, True)):
        ours = {}
        zero = {}
        for k in keys:
            o = {n: v["answers"] for n, v in old[k]["response"].items()}
            f, v = o["fidelity"], o["validity"]
            em = fx.get(k) if new_em and k in fx else v
            d = {"P": cj.argmax(f["P"]), "T": cj.argmax(f["T"]), "E": cj.argmax(em["E"]), "M": cj.argmax(em["M"])}
            w = {"P": f["P"]["score"], "T": f["T"]["score"], "E": em["E"]["score"], "M": em["M"]["score"]}
            z = (use_gate and bool(gate[k])) or (use_stage1 and stage1(k)) or (not use_stage1 and v["shortcut"]["noul"] > 0.5)
            zero[k] = z
            ours[k] = (d, w)
        kap = {d: cj.qwk([ds_dims[k][d] for k in keys], [ours[k][0][d] for k in keys]) for d in "PTEM"}
        dt = [ds_tot[k] for k in keys]
        jt = [0.0 if zero[k] else 6.25 * sum(ours[k][0].values()) for k in keys]
        jw = [0.0 if zero[k] else 6.25 * sum(ours[k][1].values()) for k in keys]
        pw, pwc, *_ = v2.pairwise(list(zip(uids, dt, jw)))
        means = " ".join(f"{d} {st.mean(ds_dims[k][d] for k in keys):.2f}/{st.mean(ours[k][0][d] for k in keys):.2f}" for d in "PTEM")
        L.append(f"| {name} | " + " | ".join(f"{kap[d]:.2f}" for d in "PTEM") +
                 f" | {cj.pearson(dt, jt):.2f} | {st.mean(cj.rating_v4(a) == cj.rating_v4(b) for a, b in zip(dt, jt)):.0%} | "
                 f"{st.mean(abs(a - b) for a, b in zip(dt, jt)):.1f} | {means} | {pw.rsplit(' / ', 1)[0]} | {pwc.rsplit(' / ', 1)[0]} |")
        L[-1] += f" <!-- zeroed {sum(zero.values())}, of which DeepSeek shortcut {sum(zero[k] and bool(ds[k]['shortcut']) for k in keys)} -->"
    L.append("")


def cmd_report(_a):
    L = ["# Jev judge fixes vs DeepSeek (500-answer samples)", ""]
    report_judge(L)
    report_recon(L)
    (OUT / "fixes-report.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--task", choices=["judge", "reconstruct"], required=True)
    r.add_argument("--limit", type=int, default=0)
    r.add_argument("--workers", type=int, default=16)
    sub.add_parser("report")
    a = ap.parse_args()
    {"run": cmd_run, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()
