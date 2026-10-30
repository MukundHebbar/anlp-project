"""Shared Phase-3 pieces: question sets, prompts, own-attempt -> JUDGE step format, verdict-token scoring.

The Phase-2 self-judge code was lost, so the step conversion is rebuilt here: paragraphs of the attempt become
steps S1..Sn (display maths and very short paragraphs are merged into the step before), and the final-answer tag
becomes a last step "The final answer is X.".
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anlp_project import baseline  # noqa: E402
from anlp_project.reconstruct import render_template  # noqa: E402

SETS = ROOT / "phase3" / "manifests" / "sets.json"
JUDGE_TEMPLATE = ROOT / "data" / "prompts" / "judge" / "judge_student_p2.md"
STUDENT = "Qwen/Qwen3.5-2B"

# SOLVE attempts: protocol v2 sampling with Phase 2's 16k cap. JUDGE: Phase 2's 8,192-token judge cap.
SOLVE_SAMPLING = {"temperature": 1.0, "top_p": 1.0, "top_k": 0, "max_tokens": 16384}
JUDGE_SAMPLING = {"temperature": 1.0, "top_p": 1.0, "top_k": 0, "max_tokens": 8192}
VERDICT_LABEL = "Decision:"
JUDGE_QUESTION = ("Decide whether the proposed solution is correct. If it is incorrect, identify the first wrong "
                  "step and explain the mathematical error.")


def load_sets() -> dict[str, list[str]]:
    return json.loads(SETS.read_text())["uids"]


def rows_by_uid() -> dict[str, dict[str, Any]]:
    rows = baseline.load_rows("solve", "train") + baseline.load_rows("solve", "test")
    return {r["uid"]: r for r in rows}


def solve_prompt(row: dict[str, Any]) -> str:
    return baseline.render_prompt(row, "v2")


_FINAL_TAG = re.compile(r"<final_answer>.*?</final_answer>", re.DOTALL | re.IGNORECASE)
_DISPLAY_START = re.compile(r"^(\\\[|\$\$|\\begin\{)")


def to_steps(text: str, answer: str) -> list[str]:
    """Split an own attempt into JUDGE-style steps."""
    body = _FINAL_TAG.sub("", text).strip()
    steps: list[str] = []
    for para in (p.strip() for p in re.split(r"\n\s*\n", body)):
        if not para:
            continue
        if steps and (_DISPLAY_START.match(para) or len(para) < 40):
            steps[-1] = steps[-1] + "\n" + para
        else:
            steps.append(para)
    steps.append(f"The final answer is {answer}.")
    return steps


def judge_input(question: str, steps: list[str]) -> str:
    numbered = "\n".join(f"S{i}: {s}" for i, s in enumerate(steps, 1))
    return f"Problem:\n{question}\n\nProposed solution:\n{numbered}\n\n{JUDGE_QUESTION}"


def judge_prompt(question: str, attempt_text: str, answer: str) -> str:
    template = JUDGE_TEMPLATE.read_text(encoding="utf-8").strip()
    return render_template(template, {"JUDGE_INPUT": judge_input(question, to_steps(attempt_text, answer))})


def verdict_kind(token: str) -> str | None:
    """'incorrect' / 'correct' / None for one decoded token."""
    t = token.replace("Ġ", " ").strip().strip("*_`:").strip().lower()
    if t.startswith("incorrect"):
        return "incorrect"
    if t.startswith("correct"):
        return "correct"
    return None


def verdict_probability(positions: list[dict[str, float]]) -> tuple[float | None, int | None]:
    """P(incorrect) / (P(incorrect) + P(correct)) at the first forced position whose top tokens contain a verdict.

    ``positions`` holds, for each forced token position, {decoded token: logprob} for the top candidates.
    Returns (probability, position index), or (None, None) if no position shows a verdict token.
    """
    for i, top in enumerate(positions):
        p = {"incorrect": 0.0, "correct": 0.0}
        for tok, lp in top.items():
            kind = verdict_kind(tok)
            if kind:
                p[kind] += math.exp(lp)
        if p["incorrect"] + p["correct"] > 0:
            return p["incorrect"] / (p["incorrect"] + p["correct"]), i
    return None, None
