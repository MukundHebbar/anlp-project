"""Strict rule gates applied before any judge or reward. A failed gate scores 0; no model is asked.

Each gate returns the list of rules a response breaks (empty = passes). The rules are deliberately strict:
they target answers that game a judge or a parser, not mathematical quality, which the judges score.

RECONSTRUCT (on the extracted ``question`` field, math spans removed for the word rules):
- no_question: empty or under 20 characters, or no request (no "?" and no task verb).
- answer_in_question: an "Answer:" / "the answer is" line, or the supplied final answer written in the question.
- monologue: first-person drafting, self-corrections ("No.", "Wait", "Maybe"...), or meta words
  (JSON, prompt, observations, clues, reconstruct) or field labels ("Question:", "Justification:").
Format flag, reported but not zeroed (the graded question can still be clean):
- several_drafts: the response holds more than one different "question" value.
JUDGE: several_decisions / several_steps (different values), or decision_step_mismatch
(``correct`` with a wrong step, or ``incorrect`` with ``none``).
SOLVE: several_answers: ``<final_answer>`` tags that are not all equivalent.
"""

from __future__ import annotations

import re

MATH = re.compile(r"\$\$.*?\$\$|\$[^$]*\$|\\\(.*?\\\)|\\\[.*?\\\]", re.S)
ANSWER_LINE = re.compile(r"(?im)(^|[.!?]\s+|\n)\s*[*_\"']*\s*(final\s+)?answer\s*[*_\"']*\s*[:=]|\bthe\s+(final\s+)?answer\s+(is|=|would be)\b")
# A bare "I" is a common symbol (identity matrix, integral), so only first-person phrases count.
FIRST_PERSON = re.compile(r"\b(I'm|I'll|I've|I'd|I think|I guess|I need|I will|I can|I believe|I would|I am|my|let's|let me|we'll try|let us try)\b")
DRAFTING = re.compile(r"(?m)(^|[.!?]\s+|\n)\s*(No[.,!]|Wait\b|Hmm\b|Actually\b|Maybe\b|Perhaps\b|Or better\b|Alternatively\b|Hold on\b|Oops\b|Let's\b)", re.I)
META = re.compile(r"\b(JSON|the prompt|the (given |supplied )?(observations|clues)|observation\s*#?\d|clue\s*#?\d|reconstruct\w*|"
                  r"the supplied answer|the given answer|the final answer)\b", re.I)
LABEL = re.compile(r"(?im)(^|[.!?]\s+)\s*[*_\"']*\s*(question|justification|reason|reasoning|assumptions?|observations?|solution|verification)\s*[*_\"']*\s*:")
REQUEST = re.compile(r"\?|\b(find|compute|determine|evaluate|calculate|prove|show|give|express|simplify|solve|"
                     r"what|which|how|is|are|does|do|can|list|count|decide|estimate|approximate)\b", re.I)
QUESTION_FIELD = re.compile(r'"question"\s*:\s*"((?:\\.|[^"\\])*)"', re.S)
TRIVIAL_ANSWERS = {"yes", "no", "true", "false"}


def _norm(s: str) -> str:
    s = s.replace("\\dfrac", "\\frac").replace("\\tfrac", "\\frac").replace("\\left", "").replace("\\right", "")
    return re.sub(r"[\s$]|\\[,;!]", "", s).lower()


def _answer_written(final_answer: str, question: str) -> bool:
    """The supplied answer appears verbatim (after normalization) in the question. Short integers and yes/no
    answers are too common to count; they are caught by the answer-line rule instead."""
    a = _norm(final_answer)
    if not a or a in TRIVIAL_ANSWERS or re.fullmatch(r"[a-z]+", a):  # plain words ("alice") recur in setups
        return False
    if re.fullmatch(r"-?\d+", a):
        if len(a.lstrip("-")) < 3:
            return False
        return re.search(rf"(?<![\d.]){re.escape(a)}(?![\d.])", _norm(question)) is not None
    return len(a) >= 3 and a in _norm(question)


def reconstruct_gate(final_answer: str, question: str | None, response_text: str = "") -> list[str]:
    q = (question or "").strip()
    words = MATH.sub(" ", q)
    out = []
    if len(q) < 20 or not REQUEST.search(words):
        out.append("no_question")
    if ANSWER_LINE.search(q) or _answer_written(final_answer, q):
        out.append("answer_in_question")
    if FIRST_PERSON.search(words) or DRAFTING.search(words) or META.search(words) or LABEL.search(q):
        out.append("monologue")
    return out


def reconstruct_format_flags(response_text: str) -> list[str]:
    drafts = {re.sub(r"\s+", " ", m).strip() for m in QUESTION_FIELD.findall(response_text or "")}
    return ["several_drafts"] if len(drafts) > 1 else []


DECISION = re.compile(r"Decision:\s*[*_`]*\s*(correct|incorrect)\b", re.I)
STEP = re.compile(r"First wrong step:\s*[*_`]*\s*(S\d+|none)\b", re.I)


def judge_gate(text: str) -> list[str]:
    decisions = {d.lower() for d in DECISION.findall(text or "")}
    steps = {s.lower() for s in STEP.findall(text or "")}
    out = []
    if len(decisions) > 1:
        out.append("several_decisions")
    if len(steps) > 1:
        out.append("several_steps")
    if len(decisions) == 1 and len(steps) == 1:
        d, s = next(iter(decisions)), next(iter(steps))
        if (d == "correct") != (s == "none"):
            out.append("decision_step_mismatch")
    return out


FINAL = re.compile(r"<final_answer>\s*(.*?)\s*</final_answer>", re.S | re.I)


def solve_gate(text: str) -> list[str]:
    from .solution_verification import compare_answer_detailed

    answers = list(dict.fromkeys(_norm(a) for a in FINAL.findall(text or "") if a.strip()))
    if len(answers) < 2:
        return []
    raw = [a for a in dict.fromkeys(a.strip() for a in FINAL.findall(text) if a.strip())]
    first = raw[0]
    same = all(compare_answer_detailed(first, other)["answer_status"] == "correct" for other in raw[1:])
    return [] if same else ["several_answers"]
