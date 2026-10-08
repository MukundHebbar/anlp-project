"""Jev (TypeSafe System One, jev-1.13.0) judge for stored JUDGE and RECONSTRUCT responses.

Pipeline per answer (validated against the saved DeepSeek V4.1 Flash scores on 500-answer samples;
artifacts/jev-recon-v2/fixes-report.md, staged-report.md):

JUDGE
1. Strict gate (strict_gates.judge_gate): several decisions or steps, or a contradictory block -> score 0.
2. V and L from the deterministic parser (exact once hedged answers are gated).
3. Jev E (only when V = 4) and Jev M (always, as in the rubric), M with the teacher's reference solution in
   the state. Both are probability-weighted levels mapped through data/jev-eval/calibration-v1.json.
RECONSTRUCT
1. The LAST JSON object in the response (baseline.extract_reconstruction_last); none -> unusable.
2. Strict gate (strict_gates.reconstruct_gate): answer in the question, monologue, no question -> score 0.
3. Stage 1, few-shot shortcut check on (final answer, question) only -> score 0 on a shortcut.
4. Jev P, T (fidelity: source vs candidate) and E, M (validity: answer, observations, response), calibrated.
Score: 6.25 * (sum of the four levels); score_weighted uses the uncalibrated expectations (finer ranking).

Every Jev call is stored with its request and response in judgments.jev.jsonl; finished answers are never
re-requested. A failed call is recorded and the answer stays unresolved; nothing is guessed.
"""

from __future__ import annotations

import json
import os
import statistics
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .baseline import extract_reconstruction_last, parse_judge_response
from .paths import ENV_FILE
from .strict_gates import judge_gate, reconstruct_gate

API = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"  # pinned: the calibration is only valid for this version
PRICE_PER_TOKEN = 0.042 / 1_000_000
CALIBRATION = Path(__file__).resolve().parents[2] / "data" / "jev-eval" / "calibration-v1.json"
MAX_CHARS = 40_000  # LaTeX-dense text runs ~2 chars/token; Jev allows 32k tokens for state + longest question
JUDGE_NAME = "jev-eval-v1"


def score_q(instructions, levels):
    return {"type": "score", "instructions": instructions, "criteria": levels}


def noul_q(instructions, true, false):
    return {"type": "noul", "instructions": instructions, "criteria": {"true": true, "false": false}}


def choice_q(instructions, options):
    return {"type": "choice", "instructions": instructions, "criteria": options}


# ------------------------------------------------------------------------------------------- JUDGE

def judge_e_question(label: str) -> dict:
    if label == "incorrect":
        return score_q(
            "How well does `student_response` explain the mathematical error described in `answer_key.explanation`? "
            "A different but mathematically valid account of the SAME error counts.",
            ["The student explains a different error, gives no explanation, or gives an explanation unrelated to the key's error.",
             "The student points at the right step but for a wrong or irrelevant reason.",
             "The student's explanation is partly related to the key's error but misses its essence.",
             "The student explains the same error as the key, with a minor imprecision or omission.",
             "The student explains precisely the same mathematical error as the key."])
    return score_q(
        "The answer key says the proposed solution is correct. How well does `student_response` justify that the solution holds?",
        ["The student gives no justification or an invalid reason.",
         "The student gives only a vague justification such as 'all steps are fine', which is not wrong but not concrete.",
         "The student gives a concrete, valid reason the solution holds, such as checking the decisive step or the answer."])


JUDGE_M = score_q(
    "Score M (mathematical soundness) of `student_response`: are the student's OWN mathematical claims true? "
    "Check each claim against `answer_key.explanation` and `answer_key.reference_response`, which are correct. "
    "Score what the student asserts, independently of whether its decision is right. A correct decision does "
    "not excuse a false explanation. Saying only 'step S3 is wrong' with no mathematical content is not a "
    "substantive claim.",
    ["Essentially false, circular, or no substantive mathematical claim.",
     "Mostly false reasoning.",
     "A false claim alongside some correct reasoning.",
     "A minor inaccuracy that does not affect the judgment.",
     "No false claims."])


def judge_state(row: dict[str, Any], text: str, with_reference: bool) -> dict:
    key = row["private"]
    state = {"problem": row["public"]["problem"],
             "proposed_solution": [{"step": s["step_id"], "text": s["text"]} for s in row["public"]["proposed_solution"]],
             "answer_key": {"label": key["label"], "first_wrong_step": key["first_error_step_id"] or "none",
                            "explanation": key["first_error_explanation"], "error_type": key["error_type"]},
             "student_response": clip(text or "(empty response)")}
    if with_reference:
        state["answer_key"]["reference_response"] = key["teacher_target_response"]
    return state


