#!/usr/bin/env python3
"""Re-score the saved FINAL-v3 test evaluations with Jev and compare with the saved DeepSeek scores.

    python3 scripts/jev_vs_deepseek.py run --arms base --limit 5     # smoke test
    python3 scripts/jev_vs_deepseek.py run                           # every matrix-* arm
    python3 scripts/jev_vs_deepseek.py report

The Jev questions, the gating and the 6.25 * sum aggregation come from compare_jev_judges.py (the
earlier agreement study on Qwen3-4B responses); only the inputs are adapted to FINAL-v3 rows. JUDGE
gets the problem, the proposed solution, the key's label, first wrong step, explanation and error
type (the teacher's reference response, which DeepSeek also sees, is left out to keep the state
small). RECONSTRUCT gets the same fidelity and validity inputs as DeepSeek. Responses the
RECONSTRUCT parser cannot read are not judged, as with DeepSeek.

Raw requests and responses go to artifacts/jev-vs-deepseek-v1/<arm>.jsonl; finished items are never
re-requested. DeepSeek scores are the saved judged-scores.jsonl, which are a reference, not ground truth.
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import statistics as st
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import compare_jev_judges as cj  # noqa: E402
from anlp_project.baseline import extract_reconstruction, rows_for  # noqa: E402

TEST = ROOT / "artifacts" / "baselines" / "final-v3" / "test"
OUT = ROOT / "artifacts" / "jev-vs-deepseek-v1"
MAX_CHARS = 40_000  # LaTeX-dense text runs ~2 chars/token; Jev allows 32k tokens for state + the longest question
RECON_DIMS = {"P": "premise_fidelity", "T": "target_fidelity", "E": "evidence_integration",
              "M": "mathematical_validity"}


def arms() -> list[str]:
    return sorted(p.name.removeprefix("matrix-") for p in TEST.glob("matrix-*") if (p / "judged-scores.jsonl").exists())


def clip(text: str) -> tuple[str, bool]:
    if len(text) <= MAX_CHARS:
        return text, False
    head = MAX_CHARS // 4  # keep the opening and, mostly, the end, where the verdict is
    return text[:head] + "\n[... middle of the response omitted for length ...]\n" + text[-(MAX_CHARS - head):], True


def judge_item(row, text) -> dict:
    """compare_jev_judges.judge_* expect the earlier item layout; build it from a FINAL-v3 row."""
    key = row["private"]
    return {"problem": row["public"]["problem"], "proposed_solution": row["public"]["proposed_solution"],
            "key_label": key["label"], "key_first_wrong_step": key["first_error_step_id"] or "none",
            "key_explanation": key["first_error_explanation"], "qwen_response": text}


def requests_for(row, text) -> tuple[dict, bool] | None:
    """{name: (state, questions)} for one response, or None when the response is not judged."""
    text, truncated = clip(text or "(empty response)")
    if row["task"] == "judge":
        item = judge_item(row, text)
        state = cj.judge_state(item)
        state["answer_key"]["error_type"] = row["private"]["error_type"]
        return {"judge": (state, cj.judge_questions(item))}, truncated
    response, _ = extract_reconstruction(text)
    if response is None:
        return None
    item = {"source_question": row["question"], "clues": row["public_input"]["clues"],
            "source_final_answer": row["public_input"]["final_answer"], "source_reference_solution": "",
            "qwen": response}
    reqs = cj.recon_requests(item)
    return {k: reqs[k] for k in ("fidelity", "validity")}, truncated


def cmd_run(a):
    OUT.mkdir(parents=True, exist_ok=True)
    rows = {r["uid"]: r for r in rows_for("test", ("judge", "reconstruct"))}
    jev, lock = cj.Jev(), threading.Lock()
    for arm in a.arms or arms():
        path = OUT / f"{arm}.jsonl"
        done = cj.load_done(path)
        responses = [json.loads(l) for l in (TEST / f"matrix-{arm}" / "responses.jsonl").open()]
        todo = []
        for resp in responses:
            row = rows.get(resp["uid"])
            if row is None or row["task"] == "solve" or resp["uid"] in done:
                continue
            built = requests_for(row, resp["text"])
            if built is not None:
                todo.append((resp["uid"], row["task"], *built))
        todo = todo[: a.limit or None]

        def work(job):
            uid, task, reqs, truncated = job
            rec = {"id": uid, "task": task, "model": cj.MODEL, "truncated": truncated, "request": {}, "response": {}}
            try:
                for name, (state, qs) in reqs.items():
                    rec["request"][name] = {"state": state, "questions": qs}
                    rec["response"][name] = jev.call(state, qs)
                rec["ok"] = True
            except Exception as e:  # keep the failure, never guess a score
                rec.update(ok=False, error=str(e)[:500])
            with lock, path.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return rec["ok"]

        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            ok = list(pool.map(work, todo))
        print(f"{arm}: {sum(ok)}/{len(todo)} ok, {len(done)} previously done", flush=True)
    print(f"input tokens this run: {jev.tokens:,}  cost ≈ ${jev.tokens * cj.PRICE_PER_TOKEN:.4f}")


# ----------------------------------------------------------------------- report

def jev_scores(arm, rows) -> dict[str, dict]:
    out = {}
    for uid, rec in cj.load_done(OUT / f"{arm}.jsonl").items():
        ans = {k: v["answers"] for k, v in rec["response"].items()}
        if rec["task"] == "judge":
            item = judge_item(rows[uid], "")
            out[uid] = cj.judge_dims(item, ans["judge"])
        else:
            out[uid] = cj.recon_dims(ans, "validity")
        out[uid]["truncated"] = rec["truncated"]
    return out


def kendall(x, y) -> float:
    c = d = 0
    for i, j in itertools.combinations(range(len(x)), 2):
        s = (x[i] - x[j]) * (y[i] - y[j])
        c += s > 0
        d += s < 0
    return (c - d) / (c + d) if c + d else float("nan")


def boot_diff(pairs, seed=0):
    rng = random.Random(seed)
    means = sorted(st.mean(rng.choices(pairs, k=len(pairs))) for _ in range(2000))
    return st.mean(pairs), means[49], means[1949]


def cmd_report(_a):
    rows = {r["uid"]: r for r in rows_for("test", ("judge", "reconstruct"))}
    all_arms = arms()
    ds, jv = {}, {}
    for arm in all_arms:
        ds[arm] = {x["uid"]: x for x in map(json.loads, (TEST / f"matrix-{arm}" / "judged-scores.jsonl").open())}
        jv[arm] = jev_scores(arm, rows)
    lines = ["# Jev vs DeepSeek on the FINAL-v3 test evaluations", "",
             f"Jev `{cj.MODEL}` re-scored the {len(all_arms)} saved checkpoints in "
             "`artifacts/baselines/final-v3/test/matrix-*`. DeepSeek V4.1 Flash scores are the saved "
             "`judged-scores.jsonl`. They are a reference, not ground truth. Item-level numbers use items both judges scored.", ""]
    summary = {}
    for task, dims in (("judge", {d: d for d in "VLEM"}), ("reconstruct", RECON_DIMS)):
        both = [(arm, uid, ds[arm][uid], jv[arm][uid]) for arm in all_arms for uid in jv[arm]
                if rows[uid]["task"] == task and ds[arm].get(uid, {}).get("score_100") is not None]
        if not both:
            continue
        s = {"n_both": len(both),
             "jev_only": sum(1 for arm in all_arms for uid in jv[arm] if rows[uid]["task"] == task
                             and ds[arm].get(uid, {}).get("score_100") is None),
             "truncated": sum(j["truncated"] for *_, j in both)}
        s["dimensions"] = []
        for d, name in dims.items():
            pairs = [(x["dimensions"][name], j["dims"][d], j["dims_weighted"][d]) for *_, x, j in both
                     if x["dimensions"][name] is not None]
            s["dimensions"].append(cj.agreement(d, [p[0] for p in pairs], [p[1] for p in pairs], [p[2] for p in pairs]))
        dt = [x["score_100"] for *_, x, _ in both]
        jt = [j["score_100"] for *_, j in both]
        s["total"] = {"pearson": cj.pearson(dt, jt), "spearman_weighted": cj.spearman(dt, [j["score_100_weighted"] for *_, j in both]),
                      "mae": st.mean(abs(a - b) for a, b in zip(dt, jt)), "deepseek_mean": st.mean(dt), "jev_mean": st.mean(jt)}
        s["rating_exact"] = st.mean(cj.rating_v4(a) == cj.rating_v4(b) for a, b in zip(dt, jt))
        if task == "reconstruct":
            sc = [(bool(x["shortcut"]), j["shortcut"]) for *_, x, j in both]
            s["shortcut"] = {"deepseek": sum(a for a, _ in sc), "jev": sum(b for _, b in sc), "agree": st.mean(a == b for a, b in sc)}
            eq = [(x.get("semantic_equivalent") is True, j["dims"]["P"] == 4 and j["dims"]["T"] == 4,
                   j["equivalent_p"] > 0.5) for *_, x, j in both]
            s["same_question"] = {"deepseek": sum(a for a, _, _ in eq), "jev_P4T4": sum(b for _, b, _ in eq),
                                  "jev_noul": sum(c for _, _, c in eq), "both_P4T4": sum(a and b for a, b, _ in eq)}
        lines += cj.table(f"{task.upper()}: item level ({len(both)} responses from {len(all_arms)} checkpoints)", s)
        lines.append(f"- Scored by Jev but unresolved by DeepSeek: {s['jev_only']}. Inputs shortened for length: {s['truncated']}.")
        if task == "reconstruct":
            lines.append(f"- Shortcut flags: DeepSeek {s['shortcut']['deepseek']}, Jev {s['shortcut']['jev']}, agreement {s['shortcut']['agree']:.1%}. "
                         f"Same question: DeepSeek {s['same_question']['deepseek']}, Jev P4∧T4 {s['same_question']['jev_P4T4']} "
                         f"(both {s['same_question']['both_P4T4']}), Jev yes/no {s['same_question']['jev_noul']}.")
        lines.append("")

        # Checkpoint level: means and paired differences against base, on items both judges scored.
        per = {arm: {uid: (x["score_100"], j["score_100"]) for a2, uid, x, j in both if a2 == arm} for arm in all_arms}
        lines += [f"### {task.upper()}: checkpoint level", "",
                  "| Checkpoint | n | DeepSeek mean | Jev mean | Δ vs base, DeepSeek [95% CI] | Δ vs base, Jev [95% CI] |",
                  "|---|---:|---:|---:|---:|---:|"]
        ck = {}
        for arm in all_arms:
            m = per[arm]
            if not m:
                continue
            row = [arm, str(len(m)), f"{st.mean(v[0] for v in m.values()):.1f}", f"{st.mean(v[1] for v in m.values()):.1f}"]
            ck[arm] = (st.mean(v[0] for v in m.values()), st.mean(v[1] for v in m.values()))
            if arm != "base" and "base" in per:
                common = sorted(set(m) & set(per["base"]))
                dd = boot_diff([m[u][0] - per["base"][u][0] for u in common])
                dj = boot_diff([m[u][1] - per["base"][u][1] for u in common])
                row += [f"{dd[0]:+.1f} [{dd[1]:+.1f}, {dd[2]:+.1f}]", f"{dj[0]:+.1f} [{dj[1]:+.1f}, {dj[2]:+.1f}]"]
            else:
                row += ["—", "—"]
            lines.append("| " + " | ".join(row) + " |")
        names = list(ck)
        s["checkpoint_kendall"] = kendall([ck[n][0] for n in names], [ck[n][1] for n in names])
        lines += ["", f"- Checkpoint ranking, Kendall τ (DeepSeek vs Jev means): {s['checkpoint_kendall']:.2f}.", ""]

        # Question level: do the judges order different checkpoints' answers to the same question alike?
        by_q = {}
        for arm, uid, x, j in both:
            by_q.setdefault(uid, []).append((x["score_100"], j["score_100"]))
        conc = disc = jtie = 0
        close = [0, 0, 0]
        for vals in by_q.values():
            for (d1, j1), (d2, j2) in itertools.combinations(vals, 2):
                if d1 == d2:
                    continue
                sgn = (d1 - d2) * (j1 - j2)
                conc += sgn > 0
                disc += sgn < 0
                jtie += sgn == 0
                if abs(d1 - d2) <= 12.5:
                    close[0 if sgn > 0 else 1 if sgn < 0 else 2] += 1
        tot = conc + disc + jtie
        s["pairwise"] = {"pairs": tot, "concordant": conc / tot, "discordant": disc / tot, "jev_tie": jtie / tot,
                         "close_pairs": sum(close), "close_concordant": close[0] / max(1, sum(close)),
                         "close_discordant": close[1] / max(1, sum(close))}
        p = s["pairwise"]
        lines += [f"### {task.upper()}: same question, different checkpoints", "",
                  f"For each question, every pair of checkpoint answers that DeepSeek scored differently ({p['pairs']} pairs): "
                  f"Jev orders them the same way {p['concordant']:.1%}, the opposite way {p['discordant']:.1%}, "
                  f"and gives a tie {p['jev_tie']:.1%}. On close pairs (DeepSeek within 12.5 points, {p['close_pairs']} pairs): "
                  f"same {p['close_concordant']:.1%}, opposite {p['close_discordant']:.1%}. "
                  "This is the comparison a GRPO reward makes inside a group of samples.", ""]
        summary[task] = s
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--arms", nargs="*", default=None, help="default: every matrix-* arm")
    r.add_argument("--limit", type=int, default=0, help="at most this many new items per arm")
    r.add_argument("--workers", type=int, default=16)
    sub.add_parser("report")
    a = p.parse_args()
    {"run": cmd_run, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()
