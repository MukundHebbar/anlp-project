"""GRPO rewards in [0, 1] for one rollout. A rollout that fails a strict gate or hits the cap earns 0.

- SOLVE: 1 if the single final answer matches the key (verifier v2), else 0. Unverified answers earn 0.
- JUDGE: rows marked ``verdict_only`` earn 1 for the right verdict, else 0. Otherwise 0.5 for the right verdict, 0.25 more for the right first wrong step ("none" for a correct
  solution), 0.25 more for Jev's explanation and soundness, (E + M) / 8 on the probability-weighted levels,
  when the verdict is right.
- RECONSTRUCT: the Jev pipeline's probability-weighted score / 100 (gate -> few-shot shortcut stage ->
  P/T/E/M; jev_judging), minus 0.1 for several question drafts in one response.
- REPAIR (failure-driven arm F): 0.75 for a correct corrected final answer + 0.25 for the right first wrong step.

``None`` means a Jev call failed: the caller drops the rollout from the step rather than guessing.
"""

from __future__ import annotations

from typing import Any

from . import jev_judging as jj
from .baseline import extract_solve_answer, parse_judge_response
from .solution_verification import compare_answer_detailed
from .strict_gates import judge_gate, reconstruct_format_flags, solve_gate


def solve_reward(row: dict[str, Any], text: str, finish: str) -> float:
    if finish != "stop" or solve_gate(text):
        return 0.0
    answer = extract_solve_answer(text)[0]
    return float(answer is not None and compare_answer_detailed(row["final_answer"], answer)["answer_status"] == "correct")


def judge_reward(row: dict[str, Any], text: str, finish: str, jev: jj.Jev | None) -> float | None:
    if finish != "stop" or judge_gate(text):
        return 0.0
    key = row["private"]
    decision, step = parse_judge_response(text)
    if key.get("verdict_only"):  # labels without a first-error step (e.g. the policy's own attempts): verdict only
        return float(decision == key["label"])
    if decision != key["label"]:
        return 0.0
    key_step = key["first_error_step_id"] if key["label"] == "incorrect" else "none"
    reward = 0.5 + (0.25 if step == key_step else 0.0)
    if jev is None:
        return reward
    try:
        answers = {name: jev.call(state, qs)["answers"] for name, (state, qs) in jj.judge_requests(row, text).items()}
    except Exception:
        return None
    e = answers["E"]["E"]["score"] * (2 if key["label"] == "correct" else 1)  # 3-level question for correct keys
    m = answers["M"]["M"]["score"]
    return reward + 0.25 * min(8.0, e + m) / 8


def selfjudge_reward(row: dict[str, Any], text: str, finish: str) -> float:
    """Phase-3 self-judge (own attempts, answer-checker label in ``row["label"]``): 1 for the right verdict, else 0.
    Cut-off answers and strict-gate violations earn 0. The first wrong step is not rewarded (no step labels)."""
    if finish != "stop" or judge_gate(text):
        return 0.0
    return float(parse_judge_response(text)[0] == row["label"])


def reconstruct_reward(row: dict[str, Any], text: str, finish: str, jev: jj.Jev) -> float | None:
    if finish != "stop":
        return 0.0
    try:
        rec = jj.reconstruct_answer(row, text, jev, None)
    except Exception:
        return None
    cutoffs = jev.cutoffs if hasattr(jev, 'cutoffs') else jj._cutoffs()
    out = jj.score_record(row, text, rec, cutoffs)
    penalty = 0.1 if reconstruct_format_flags(text) else 0.0
    return max(0.0, out["score_weighted"] / 100 - penalty)


def repair_reward(row: dict[str, Any], text: str, finish: str) -> float:
    """REPAIR (phase2/failure_driven arm F): the student's own failed attempt is shown; it names the first wrong step
    and writes a corrected solution. 0.75 if the corrected final answer is right (SOLVE checker and strict gate),
    + 0.25 if the named first wrong step is the key's."""
    if finish != "stop" or solve_gate(text):
        return 0.0
    _, step = parse_judge_response(text)
    answer = extract_solve_answer(text)[0]
    right = answer is not None and compare_answer_detailed(row["final_answer"], answer)["answer_status"] == "correct"
    return 0.75 * right + 0.25 * (step == row["private"]["first_error_step_id"])


def reward(task: str, row: dict[str, Any], text: str, finish: str, jev: jj.Jev | None) -> float | None:
    if task == "solve":
        return solve_reward(row, text, finish)
    if task == "repair":
        return repair_reward(row, text, finish)
    if task == "judge":
        return judge_reward(row, text, finish, jev)
    if task == "selfjudge":
        return selfjudge_reward(row, text, finish)
    return reconstruct_reward(row, text, finish, jev)
