"""Grade attempts and group them by answer (CPU, local).

    PYTHONPATH=src python phase3/grade.py --set test --attempts runs/attempts --out runs/graded

correct = the project's SOLVE reward (finished, strict gates pass, answer matches the key; checker v3).
group   = answer cluster within a question: identical normalised strings first, then checker equivalence between
          cluster representatives. Unanswered attempts (cut off or no extractable answer) get group -1.
"""

import argparse
import json
from pathlib import Path

import common
from anlp_project.rewards import solve_reward
from anlp_project.solution_verification import compare_answer_detailed, normalize_answer


def same(a: str, b: str) -> bool:
    return compare_answer_detailed(a, b)["answer_status"] == "correct"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--attempts", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = common.rows_by_uid()
    atts = [json.loads(line) for f in sorted((Path(a.attempts) / a.set).glob("[0-9][0-9][0-9].jsonl")) for line in f.open()]
    by_q: dict[str, list] = {}
    for att in atts:
        by_q.setdefault(att["uid"], []).append(att)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    n_correct = 0
    with (out / f"{a.set}.jsonl").open("w") as fh:
        for uid, group in by_q.items():
            row = rows[uid]
            reps: list[tuple[str, int]] = []      # (representative answer, group id)
            by_norm: dict[str, int] = {}
            for att in sorted(group, key=lambda x: x["k"]):
                ans = common.baseline.extract_solve_answer(att["text"])[0] if att["finish_reason"] == "stop" else None
                correct = solve_reward(row, att["text"], att["finish_reason"]) == 1.0
                gid = -1
                if ans is not None:
                    norm = normalize_answer(ans)
                    if norm in by_norm:
                        gid = by_norm[norm]
                    else:
                        gid = next((g for rep, g in reps if same(rep, ans)), len(reps))
                        if gid == len(reps):
                            reps.append((ans, gid))
                        by_norm[norm] = gid
                n_correct += correct
                # answer-level truth for picking (the strict gates judge the attempt, not the answer)
                matches = ans is not None and same(row["final_answer"], ans)
                fh.write(json.dumps({"uid": uid, "k": att["k"], "finish_reason": att["finish_reason"],
                                     "tokens": att["completion_tokens"], "answer": ans, "correct": correct,
                                     "answer_matches": matches, "group": gid}, ensure_ascii=False) + "\n")
    print(f"{a.set}: {len(atts)} attempts, {len(by_q)} questions, accuracy {n_correct/len(atts):.3f}")


if __name__ == "__main__":
    main()
