#!/usr/bin/env python3
"""Calibrate the Qwen3.8-27B final judge on the same 500-answer samples as Jev, against the saved DeepSeek scores.

    python3 scripts/qwen_judge_calibration.py build     # requests.jsonl (local; no model)
    # on Turing: python scripts/turing/qwen_judge_run.py --requests <requests.jsonl> --out <answers.jsonl>
    python3 scripts/qwen_judge_calibration.py fit       # cutoffs + held-out agreement (local)
    python3 scripts/qwen_judge_calibration.py score <eval dir>/s0 ...   # judgments.qwen.jsonl -> judged-scores.qwen.jsonl

Requests use jev_judging's questions and states exactly. RECONSTRUCT uses the reconstruction DeepSeek judged
(baseline.extract_reconstruction), so both judges score the same text. Every request is asked, whatever an
earlier stage decides, so each stage can be checked. Cutoffs are fitted as for Jev (maximum quadratic-weighted
kappa against DeepSeek levels on the probability-weighted score) and checked by fitting on 4 checkpoints and
testing on the other 4. Output: data/jev-eval/calibration-qwen27b-v1.json and
artifacts/qwen-judge-calibration/report.md.
"""

import argparse
import itertools
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import compare_jev_judges as cj  # noqa: E402  (qwk, pearson)
from anlp_project import jev_judging as jj  # noqa: E402
from anlp_project.baseline import extract_reconstruction, rows_for  # noqa: E402
from anlp_project.strict_gates import judge_gate, reconstruct_gate  # noqa: E402

TEST = ROOT / "artifacts" / "baselines" / "final-v3" / "test"
SAMPLES = ROOT / "artifacts" / "jev-recon-v2"
OUT = ROOT / "artifacts" / "qwen-judge-calibration"
CAL = ROOT / "data" / "jev-eval" / "calibration-qwen27b-v1.json"
NAMES = {"P": "premise_fidelity", "T": "target_fidelity", "E": "evidence_integration", "M": "mathematical_validity"}


def samples():
    judge = [tuple(k) for k in json.loads((SAMPLES / "judge-sample.json").read_text())["items"]]
    recon = [(arm, it["uid"]) for it in json.loads((SAMPLES / "sample.json").read_text())["items"] for arm in it["arms"]]
    return judge, recon


def load(arm, name):
    return {x["uid"]: x for x in map(json.loads, (TEST / f"matrix-{arm}" / name).open())}


def cmd_build(_a):
    rows = {r["uid"]: r for r in rows_for("test", ("judge", "reconstruct"))}
    judge, recon = samples()
    OUT.mkdir(parents=True, exist_ok=True)
    cache, n = {}, 0
    with (OUT / "requests.jsonl").open("w") as fh:
        for arm, uid in judge + recon:
            if arm not in cache:
                cache[arm] = load(arm, "responses.jsonl")
            text, row = cache[arm][uid]["text"], rows[uid]
            if row["task"] == "judge":
                if judge_gate(text):
                    continue
                reqs = jj.judge_requests(row, text)
            else:
                resp, _ = extract_reconstruction(text)
                if resp is None or reconstruct_gate(row["public_input"]["final_answer"], resp["question"]):
                    continue
                states = jj.reconstruct_states(row, resp)
                reqs = {"shortcut": (states["shortcut"], jj.SHORTCUT_QUESTIONS),
                        "fidelity": (states["fidelity"], jj.FIDELITY_QUESTIONS),
                        "validity": (states["validity"], jj.VALIDITY_QUESTIONS)}
            for part, (state, qs) in reqs.items():
                fh.write(json.dumps({"key": f"{arm}|{uid}|{part}", "state": state, "questions": qs},
                                    ensure_ascii=False) + "\n")
                n += 1
    print(f"{n} requests -> {OUT / 'requests.jsonl'}")


def fit_cutoffs(ws, ys):
    grid = [x / 10 for x in range(0, 41)]
    return max(itertools.combinations(grid, 4), key=lambda c: cj.qwk(ys, [sum(w >= x for x in c) for w in ws]))


