#!/usr/bin/env python3
"""Audit src/anlp_project/strict_gates.py on 500-answer samples of the saved FINAL-v3 test evaluations.

    python3 scripts/audit_strict_gates.py            # counts per rule
    python3 scripts/audit_strict_gates.py --show 8   # plus examples of each rule, for reading

RECONSTRUCT uses artifacts/jev-recon-v2/sample.json (506 answers, DeepSeek shortcut flags known). JUDGE and
SOLVE use 500 answers drawn with a fixed seed from the 8 matrix checkpoints. No model is called.
"""

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anlp_project.baseline import extract_reconstruction, rows_for  # noqa: E402
from anlp_project.strict_gates import judge_gate, reconstruct_format_flags, reconstruct_gate, solve_gate  # noqa: E402

TEST = ROOT / "artifacts" / "baselines" / "final-v3" / "test"
SEED = 20261006


def load(arm, name):
    return {x["uid"]: x for x in map(json.loads, (TEST / f"matrix-{arm}" / name).open())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=0)
    a = ap.parse_args()
    arms = sorted(p.name.removeprefix("matrix-") for p in TEST.glob("matrix-*"))
    rows = {r["uid"]: r for r in rows_for("test")}
    resp = {arm: load(arm, "responses.jsonl") for arm in arms}
    det = {arm: load(arm, "scores.jsonl") for arm in arms}
    judged = {arm: load(arm, "judged-scores.jsonl") for arm in arms}
    report = {}

    # RECONSTRUCT
    sample = json.loads((ROOT / "artifacts/jev-recon-v2/sample.json").read_text())["items"]
    hits, ex, fmt = Counter(), {}, Counter()
    ds_sc = flagged = both = 0
    for it in sample:
        for arm in it["arms"]:
            text = resp[arm][it["uid"]]["text"]
            r, _ = extract_reconstruction(text)
            rules = reconstruct_gate(rows[it["uid"]]["public_input"]["final_answer"], r["question"])
            fmt[bool(reconstruct_format_flags(text))] += 1
            ds = bool(judged[arm][it["uid"]]["shortcut"])
            ds_sc += ds
            flagged += bool(rules)
            both += bool(rules) and ds
            for rule in rules:
                hits[rule] += 1
                ex.setdefault(rule, []).append((arm, it["uid"], ds, rows[it["uid"]]["public_input"]["final_answer"], r["question"]))
    n = sum(len(it["arms"]) for it in sample)
    report["reconstruct"] = {"n": n, "failed": flagged, "deepseek_shortcuts": ds_sc, "deepseek_shortcuts_failed": both,
                             "rules": dict(hits), "format_flag_several_drafts": fmt[True]}
    print(f"RECONSTRUCT {n}: {flagged} fail a gate; DeepSeek shortcuts {ds_sc}, of which {both} fail a gate; {dict(hits)}; format flag several_drafts {fmt[True]}")
    if a.show:
        for rule, xs in ex.items():
            random.Random(SEED).shuffle(xs)
            print(f"\n=== {rule} ({len(xs)}; DeepSeek shortcut among them: {sum(x[2] for x in xs)})")
            for arm, uid, ds, fa, q in xs[: a.show]:
                print(f"- {arm} {uid} DS_shortcut={ds} ANSWER={fa!r}\n    Q: {q[:300]!r}")

    # JUDGE and SOLVE
    for task, gate in (("judge", judge_gate), ("solve", solve_gate)):
        pool = [(arm, uid) for arm in arms for uid, s in det[arm].items() if s["task"] == task]
        pick = random.Random(f"{SEED}:{task}").sample(pool, 500)
        hits, ex, rewarded = Counter(), {}, 0
        for arm, uid in pick:
            rules = gate(resp[arm][uid]["text"])
            s = det[arm][uid]
            good = s.get("verdict_correct") if task == "judge" else s.get("answer_status") == "correct"
            rewarded += bool(rules) and bool(good)
            for rule in rules:
                hits[rule] += 1
                ex.setdefault(rule, []).append((arm, uid, good))
        status = Counter(det[arm][uid].get("answer_status") for arm, uid in pick) if task == "solve" else None
        report[task] = {"n": 500, "failed": sum(1 for arm, uid in pick if gate(resp[arm][uid]["text"])),
                        "failed_but_scored_correct_today": rewarded, "rules": dict(hits),
                        **({"answer_status": dict(status)} if status else {})}
        print(f"{task.upper()} 500: {report[task]['failed']} fail a gate, {rewarded} of them currently scored correct; "
              f"{dict(hits)}" + (f"; answer status {dict(status)}" if status else ""))
        if a.show:
            for rule, xs in ex.items():
                print(f"\n=== {task} {rule} ({len(xs)})")
                for arm, uid, good in xs[: a.show]:
                    t = resp[arm][uid]["text"]
                    import re
                    pat = r"Decision:.{0,40}|First wrong step:.{0,20}" if task == "judge" else r"<final_answer>.{0,60}?</final_answer>"
                    print(f"- {arm} {uid} scored_correct={good}: {[m for m in re.findall(pat, t, re.S | re.I)][:6]}")
    out = ROOT / "artifacts" / "strict-gates-audit.json"
    out.write_text(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main()
