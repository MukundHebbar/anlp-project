"""Cheap trace features of own attempts, and how well they separate right from wrong (CPU).

    python phase3/trace_features.py --attempts phase3/runs/main/attempts --graded phase3/runs/graded --sets dev,test

Features per attempt: length (tokens), retraction markers ("wait", "actually", "let me re-check", "mistake", ...),
guess markers ("let's assume", "most likely", "seems to be", ...), and the number of final-answer tags. Reported:
pooled AUROC and within-question AUROC (wrong attempts scored as more suspicious), with question-cluster bootstrap CIs.
These are the baselines a judge has to beat, and a direct test of the liveness account (retractions in right traces).
"""

import argparse
import json
import re
from pathlib import Path

import numpy as np

import analyze as A

RETRACT = re.compile(r"\b(wait|actually|hold on|let me re-?(check|examine|consider|do|compute|evaluate|think)|"
                     r"i made (a|an) (mistake|error)|that'?s (wrong|incorrect|not right)|on second thought|correction)\b",
                     re.I)
GUESS = re.compile(r"\b(let'?s assume|assume the answer|most likely|seems to be|i'?ll go with|probably|i guess|"
                   r"cannot determine|can'?t determine)\b", re.I)
TAG = re.compile(r"<final_answer>", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attempts", default="phase3/runs/main/attempts")
    ap.add_argument("--graded", default="phase3/runs/graded")
    ap.add_argument("--sets", default="dev,test")
    ap.add_argument("--out", default="phase3/runs/trace_features.json")
    a = ap.parse_args()
    report = {}
    for s in a.sets.split(","):
        feats = {}
        for f in sorted((Path(a.attempts) / s).glob("[0-9][0-9][0-9].jsonl")):
            for line in f.open():
                r = json.loads(line)
                t = r["text"]
                feats[(r["uid"], r["k"])] = {"length": r["completion_tokens"], "retractions": len(RETRACT.findall(t)),
                                             "guesses": len(GUESS.findall(t)), "tags": len(TAG.findall(t))}
        qs = [q for q in A.load(Path(a.graded), Path("/nonexistent"), s) if all((q["uid"], k) in feats for k in range(q["n"]))]
        rep = {"questions": len(qs)}
        for name in ("length", "retractions", "guesses", "tags"):
            for q in qs:
                q["feat"] = np.array([feats[(q["uid"], k)][name] for k in range(q["n"])], float)
            w = A.within_pairs(qs, lambda q: q["feat"])
            wc = A.within_pairs(qs, lambda q: q["feat"], contested_only=True)
            lab = np.concatenate([~q["correct"][q["answered"]] for q in qs])
            sc = np.concatenate([q["feat"][q["answered"]] for q in qs])
            right, wrong = sc[~lab], sc[lab]
            rep[name] = {"pooled_auroc": float(A.auroc(sc, lab)), "within_auroc": A.boot_ratio(w),
                         "contested_within_auroc": A.boot_ratio(wc), "mean_right": float(right.mean()),
                         "mean_wrong": float(wrong.mean()), "share_right_with_any": float((right > 0).mean()),
                         "share_wrong_with_any": float((wrong > 0).mean())}
            print(f"{s} {name:11s} pooled {rep[name]['pooled_auroc']:.3f} within {rep[name]['within_auroc'][0]:.3f} "
                  f"[{rep[name]['within_auroc'][1][0]:.3f}, {rep[name]['within_auroc'][1][1]:.3f}] contested "
                  f"{rep[name]['contested_within_auroc'][0]:.3f} | mean right {right.mean():.2f} wrong {wrong.mean():.2f} | "
                  f">0: right {(right > 0).mean():.2f} wrong {(wrong > 0).mean():.2f}")
        report[s] = rep
    Path(a.out).write_text(json.dumps(report, indent=1, default=float) + "\n")


if __name__ == "__main__":
    main()
