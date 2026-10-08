#!/usr/bin/env python3
"""RECONSTRUCT Jev v2: atomic yes/no questions for evidence, validity and shortcuts, plus a code shortcut check.

    python3 scripts/jev_recon_v2.py run --limit 3     # smoke test
    python3 scripts/jev_recon_v2.py run
    python3 scripts/jev_recon_v2.py report

Checked on the fixed sample in artifacts/jev-recon-v2/sample.json: 82 test questions, all 507 checkpoint
answers to them that DeepSeek scored. P and T reuse the v1 fidelity answers (artifacts/jev-vs-deepseek-v1),
which this version does not change; only the validity request is new. v1 and v2 are compared against the
saved DeepSeek scores on the same responses.

Why: v1 caught 15 of DeepSeek's 32 shortcuts in this sample. The misses were an "Answer: X" line inside
the question field, a monologue or meta commentary instead of a question, and a question that just asks
for the supplied answer. Jev reads instructions literally and cannot count, so each shortcut type gets
its own question, each observation gets its own question, and code does the counting and the rubric logic.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import statistics as st
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import compare_jev_judges as cj  # noqa: E402
import jev_vs_deepseek as v1  # noqa: E402

OUT = ROOT / "artifacts" / "jev-recon-v2"
YES = 0.5
noul = cj.noul_q

# ------------------------------------------------------------------ code shortcut check

ANSWER_LINE = re.compile(r"(^|\n|\.\s|\)\s)\s*(\*\*)?(final\s+)?answer(\*\*)?\s*[:=]|\bthe (final )?answer is\b", re.I)
META = re.compile(r"\bJSON\b|\"assumptions\"|\bthe prompt\b|\bobservations?\s*\d|\breconstruct", re.I)


def code_shortcut(question: str | None) -> str | None:
    """A shortcut that needs no judgment: the reason, or None."""
    q = (question or "").strip()
    if len(q) < 15 or not re.search(r"[A-Za-z]", q):
        return "no question"
    if ANSWER_LINE.search(q):
        return "answer stated in the question field"
    if META.search(q):
        return "meta commentary in the question field"
    return None


# ------------------------------------------------------------------ Jev questions

def validity_questions(n_obs: int) -> dict:
    q = {}
    for i in range(1, n_obs + 1):
        q[f"obs{i}"] = noul(
            f"Look at observation number {i} in `observations`. Is this observation built into "
            "`response.question`, or explicitly connected to it in `response.justification`, in a way that agrees "
            "with the observation? Only repeating the observation's words without linking it to the question "
            "does not count.",
            f"Observation {i} is part of the reconstructed question, or the justification links it to the question, and they agree.",
            f"Observation {i} is ignored, only repeated without a link, or contradicted.")
    q["contradiction"] = noul(
        "Does `response.question` or `response.justification` state something that contradicts any item in `observations`?",
        "At least one statement in the response contradicts an observation.",
        "Nothing in the response contradicts the observations.")
    q["restates"] = noul(
        "Does `response.justification` only repeat `final_answer` or the question, without any derivation or "
        "calculation that leads to it?",
        "The justification only restates the answer or the question; there is no derivation.",
        "The justification contains a derivation or calculation, even if it is flawed.")
    q["well_posed"] = noul(
        "Read only `response.question`, ignoring the assumptions and the justification. Does it give every value "
        "and condition needed to determine one single answer, with no conflicting conditions?",
        "The question alone determines a single answer.",
        "Something needed is missing, a condition conflicts, or the answer is not unique.")
    q["answer_matches"] = noul(
        "If `response.question` were solved correctly, would the answer be exactly `final_answer`?",
        "Solving the question gives exactly `final_answer`.",
        "Solving the question gives something other than `final_answer`, or cannot be done.")
    q["false_claim"] = noul(
        "Does `response.justification` contain a mathematical statement that is false?",
        "At least one mathematical statement in the justification is false.",
        "Every mathematical statement in the justification is true.")
    q["complete"] = noul(
        "Does `response.justification` show every step needed to get from `response.question` to `final_answer`?",
        "Every needed step is shown.",
        "At least one needed step is missing.")
    q["sc_states_value"] = noul(
        "Does `response.question` itself already state the value of the quantity it asks to find, for example a "
        "line such as 'Answer: ...' or a premise that gives the requested value directly?",
        "The question states the value of the very quantity it asks for.",
        "The question does not state the value it asks for.")
    q["sc_repeat"] = noul(
        "Does `response.question` merely ask to repeat or restate `final_answer`, for example 'What is X?' where X "
        "is written exactly as `final_answer`, with nothing to compute?",
        "The question only asks to repeat the supplied answer.",
        "The question asks for something that has to be worked out.")
    q["sc_no_request"] = noul(
        "Is `response.question` a single coherent mathematical problem statement? Answer no if it is mostly the "
        "writer's own commentary, reasoning, drafts or self-corrections, or if it contains no identifiable request.",
        "It is one coherent problem statement with an identifiable request.",
        "It is commentary, reasoning or drafts, or it has no identifiable request.")
    return q


def p(ans, k):
    return ans[k]["noul"]


def v2_dims(ans: dict, n_obs: int, question: str | None, fidelity: dict) -> dict:
    used = [p(ans, f"obs{i}") for i in range(1, n_obs + 1)]
    contra = p(ans, "contradiction")
    k = sum(x > YES for x in used)
    E = max(0, k - (contra > YES))
    E_w = max(0.0, sum(used) * 4 / n_obs - contra)
    if p(ans, "restates") > YES:
        M = 0
    elif min(p(ans, "well_posed"), p(ans, "answer_matches")) <= YES or p(ans, "false_claim") > YES:
        M = 1
    else:
        M = 4 if p(ans, "complete") > 0.8 else 3 if p(ans, "complete") > YES else 2
    M_w = (1 - p(ans, "restates")) * (1 + 3 * p(ans, "well_posed") * p(ans, "answer_matches")
                                       * (1 - p(ans, "false_claim")) * (0.33 + 0.67 * p(ans, "complete")))
    code = code_shortcut(question)
    jev_sc = max(p(ans, "sc_states_value"), p(ans, "sc_repeat"), 1 - p(ans, "sc_no_request"))
    P, T = cj.argmax(fidelity["P"]), cj.argmax(fidelity["T"])
    Pw, Tw = fidelity["P"]["score"], fidelity["T"]["score"]
    out = {}
    for name, sc in (("code", code is not None), ("jev", jev_sc > YES), ("combined", code is not None or jev_sc > YES)):
        out[name] = {"shortcut": sc, "score_100": 0.0 if sc else 6.25 * (P + T + E + M),
                     "score_100_weighted": 0.0 if sc else 6.25 * (Pw + Tw + E_w + M_w)}
    return {"dims": {"P": P, "T": T, "E": E, "M": M}, "code_reason": code, "jev_shortcut_p": jev_sc, **out}


# ---------------------------------------------------------------------- run

def sample_items():
    s = json.loads((OUT / "sample.json").read_text())
    return [(arm, it["uid"]) for it in s["items"] for arm in it["arms"]]


def v1_records() -> dict:
    recs = {}
    for arm in {a for a, _ in sample_items()}:
        for uid, r in cj.load_done(v1.OUT / f"{arm}.jsonl").items():
            recs[(arm, uid)] = r
    return recs


def cmd_run(a):
    path = OUT / "validity-v2.jsonl"
    done = {(r["arm"], r["id"]) for r in map(json.loads, path.open()) if r.get("ok")} if path.exists() else set()
    old = v1_records()
    todo = [k for k in sample_items() if k not in done and k in old][: a.limit or None]
    jev, lock = cj.Jev(), threading.Lock()

    def work(key):
        arm, uid = key
        state = old[key]["request"]["validity"]["state"]  # same inputs as v1 and DeepSeek
        qs = validity_questions(len(state["observations"]))
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
    print(f"{sum(ok)}/{len(todo)} ok, {len(done)} previously done; input tokens {jev.tokens:,}, "
          f"cost ≈ ${jev.tokens * cj.PRICE_PER_TOKEN:.4f}")


# ---------------------------------------------------------------------- report

def pairwise(vals):
    """vals: list of (question uid, deepseek, jev). Same/opposite/tie on pairs DeepSeek separates."""
    by = {}
    for u, d, j in vals:
        by.setdefault(u, []).append((d, j))
    c = [0, 0, 0]
    close = [0, 0, 0]
    for v in by.values():
        for (d1, j1), (d2, j2) in itertools.combinations(v, 2):
            if d1 == d2:
                continue
            s = (d1 - d2) * (j1 - j2)
            idx = 0 if s > 0 else 1 if s < 0 else 2
            c[idx] += 1
            if abs(d1 - d2) <= 12.5:
                close[idx] += 1
    f = lambda x: f"{x[0] / sum(x):.0%} / {x[1] / sum(x):.0%} / {x[2] / sum(x):.0%}" if sum(x) else "—"
    return f(c), f(close), sum(c), sum(close)


def cmd_report(_a):
    old = v1_records()
    new = {(r["arm"], r["id"]): r for r in map(json.loads, (OUT / "validity-v2.jsonl").open()) if r.get("ok")}
    ds = {}
    for arm in {a for a, _ in sample_items()}:
        for x in map(json.loads, (v1.TEST / f"matrix-{arm}" / "judged-scores.jsonl").open()):
            ds[(arm, x["uid"])] = x
    rows = []
    for key in sample_items():
        if key not in new or key not in old:
            continue
        o = {k: v["answers"] for k, v in old[key]["response"].items()}
        state = old[key]["request"]["validity"]["state"]
        rows.append((key, ds[key], cj.recon_dims(o, "validity"),
                     v2_dims(new[key]["response"]["answers"], len(state["observations"]),
                             state["response"]["question"], o["fidelity"])))
    n = len(rows)
    L = ["# RECONSTRUCT Jev v2 vs v1, against DeepSeek", "",
         f"Fixed sample: {n} checkpoint answers to {len({k[1] for k, *_ in rows})} test questions "
         "(artifacts/jev-recon-v2/sample.json). P and T are identical in v1 and v2.", "",
         "## Dimensions (weighted κ against DeepSeek; mean DeepSeek vs Jev)", "",
         "| Dim | v1 κ | v2 κ | DeepSeek mean | v1 mean | v2 mean |", "|---|---:|---:|---:|---:|---:|"]
    for d, name in (("E", "evidence_integration"), ("M", "mathematical_validity")):
        dd = [x["dimensions"][name] for _, x, _, _ in rows]
        a1 = [j1["dims"][d] for *_, j1, _ in rows]
        a2 = [j2["dims"][d] for *_, j2 in rows]
        L.append(f"| {d} | {cj.qwk(dd, a1):.2f} | {cj.qwk(dd, a2):.2f} | {st.mean(dd):.2f} | {st.mean(a1):.2f} | {st.mean(a2):.2f} |")
    sc_ds = [bool(x["shortcut"]) for _, x, _, _ in rows]
    L += ["", f"## Shortcuts (DeepSeek flags {sum(sc_ds)} of {n})", "",
          "| Detector | Caught | False flags |", "|---|---:|---:|"]
    dets = [("v1 Jev", lambda j1, j2: j1["shortcut"]), ("v2 code check", lambda j1, j2: j2["code"]["shortcut"]),
            ("v2 Jev questions", lambda j1, j2: j2["jev"]["shortcut"]), ("v2 combined", lambda j1, j2: j2["combined"]["shortcut"])]
    for name, f in dets:
        flags = [f(j1, j2) for *_, j1, j2 in rows]
        L.append(f"| {name} | {sum(a and b for a, b in zip(sc_ds, flags))} / {sum(sc_ds)} | {sum(b and not a for a, b in zip(sc_ds, flags))} |")
    reasons = {}
    for (_, x, _, j2), a in zip(rows, sc_ds):
        if j2["code_reason"]:
            reasons.setdefault(j2["code_reason"], [0, 0])[0 if a else 1] += 1
    L += [""] + [f"- Code check, {r}: {v[0]} agree with DeepSeek, {v[1]} not flagged by DeepSeek." for r, v in reasons.items()]
    L += ["", "## Total score", "",
          "| Version | Pearson | 1–5 rating exact | MAE | Mean (DeepSeek "
          f"{st.mean(x['score_100'] for _, x, _, _ in rows):.1f}) | Pairs same / opposite / tie | Close pairs same / opposite / tie |",
          "|---|---:|---:|---:|---:|---|---|"]
    dt = [x["score_100"] for _, x, _, _ in rows]
    variants = [("v1", lambda j1, j2: (j1["score_100"], j1["score_100_weighted"]))]
    for name in ("code", "jev", "combined"):
        variants.append((f"v2 ({name} shortcut)", lambda j1, j2, name=name: (j2[name]["score_100"], j2[name]["score_100_weighted"])))
    for name, f in variants:
        vals = [f(j1, j2) for *_, j1, j2 in rows]
        jt = [v[0] for v in vals]
        uids = [k[1] for k, *_ in rows]
        pw, pwc, npairs, nclose = pairwise(list(zip(uids, dt, [v[1] for v in vals])))
        L.append(f"| {name} | {cj.pearson(dt, jt):.2f} | {st.mean(cj.rating_v4(a) == cj.rating_v4(b) for a, b in zip(dt, jt)):.0%} | "
                 f"{st.mean(abs(a - b) for a, b in zip(dt, jt)):.1f} | {st.mean(jt):.1f} | {pw} | {pwc} |")
    L += ["", f"Pairs: answers to the same question that DeepSeek scored differently ({npairs}; close = within "
          f"12.5 points, {nclose}), ordered with Jev's probability-weighted score, as a GRPO reward would use it."]
    (OUT / "report.md").write_text("\n".join(L) + "\n")
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