def judge_requests(row, text) -> dict[str, tuple[dict, dict]]:
    decision, _ = parse_judge_response(text)
    reqs = {"M": (judge_state(row, text, True), {"M": JUDGE_M})}
    if decision == row["private"]["label"]:  # E is 0 by the rubric when the verdict is wrong
        reqs["E"] = (judge_state(row, text, False), {"E": judge_e_question(row["private"]["label"])})
    return reqs


# ------------------------------------------------------------------------------------- RECONSTRUCT

SHORTCUT_DEFINITIONS = {
    "answer-copy tautology": "`question` explicitly states the value of the SAME quantity it asks to find. This "
                             "includes a line such as 'Answer: X' inside the question. Merely containing the number "
                             "somewhere is not enough, and using it as an input for a DIFFERENT unknown is not a shortcut.",
    "copy-only restatement": "`question` is a direct request to repeat `final_answer`, with nothing to work out.",
    "no usable question": "`question` contains no identifiable mathematical request at all, for example it is only "
                          "the writer's musing, drafts or self-corrections that never settle on a request.",
    "not a shortcut": "Everything else, including questions that are wrong, underdetermined, ask for a different "
                      "unknown, or are surrounded by some commentary but still contain a clear mathematical request.",
}

# Written for this judge; none is taken from the FINAL-v3 data.
SHORTCUT_EXAMPLES = [
    {"final_answer": "6", "question": "A rectangle has longer side 6. What is its longer side?",
     "label": "answer-copy tautology", "why": "It gives the longer side as 6 and asks for the longer side."},
    {"final_answer": "13", "question": "Find the remainder when 2^100 is divided by 17.\nAnswer: 13.",
     "label": "answer-copy tautology", "why": "The question field itself states the answer to its own request."},
    {"final_answer": "24", "question": "Let N = 24 be the number of arrangements. How many arrangements are there?",
     "label": "answer-copy tautology", "why": "It states the requested count as a premise."},
    {"final_answer": "x^2 + 1", "question": "What is x^2 + 1?",
     "label": "copy-only restatement", "why": "It only asks to repeat the supplied expression."},
    {"final_answer": "2", "question": "Maybe it is an integral? No. Perhaps a sum of roots... the observations "
     "mention 0.8, so maybe a probability. Hard to say; the answer is probably 2.",
     "label": "no usable question", "why": "It never settles on a mathematical request."},
    {"final_answer": "6", "question": "A rectangle has perimeter 20 and longer side 6. Find its area.",
     "label": "not a shortcut", "why": "6 is an input for a different unknown (the area, 24)."},
    {"final_answer": "6", "question": "A rectangle has perimeter 20. Find its longer side.",
     "label": "not a shortcut", "why": "Underdetermined, but it does not state the requested value."},
    {"final_answer": "43", "question": "Find the last two digits of 7^343.",
     "label": "not a shortcut", "why": "A substantive request; containing no answer, it must be worked out."},
    {"final_answer": "5", "question": "I think the clues point to modular arithmetic, so let me pose it this way. "
     "Find the smallest positive integer n such that 3^n leaves remainder 5 when divided by 7.",
     "label": "not a shortcut", "why": "Some commentary, but a clear request that does not state its answer."},
    {"final_answer": "Yes", "question": "Is every group of prime order cyclic?",
     "label": "not a shortcut", "why": "A yes/no request that must be decided; it does not state the answer."},
]

SHORTCUT_QUESTIONS = {
    "shortcut_type": choice_q(
        {"definitions": SHORTCUT_DEFINITIONS, "labelled_examples": SHORTCUT_EXAMPLES,
         "question": "Which label from `definitions` applies to `question`, given `final_answer`? "
                     "Judge only the question field. Follow the labelled examples."},
        {label: SHORTCUT_DEFINITIONS[label] for label in
         ("not a shortcut", "answer-copy tautology", "copy-only restatement", "no usable question")}),
    "states_value": noul_q(
        "Does `question` itself already state the value of the quantity it asks to find, for example a line such as "
        "'Answer: ...' or a premise that gives the requested value directly?",
        "The question states the value of the very quantity it asks for.",
        "The question does not state the value it asks for."),
    "repeats_answer": noul_q(
        "Does `question` merely ask to repeat or restate `final_answer`, for example 'What is X?' where X is written "
        "exactly as `final_answer`, with nothing to compute?",
        "The question only asks to repeat the supplied answer.",
        "The question asks for something that has to be worked out."),
}

