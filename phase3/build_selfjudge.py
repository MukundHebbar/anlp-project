"""Training prompts for the Stage-2 self-judge arms, from the `train` set's own attempts (CPU).

    PYTHONPATH=src python phase3/build_selfjudge.py --attempts runs/attempts --graded runs/graded --out runs/selfjudge

Both arms: 1,024 prompts (32 steps x 32, the Phase-2 recipe), judge prompt as in phase3/common.py, label = the
answer checker's verdict on the attempt, prompts up to 50,000 characters (Phase 2's limit) and 16,000 tokens.
  global   Phase-2 replica: every usable wrong attempt is eligible, plus as many right ones, drawn over all questions
           (globally balanced; wrong attempts from all-wrong questions included)
  perq     per-question balanced: only questions with both right and wrong attempts; each contributes equal numbers
           of right and wrong attempts, at most 4 of each (theory-and-plan.md, R7)
"""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

import common

N_PROMPTS = 1024
MAX_CHARS = 50_000
MAX_TOKENS = 16_000  # the trainer reserves 17,408 prompt tokens; 50k characters can exceed that (2026-10-29 crash)
SEED = 20261029


def token_counter():
    import glob
    from tokenizers import Tokenizer
    path = glob.glob(str(Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen3.5-2B/snapshots/*/tokenizer.json"))[0]
    tok = Tokenizer.from_file(path)
    return lambda text: len(tok.encode(text).ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attempts", required=True)
    ap.add_argument("--graded", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = common.rows_by_uid()
    texts = {}
    for f in sorted((Path(a.attempts) / "train").glob("[0-9][0-9][0-9].jsonl")):
        for line in f.open():
            r = json.loads(line)
            texts[(r["uid"], r["k"])] = r["text"]
    n_tokens = token_counter()
    by_q = defaultdict(list)
    for line in (Path(a.graded) / "train.jsonl").open():
        g = json.loads(line)
        if g["finish_reason"] != "stop" or g["answer"] is None:
            continue
        prompt = common.judge_prompt(rows[g["uid"]]["question"], texts[(g["uid"], g["k"])], g["answer"])
        if len(prompt) > MAX_CHARS or n_tokens(prompt) > MAX_TOKENS:
            continue
        by_q[g["uid"]].append({"uid": f"sj-{g['uid']}-{g['k']}", "prompt": prompt,
                               "label": "correct" if g["correct"] else "incorrect", "question": g["uid"]})
    rng = random.Random(SEED)
    wrong = [x for v in by_q.values() for x in v if x["label"] == "incorrect"]
    right = [x for v in by_q.values() for x in v if x["label"] == "correct"]
    nw = min(len(wrong), N_PROMPTS // 2)
    arms = {"global": rng.sample(wrong, nw) + rng.sample(right, N_PROMPTS - nw)}
    perq = []
    for q in sorted(by_q):
        w = [x for x in by_q[q] if x["label"] == "incorrect"]
        r = [x for x in by_q[q] if x["label"] == "correct"]
        m = min(len(w), len(r), 4)
        perq += rng.sample(w, m) + rng.sample(r, m)
    rng.shuffle(perq)
    arms["perq"] = perq[:N_PROMPTS]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, items in arms.items():
        rng.shuffle(items)
        with (out / f"{name}.jsonl").open("w") as fh:
            for x in items:
                fh.write(json.dumps(x, ensure_ascii=False) + "\n")
        qs = {x["question"] for x in items}
        print(f"{name}: {len(items)} prompts, {sum(x['label'] == 'incorrect' for x in items)} wrong, {len(qs)} questions")


if __name__ == "__main__":
    main()
