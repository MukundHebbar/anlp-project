#!/usr/bin/env python3
"""Self-judge data: the mixed model's own SOLVE attempts on unseen training problems, labelled by the answer checker.

    gen    the mixed model (step 75) answers N FINAL-v3 SOLVE train questions it never trained on, 4 attempts each
           (16k cap). Questions: positions 750.. of the mixed run's SOLVE order (it saw the first 750); the dev slice
           is excluded by construction.
    build  keep attempts the checker calls correct or incorrect (finished, gated ones are incorrect), balance the two
           labels, and write GRPO prompts in the JUDGE format (problem + the attempt split into numbered steps) plus
           verdict-only answer-key rows (rewards.judge_reward).

    python phase2/selfjudge/build.py gen --out DIR --base <2B> --n 1200 [--shard i --nshards k]
    python phase2/selfjudge/build.py build --out DIR --steps 48 --per-step 32
"""
import argparse, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "phase2" / "scripts"))
import hint_pilot as hp  # noqa: E402
import functional as F  # noqa: E402


def gen(a):
    from anlp_project import baseline
    rows = {r["uid"]: r for r in baseline.load_rows("solve", "train")}
    order = json.loads((baseline.FINAL_V3_DIR / "grpo-mixed-1134.json").read_text())["uids"]
    seen = [u for u in order if u.startswith("solve-")][:750]
    dev = {r["uid"] for r in __import__("anlp_project.opd", fromlist=["x"]).slice_rows("solve", "dev")}
    matrix = json.loads((baseline.FINAL_V3_DIR / "opd-matrix-solve.json").read_text())["uids"]
    pool = [u for u in matrix if u not in set(seen) and u not in dev][:a.n]
    mine = pool[a.shard::a.nshards]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    eng = hp.Engine(a.base, Path(a.adapters), 20480)
    outs = eng.chat([hp.solve_prompt(rows[u]) for u in mine], "mixed", 4, 16384)
    recs = []
    for u, samples in zip(mine, outs):
        for k, s in enumerate(samples):
            sc = hp.score(rows[u], s)
            recs.append({"uid": u, "attempt": k, "problem": rows[u]["question"], "key": rows[u]["final_answer"],
                         "steps": hp.to_steps(s["text"]), "finish_reason": s["finish_reason"],
                         "answer": sc["extracted_answer"], "answer_status": sc["answer_status"], "gate": sc["gate"],
                         "correct": sc["correct_strict"], "tokens": s["completion_tokens"]})
    hp.write_jsonl(out / f"attempts-shard{a.shard}.jsonl", recs)


def build(a):
    out = Path(a.out)
    atts = hp.read_jsonl(sorted(out.glob("attempts-shard*.jsonl")))
    ok = [x for x in atts if x["finish_reason"] == "stop" and x["answer"]
          and (x["correct"] or x["answer_status"] == "incorrect")
          and len(F.judge_prompt(x["problem"], x["steps"])) <= a.max_chars]  # fits the trainer's prompt allowance
    pos = [x for x in ok if not x["correct"]]; neg = [x for x in ok if x["correct"]]  # pos = wrong attempts
    rng = random.Random(20261022)
    need = a.steps * a.per_step
    k = min(len(pos), len(neg), need // 2)
    chosen = rng.sample(pos, k) + rng.sample(neg, k)
    rng.shuffle(chosen)
    if len(chosen) < need:  # top up with more correct attempts if wrong ones run short (keeps step count fixed)
        rest = [x for x in neg if x not in chosen]
        chosen += rng.sample(rest, need - len(chosen))
    prompts, rows = [], []
    for i, x in enumerate(chosen[:need]):
        uid = f"selfjudge-{x['uid']}-{x['attempt']}"
        prompts.append({"uid": uid, "task": "judge", "prompt": F.judge_prompt(x["problem"], x["steps"])})
        rows.append({"uid": uid, "task": "judge", "split": "selfjudge", "question": x["problem"],
                     "private": {"label": "correct" if x["correct"] else "incorrect", "verdict_only": True,
                                 "first_error_step_id": None}})
    hp.write_jsonl(out / "prompts.jsonl", prompts)
    hp.write_jsonl(out / "reward_rows.jsonl", rows)
    summary = {"attempts": len(atts), "usable": len(ok), "wrong": len(pos), "right": len(neg),
               "train_prompts": len(prompts), "wrong_share_in_train": round(sum(r["private"]["label"] == "incorrect" for r in rows) / len(rows), 3),
               "solver_accuracy": round(sum(x["correct"] for x in atts) / len(atts), 3)}
    (out / "build.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["gen", "build"])
    ap.add_argument("--out", required=True); ap.add_argument("--base", default="")
    ap.add_argument("--n", type=int, default=1200); ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--max-chars", type=int, default=50000)
    ap.add_argument("--steps", type=int, default=48); ap.add_argument("--per-step", type=int, default=32)
    ap.add_argument("--adapters", default=str(Path.home() / "anlp-final-adapters"))
    a = ap.parse_args()
    {"gen": gen, "build": build}[a.stage](a)