FIDELITY_QUESTIONS = {
    "P": score_q(
        "Compare the premises of `candidate_question` with those of `original_question`: objects, given conditions, "
        "parameters, domains and quantifiers. Cosmetic renaming and reparameterizations with a valid correspondence "
        "count as equivalent. The candidate must state its own premises; do not assume conditions it leaves out.",
        ["The candidate's setup has no meaningful correspondence with the original's.",
         "The candidate shares objects or topic with the original, but its essential setup is largely different.",
         "The candidate keeps important structure of the original, but at least one essential premise or parameter is missing or changed.",
         "The candidate keeps most of the original setup, with one localized material error or omission.",
         "The candidate's objects, premises, parameters, domains and quantifiers are equivalent to the original's."]),
    "T": score_q(
        "Compare what `candidate_question` asks to find with what `original_question` asks to find. Judge only the "
        "requested quantity, event or direction; missing input parameters are judged elsewhere. Asking for a "
        "different unknown is not equivalent even if an inverse calculation links them.",
        ["The candidate asks for nothing identifiable, or for something unrelated to the original's target.",
         "The candidate asks about related objects but a fundamentally different result.",
         "The candidate asks for a quantity of the same family as the original but a different quantity, event or direction.",
         "The candidate asks for the same quantity as the original with a limited material error in scope or qualification.",
         "The candidate asks for a mathematically equivalent target to the original's."]),
    "equivalent": noul_q(
        "Do `candidate_question` and `original_question` pose the same mathematical problem, up to renaming and "
        "equivalent reformulation, with the same essential premises AND the same requested target?",
        "Same essential premises and same requested target.",
        "Some essential premise or the requested target differs."),
}

VALIDITY_QUESTIONS = {
    "E": score_q(
        "Consider each numbered item in `observations`. How well does the student's reconstructed question "
        "(`response.question`) and explanation fit and use ALL of the observations? Mentioning an observation is "
        "not the same as grounding it.",
        ["The response ignores the observations or predominantly contradicts them.",
         "The response mentions observations without any usable connection to its question.",
         "The response substantively uses some observations but leaves important gaps or conflicts.",
         "Every observation is connected to the reconstruction, with one limited unsupported link.",
         "Every observation substantively fits one coherent reconstruction, and the links are explained."]),
    "M": score_q(
        "Is `response.question`, read on its own, a well-posed mathematical question whose answer is exactly "
        "`final_answer`, and does `response.justification` soundly verify that? Premises that appear only in the "
        "assumptions or justification do not count as part of the question. A correct final value does not excuse "
        "a false claim. A justification that only restates the supplied answer is not verification.",
        ["There is no meaningful verification, or the justification only restates the answer or is circular.",
         "The attempt is substantive but the answer is wrong for the question, the question is ill-posed or underdetermined, or an essential mathematical claim is false.",
         "The reasoning is plausible but an essential step of the proof or calculation is missing, so correctness is not established.",
         "The question is well posed, its answer is the supplied answer, and the argument is sound except for a minor omitted step.",
         "The question is well posed, its answer is the supplied answer, and the verification is complete and sound."]),
}


def is_shortcut(answers: dict) -> bool:
    return (answers["shortcut_type"]["probabilities"]["not a shortcut"] < 0.5
            or answers["states_value"]["noul"] > 0.5 or answers["repeats_answer"]["noul"] > 0.5)


def reconstruct_states(row, response) -> dict[str, dict]:
    clues = row["public_input"]["clues"]
    resp = {"assumptions": response.get("assumptions"), "question": response["question"],
            "justification": response.get("justification")}
    return {"shortcut": {"final_answer": row["public_input"]["final_answer"], "question": response["question"]},
            "fidelity": {"original_question": row["question"], "candidate_question": response["question"]},
            "validity": {"final_answer": row["public_input"]["final_answer"],
                         "observations": [f"{i}. {c}" for i, c in enumerate(clues, 1)], "response": resp}}


# -------------------------------------------------------------------------------------- transport

def clip(text: str) -> str:
    if len(text) <= MAX_CHARS:
        return text
    head = MAX_CHARS // 4
    return text[:head] + "\n[... middle of the response omitted for length ...]\n" + text[-(MAX_CHARS - head):]


