#!/usr/bin/env python3
"""Choose each Dr. GRPO arm's checkpoint on its OWN dev slice, by the rule fixed in the plan
(docs/plans/2026-10-06-dr-grpo-plan.md §3): steps 26, 52, 78, 104; best own-task dev score; ties -> later step.

    python3 scripts/select_dev_checkpoint.py artifacts/opd/evals/v3-drgrpo-dev

The directory holds <task>-step<k>/ eval folders (eval_matrix.py layout: s0 ... s<K-1>). Metrics:
- SOLVE: strict accuracy, mean over the samples (4).
- JUDGE: strict verdict accuracy + strict first-wrong-step accuracy on incorrect-label questions (1 sample).
- RECONSTRUCT: Jev score_100 on sample 0 (scored here if s0/judged-scores.jev.jsonl is missing; ~$0.06 per
  checkpoint). Jev is the training-time judge; the test sets use the 27B.
Writes <dir>/selection.json.
"""

import json
import statistics as st
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anlp_project import jev_judging as jj  # noqa: E402
from anlp_project.opd import slice_rows  # noqa: E402

STEPS = (26, 52, 78, 104)


def load(p):
    return [json.loads(l) for l in p.open()] if p.exists() else []


def solve_metric(d):
    by = {}
    for s in sorted(d.glob("s*")):
        for x in load(s / "scores.jsonl"):
            if x["task"] == "solve":
                by.setdefault(x["uid"], []).append(x["correct_strict"])
    return st.mean(st.mean(v) for v in by.values()), len(by)


def judge_metric(d):
    xs = [x for x in load(d / "s0" / "scores.jsonl") if x["task"] == "judge"]
    verdict = st.mean(x["verdict_correct_strict"] for x in xs)
    step = st.mean(x["step_correct_strict"] for x in xs if x["label"] == "incorrect")
    return verdict + step, len(xs)


def reconstruct_metric(d):
    s0 = d / "s0"
    path = s0 / "judged-scores.jev.jsonl"
    if not path.exists():
        rows = {r["uid"]: r for r in slice_rows("reconstruct", "dev")}
        resp = [x for x in load(s0 / "responses.jsonl") if x["uid"] in rows]
        jev, cut = jj.Jev(), jj._cutoffs()

        def work(x):
            rec = jj.reconstruct_answer(rows[x["uid"]], x["text"], jev, cut)
            return jj.score_record(rows[x["uid"]], x["text"], rec, cut)

        with ThreadPoolExecutor(16) as pool:
            out = list(pool.map(work, resp))
        with path.open("w") as fh:
            for o in out:
                fh.write(json.dumps(o, ensure_ascii=False) + "\n")
        print(f"  Jev on {d.name}: ${jev.tokens * jj.PRICE_PER_TOKEN:.3f}")
    xs = load(path)
    return st.mean(x["score_100"] for x in xs), len(xs)


METRIC = {"solve": solve_metric, "judge": judge_metric, "reconstruct": reconstruct_metric}


def main():
    base = Path(sys.argv[1])
    selection = {}
    for task in ("solve", "judge", "reconstruct"):
        scores = {}
        for k in STEPS:
            d = base / f"{task}-step{k}"
            if (d / "s0" / "scores.jsonl").exists():
                scores[k] = METRIC[task](d)
        if not scores:
            continue
        best = max(scores, key=lambda k: (round(scores[k][0], 6), k))  # ties -> later step
        selection[task] = {"selected_step": best, "dev_scores": {str(k): v[0] for k, v in scores.items()},
                           "n": {str(k): v[1] for k, v in scores.items()}}
        print(task, {k: round(v[0], 4) for k, v in scores.items()}, "-> step", best)
    (base / "selection.json").write_text(json.dumps({"rule": "best own-task dev score among steps 26/52/78/104; "
                                                             "ties -> later step", **selection}, indent=1) + "\n")


if __name__ == "__main__":
    main()
