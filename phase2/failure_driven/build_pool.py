"""Build the pilot's SOLVE question pool from the JUDGE dataset's train questions.

Each JUDGE-train question already has a final answer (SOLVE reward), three reference solutions (RECONSTRUCT
conversion) and a verified JUDGE item, so a failed question needs no JUDGE generator. The 3,600 JUDGE-train
questions share no question with SOLVE-train, SOLVE dev or SOLVE test.

Pool: 768 questions = 24 steps x 32, sampled per (broad topic, difficulty) cell in proportion to cell size
(largest remainder), then put in one seeded order.
- round 1 (shared, steps 1-8): the first 256.
- arm A (steps 9-24): the next 512, 32 SOLVE per step.
- arm B (steps 9-24): the first 384 of those 512, 24 SOLVE per step, plus 8 auxiliary prompts per step (built
  later from the failure buffer).

Writes phase2/failure_driven/data/:
- pool.json: the order, the judge uid of each question, the seed and the counts.
- solve_rows.jsonl: SOLVE-format answer-key rows (uid solvej-<DeepMath row>) for opd_train's extra_reward_rows.
- prompts-r1.jsonl, prompts-A.jsonl: {uid, prompt, task, final_answer} for opd_run --prompts-file.
"""

from __future__ import annotations

import collections
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from anlp_project.baseline import load_rows, render_prompt  # noqa: E402
from anlp_project.reconstruct_sources import normalize_option_answer  # noqa: E402

SEED = "fd-pool-v1"
STEPS, PER_STEP, ROUND1_STEPS = 24, 32, 8
OUT = Path(__file__).resolve().parent / "data"
SOLVE_FIELDS = ("dataset_row_index", "source_group_id", "topic", "broad_topic", "difficulty", "difficulty_band",
                "question", "final_answer", "answer_normalization")


def solve_row(j: dict) -> dict:
    row = {"task": "solve", "split": "train", "uid": f"solvej-{j['dataset_row_index']}",
           **{k: j[k] for k in SOLVE_FIELDS}, "source": {"from_judge_uid": j["uid"], **j["source"]}}
    # As for FINAL-v3 SOLVE (answer_normalization): a bare option label whose option is listed in the question becomes
    # the option text, so checker v3 can compare it. Labels it cannot resolve stay as they are.
    try:
        norm = normalize_option_answer(row)
    except ValueError:
        return row
    if norm["final_answer"] != row["final_answer"]:
        row["answer_normalization"] = {"original_final_answer": row["final_answer"], "rule": "normalize_option_answer"}
        row["final_answer"] = norm["final_answer"]
    return row


def stratified(rows: list[dict], n: int, rng: random.Random) -> list[dict]:
    cells = collections.defaultdict(list)
    for r in sorted(rows, key=lambda r: r["uid"]):
        cells[(r["broad_topic"], r["difficulty"])].append(r)
    quota = {c: n * len(v) / len(rows) for c, v in cells.items()}
    take = {c: int(q) for c, q in quota.items()}
    for c in sorted(cells, key=lambda c: (-(quota[c] - take[c]), c))[:n - sum(take.values())]:
        take[c] += 1
    out = []
    for c in sorted(cells):
        out += rng.sample(cells[c], take[c])
    return out


def main() -> None:
    judge = load_rows("judge", "train")
    rng = random.Random(SEED)
    picked = stratified(judge, STEPS * PER_STEP, rng)
    rng.shuffle(picked)
    rows = [solve_row(j) for j in picked]
    assert len({r["uid"] for r in rows}) == len(rows)
    OUT.mkdir(exist_ok=True)
    with open(OUT / "solve_rows.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    prompts = [{"uid": r["uid"], "prompt": render_prompt(r), "task": "solve", "final_answer": r["final_answer"]}
               for r in rows]
    cut = ROUND1_STEPS * PER_STEP
    for name, part in (("prompts-r1.jsonl", prompts[:cut]), ("prompts-A.jsonl", prompts[cut:])):
        with open(OUT / name, "w") as fh:
            for p in part:
                fh.write(json.dumps(p, ensure_ascii=False) + "\n")
    labels = collections.Counter(j["label"] for j in picked)
    (OUT / "pool.json").write_text(json.dumps({
        "seed": SEED, "uids": [r["uid"] for r in rows], "judge_uid": {r["uid"]: j["uid"] for r, j in zip(rows, picked)},
        "round1": [r["uid"] for r in rows[:cut]], "armA": [r["uid"] for r in rows[cut:]],
        "armB_solve": [r["uid"] for r in rows[cut:cut + (STEPS - ROUND1_STEPS) * 24]],
        "counts": {"topic": collections.Counter(r["broad_topic"] for r in rows),
                   "difficulty": collections.Counter(str(r["difficulty"]) for r in rows),
                   "judge_label": labels}}, indent=1))
    print(f"{len(rows)} questions; labels of their JUDGE items {dict(labels)}; wrote {OUT}")


if __name__ == "__main__":
    main()