def api_key() -> str:
    key = os.getenv("JEV_KEY")
    if key:
        return key
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("JEV_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    raise RuntimeError("Set JEV_KEY in the environment or .env")


class Jev:
    def __init__(self):
        self.key = api_key()
        self.lock = threading.Lock()
        self.tokens = 0

    def call(self, state: dict, questions: dict) -> dict:
        body = json.dumps({"model": MODEL, "state": state, "questions": questions}).encode()
        for attempt in range(6):
            req = urllib.request.Request(API, data=body, method="POST", headers={
                "Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    out = json.loads(r.read())
                with self.lock:
                    self.tokens += out.get("usage", {}).get("input_tokens", 0)
                return out
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:300]
                if e.code in (429, 500, 502, 503, 520, 529) and attempt < 5:
                    time.sleep(float(e.headers.get("retry-after") or 2 ** attempt))
                    continue
                raise RuntimeError(f"HTTP {e.code}: {detail}") from None
            except (urllib.error.URLError, TimeoutError):
                if attempt == 5:
                    raise
                time.sleep(2 ** attempt)


# ------------------------------------------------------------------------------------ calibration

def _cutoffs(path: Path = CALIBRATION, model: str = MODEL) -> dict[str, list[float]]:
    data = json.loads(Path(path).read_text())
    if data["model"] != model:
        raise RuntimeError(f"calibration is for {data['model']}, not {model}")
    return data["cutoffs"]


def level(weighted: float, cutoffs: list[float]) -> int:
    return sum(weighted >= c for c in cutoffs)


# ------------------------------------------------------------------------------------ per answer

def judge_answer(row: dict, text: str, jev: Any, cut: dict | None) -> dict:
    """Score one JUDGE answer. Returns (record for judgments.jev.jsonl)."""
    gate = judge_gate(text)
    rec = {"task": "judge", "gate": gate, "calls": {}}
    if gate:
        return rec
    for name, (state, qs) in judge_requests(row, text).items():
        rec["calls"][name] = {"answers": jev.call(state, qs)["answers"]}
    return rec


def reconstruct_answer(row: dict, text: str, jev: Any, cut: dict | None) -> dict:
    response, method = extract_reconstruction_last(text)
    rec = {"task": "reconstruct", "extraction": method, "calls": {}}
    if response is None:
        rec["gate"] = ["unusable_response"]
        return rec
    rec["question"] = response["question"]
    rec["gate"] = reconstruct_gate(row["public_input"]["final_answer"], response["question"])
    if rec["gate"]:
        return rec
    states = reconstruct_states(row, response)
    stage1 = jev.call(states["shortcut"], SHORTCUT_QUESTIONS)["answers"]
    rec["calls"]["shortcut"] = {"answers": stage1}
    if is_shortcut(stage1):
        return rec
    rec["calls"]["fidelity"] = {"answers": jev.call(states["fidelity"], FIDELITY_QUESTIONS)["answers"]}
    rec["calls"]["validity"] = {"answers": jev.call(states["validity"], VALIDITY_QUESTIONS)["answers"]}
    return rec


def score_record(row: dict, text: str, rec: dict, cut: dict) -> dict:
    """judged-scores row from a stored record (no API call)."""
    out = {"uid": row["uid"], "task": row["task"], "judge": JUDGE_NAME, "gate": rec.get("gate", [])}
    if row["task"] == "judge":
        key = row["private"]
        decision, step = parse_judge_response(text)
        verdict = decision == key["label"]
        s = {"verdict_correct": verdict,
             "step_correct": verdict and step == (key["first_error_step_id"] if key["label"] == "incorrect" else "none")}
        out["label"] = key["label"]
        out["verdict_correct_strict"] = bool(s["verdict_correct"]) and not out["gate"]
        out["step_correct_strict"] = bool(s["step_correct"]) and not out["gate"]
        if out["gate"]:
            out.update(status="gated", dimensions={d: 0 for d in "VLEM"}, score_100=0.0, score_weighted=0.0)
            return out
        V = 4 if s["verdict_correct"] else 0
        L = 0 if not V else 4 if (row["private"]["label"] == "correct" or s["step_correct"]) else 0
        mw = rec["calls"]["M"]["answers"]["M"]["score"]
        ew = rec["calls"]["E"]["answers"]["E"]["score"] if "E" in rec["calls"] else 0.0
        if row["private"]["label"] == "correct" and "E" in rec["calls"]:
            ew *= 2  # the correct-label E question has three levels (0, 2, 4 on the rubric scale)
        E = level(ew, cut["judge.E"]) if V else 0
        M = level(mw, cut["judge.M"])
        out.update(status="scored", dimensions={"V": V, "L": L, "E": E, "M": M},
                   score_100=6.25 * (V + L + E + M), score_weighted=6.25 * (V + L + (ew if V else 0) + mw))
        return out
    out["extraction"] = rec.get("extraction")
    names = {"P": "premise_fidelity", "T": "target_fidelity", "E": "evidence_integration", "M": "mathematical_validity"}
    if "unusable_response" in out["gate"]:
        out.update(status="unusable_response", score_100=0.0, score_weighted=0.0, shortcut=None, semantic_equivalent=False)
        return out
    if out["gate"]:
        out.update(status="gated", score_100=0.0, score_weighted=0.0, shortcut=True, semantic_equivalent=False)
        return out
    if is_shortcut(rec["calls"]["shortcut"]["answers"]):
        out.update(status="shortcut", score_100=0.0, score_weighted=0.0, shortcut=True, semantic_equivalent=False)
        return out
    f, v = rec["calls"]["fidelity"]["answers"], rec["calls"]["validity"]["answers"]
    w = {"P": f["P"]["score"], "T": f["T"]["score"], "E": v["E"]["score"], "M": v["M"]["score"]}
    lv = {d: level(w[d], cut[f"reconstruct.{d}"]) for d in "PTEM"}
    out.update(status="scored", shortcut=False, dimensions={names[d]: lv[d] for d in "PTEM"},
               semantic_equivalent=lv["P"] == 4 and lv["T"] == 4 and f["equivalent"]["noul"] > 0.5,
               score_100=6.25 * sum(lv.values()), score_weighted=6.25 * sum(w.values()))
    return out


# --------------------------------------------------------------------------------------- driver

def run(split: str, model_key: str, limit: int = 0, workers: int = 16) -> dict[str, Any]:
    from .baseline_judging import _resolve

    directory, rows = _resolve(split, model_key)
    path = directory / "judgments.jev.jsonl"
    done = {r["uid"] for r in map(json.loads, path.open()) if r.get("ok")} if path.exists() else set()
    responses = [json.loads(l) for l in (directory / "responses.jsonl").open(encoding="utf-8")]
    todo = [r for r in responses if r["uid"] in rows and rows[r["uid"]]["task"] in ("judge", "reconstruct")
            and r["uid"] not in done][: limit or None]
    jev, cut, lock = Jev(), _cutoffs(), threading.Lock()
    counts = {"ok": 0, "error": 0}

    def work(resp):
        row = rows[resp["uid"]]
        rec = {"uid": row["uid"], "model": MODEL, "judge": JUDGE_NAME}
        try:
            fn = judge_answer if row["task"] == "judge" else reconstruct_answer
            rec.update(fn(row, resp["text"], jev, cut), ok=True)
        except Exception as exc:  # recorded, never guessed; the next run retries it
            rec.update(ok=False, error=f"{type(exc).__name__}: {exc}"[:500])
        with lock:
            counts["ok" if rec["ok"] else "error"] += 1
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, todo))
    return {**counts, "attempted_now": len(todo), "previously_done": len(done),
            "input_tokens": jev.tokens, "cost_usd": round(jev.tokens * PRICE_PER_TOKEN, 4)}