def cmd_fit(_a):
    ans = {}
    for line in (OUT / "answers.jsonl").open():
        r = json.loads(line)
        if r.get("ok"):
            arm, uid, part = r["key"].split("|")
            ans.setdefault((arm, uid), {})[part] = r["response"]["answers"]
    judge, recon = samples()
    arms = sorted({a for a, _ in judge + recon})
    ds = {a: load(a, "judged-scores.jsonl") for a in arms}
    det = {a: load(a, "scores.jsonl") for a in arms}
    fit_arms = set(arms[::2])
    dims = []  # (name, key list, weighted score fn, DeepSeek level fn)
    jk = [k for k in judge if k in ans and ds[k[0]].get(k[1], {}).get("score_100") is not None]
    dims.append(("judge.M", jk, lambda k: ans[k]["M"]["M"]["score"], lambda k: ds[k[0]][k[1]]["dimensions"]["M"]))
    ek = [k for k in jk if "E" in ans[k] and ds[k[0]][k[1]]["dimensions"]["V"] == 4]
    dims.append(("judge.E", ek, lambda k: ans[k]["E"]["E"]["score"] * (2 if det[k[0]][k[1]]["label"] == "correct" else 1),
                 lambda k: ds[k[0]][k[1]]["dimensions"]["E"]))
    rk = [k for k in recon if k in ans and len(ans[k]) == 3 and ds[k[0]].get(k[1], {}).get("score_100") is not None]
    for d, part in (("P", "fidelity"), ("T", "fidelity"), ("E", "validity"), ("M", "validity")):
        dims.append((f"reconstruct.{d}", rk, lambda k, d=d, part=part: ans[k][part][d]["score"],
                     lambda k, d=d: ds[k[0]][k[1]]["dimensions"][NAMES[d]]))
    L = ["# Qwen3.8-27B judge calibration against DeepSeek", "",
         "Cutoffs on the probability-weighted level; held-out = fitted on 4 checkpoints, tested on the other 4. "
         "Jev's held-out numbers for comparison: JUDGE M 0.88, RECONSTRUCT P 0.68, T 0.74, E 0.63, M 0.72.", "",
         "| Dimension | n | held-out κ (nearest level) | held-out κ (calibrated) | mean DeepSeek / 27B |", "|---|---:|---:|---:|---|"]
    cut = {}
    for name, keys, w, y in dims:
        tr = [k for k in keys if k[0] in fit_arms]
        te = [k for k in keys if k[0] not in fit_arms]
        c = fit_cutoffs([w(k) for k in tr], [y(k) for k in tr])
        lv = lambda x, c=c: sum(x >= t for t in c)
        L.append(f"| {name} | {len(keys)} | {cj.qwk([y(k) for k in te], [min(4, round(w(k))) for k in te]):.2f} | "
                 f"{cj.qwk([y(k) for k in te], [lv(w(k)) for k in te]):.2f} | "
                 f"{st.mean(y(k) for k in te):.2f} / {st.mean(lv(w(k)) for k in te):.2f} |")
        cut[name] = list(fit_cutoffs([w(k) for k in keys], [y(k) for k in keys]))  # final: all items
    sc = [k for k in rk if "shortcut" in ans[k]]
    flag = [jj.is_shortcut(ans[k]["shortcut"]) for k in sc]
    dsf = [bool(ds[k[0]][k[1]]["shortcut"]) for k in sc]
    L += ["", f"Shortcut stage (answers that pass the gate): DeepSeek flags {sum(dsf)}, 27B catches "
          f"{sum(a and b for a, b in zip(dsf, flag))}, extra flags {sum(b and not a for a, b in zip(dsf, flag))}.",
          f"Label probability mass: median {st.median(a['mass'] for k in ans for p in ans[k].values() for a in p.values()):.3f}."]
    CAL.write_text(json.dumps({"version": "qwen27b-eval-v1", "model": "Qwen/Qwen3.8-27B", "created": "2026-10-06",
                               "description": "Cutoffs on the 27B judge's probability-weighted level (see qwen_judging.py), "
                                              "fitted as in calibration-v1.json on the same samples.",
                               "cutoffs": cut}, indent=1))
    (OUT / "report.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def cmd_score(a):
    """Calibrated judged-scores from the raw 27B records of eval dirs (no model call)."""
    cut = jj._cutoffs(CAL, "Qwen/Qwen3.8-27B")
    for d in map(Path, a.dirs):
        meta = json.loads((d / "metadata.json").read_text())
        rows = ({r["uid"]: r for r in rows_for("test", ("judge", "reconstruct"))} if meta["split"] == "test" else
                {r["uid"]: r for t in ("judge", "reconstruct") for r in __import__("anlp_project.opd", fromlist=["x"]).slice_rows(t, "dev")})
        texts = {x["uid"]: x["text"] for x in map(json.loads, (d / "responses.jsonl").open())}
        recs = {r["uid"]: r for r in map(json.loads, (d / "judgments.qwen.jsonl").open()) if r.get("ok")}
        items = [{**jj.score_record(rows[u], texts[u], r, cut), "judge": "qwen27b-eval-v1"} for u, r in recs.items()]
        with (d / "judged-scores.qwen.jsonl").open("w") as fh:
            for it in items:
                fh.write(json.dumps(it, ensure_ascii=False) + "\n")
        print(f"{d}: {len(items)} judged answers; missing {sum(1 for u in texts if u in rows and rows[u]['task'] != 'solve' and u not in recs)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    sub.add_parser("fit")
    sc = sub.add_parser("score")
    sc.add_argument("dirs", nargs="+")
    a = ap.parse_args()
    {"build": cmd_build, "fit": cmd_fit, "score": cmd_score}[a.cmd](a)


if __name__ == "__main__":
    main()