def summarize(split: str, model_key: str) -> dict[str, Any]:
    from .baseline_judging import _resolve

    directory, rows = _resolve(split, model_key)
    cut = _cutoffs()
    recs = {}
    for r in map(json.loads, (directory / "judgments.jev.jsonl").open()):
        if r.get("ok"):
            recs[r["uid"]] = r
    texts = {x["uid"]: x["text"] for x in map(json.loads, (directory / "responses.jsonl").open(encoding="utf-8"))}
    items = [score_record(rows[u], texts[u], rec, cut) for u, rec in recs.items()]
    with (directory / "judged-scores.jev.jsonl").open("w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    summary: dict[str, Any] = {"judge": JUDGE_NAME, "model": MODEL}
    for task in ("judge", "reconstruct"):
        xs = [i for i in items if i["task"] == task]
        if not xs:
            continue
        total = sum(1 for u in texts if u in rows and rows[u]["task"] == task)
        summary[task] = {"responses": total, "judged": len(xs), "missing": total - len(xs),
                         "mean_score_100": statistics.mean(i["score_100"] for i in xs),
                         "status": {s: sum(i["status"] == s for i in xs) for s in sorted({i["status"] for i in xs})},
                         "gate_rules": {g: sum(g in i["gate"] for i in xs) for g in sorted({g for i in xs for g in i["gate"]})}}
        if task == "judge":
            summary[task]["verdict_accuracy_strict"] = statistics.mean(i["verdict_correct_strict"] for i in xs)
        else:
            summary[task]["semantic_equivalent"] = sum(bool(i.get("semantic_equivalent")) for i in xs)
    (directory / "judged-summary.jev.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary
