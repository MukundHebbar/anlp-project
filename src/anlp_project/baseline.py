"""Zero-training baselines (E0) on FINAL-v3: prompts, pilot selection and scoring.

Generation happens elsewhere (``scripts/modal_baseline.py`` runs vLLM on Modal); this
module only builds the exact prompts sent and scores the returned text
deterministically. Model-judged scores (JUDGE V/L/E/M, RECONSTRUCT P/T/E/M) are a
separate step that reads the stored responses.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any, Iterable

from .paths import ARTIFACTS_DIR, MANIFESTS_DIR, PROMPTS_DIR
from .reconstruct import parse_student_response, render_template, repair_json_backslashes
from .solution_verification import compare_answer_detailed, extract_final_answer

TASKS = ("solve", "judge", "reconstruct")
FINAL_V3_DIR = MANIFESTS_DIR / "final-v3"
PILOT_MANIFEST = FINAL_V3_DIR / "pilot-train-100.json"
BASELINE_DIR = ARTIFACTS_DIR / "baselines" / "final-v3"
PILOT_SIZE = 100
PILOT_SEED = 20260929

# Student prompts v1: every run up to the 2026-10 transfer matrix. Kept to reproduce those runs.
PROMPT_FILES_V1 = {
    "solve": PROMPTS_DIR / "solve" / "solve_no_reference.md",
    "judge": PROMPTS_DIR / "judge" / "judge_student_p1.md",
    "reconstruct": PROMPTS_DIR / "reconstruct" / "final_v1" / "student.md",
}
# Student prompts v2 (default from 2026-10-06): JUDGE ends with one final block written once (no hedging);
# RECONSTRUCT reasons before a single final JSON whose question field holds only the question; both state the
# strict-gate rules (strict_gates.py) that score violations 0. SOLVE is unchanged.
PROMPT_FILES = {
    **PROMPT_FILES_V1,
    "judge": PROMPTS_DIR / "judge" / "judge_student_p2.md",
    "reconstruct": PROMPTS_DIR / "reconstruct" / "final_v2" / "student.md",
}
PROMPT_VERSIONS = {"v1": PROMPT_FILES_V1, "v2": PROMPT_FILES}

# Protocol v1 (earlier runs): Qwen's general non-thinking defaults. Kept for the recorded runs.
SAMPLING = {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "seed": 0, "max_tokens": 8192}
# Protocol v2 (final, 2026-09-30): full distribution, matching the OPD training rollouts
# (temperature 1.0, no top-p/top-k truncation, no penalties), one sample per question, 32k cap.
EVAL_SAMPLING = {"temperature": 1.0, "top_p": 1.0, "top_k": 0, "seed": 0, "max_tokens": 32768}
PROTOCOLS = {"v1": SAMPLING, "v2": EVAL_SAMPLING}

MODELS = {
    "qwen3.5-4b": "Qwen/Qwen3.5-4B",
    "qwen3.5-2b": "Qwen/Qwen3.5-2B",
    "qwen3.8-27b": "Qwen/Qwen3.8-27B",
}


def load_rows(task: str, split: str) -> list[dict[str, Any]]:
    path = FINAL_V3_DIR / f"{task}-{split}.jsonl.gz"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def select_pilot(rows_by_task: dict[str, list[dict[str, Any]]], size: int = PILOT_SIZE,
                 seed: int = PILOT_SEED) -> dict[str, list[str]]:
    """Seeded sample of training uids per task. Test rows are never eligible."""
    selected = {}
    for task in TASKS:
        rows = rows_by_task[task]
        if any(r["split"] != "train" for r in rows):
            raise ValueError("pilot rows must come from the train split")
        uids = sorted(r["uid"] for r in rows)
        selected[task] = sorted(random.Random(f"{seed}:{task}").sample(uids, size))
    return selected


def pilot_uids() -> dict[str, list[str]]:
    """Return the frozen pilot selection, creating the manifest on first use."""
    if PILOT_MANIFEST.exists():
        return json.loads(PILOT_MANIFEST.read_text())["uids"]
    uids = select_pilot({t: load_rows(t, "train") for t in TASKS})
    PILOT_MANIFEST.write_text(json.dumps({
        "description": "Fixed train-split pilot for prompt, token-cap and headroom checks before the test baseline.",
        "seed": PILOT_SEED, "size_per_task": PILOT_SIZE, "uids": uids}, indent=1) + "\n")
    return uids


def rows_for(split: str, tasks: Iterable[str] = TASKS, limit: int = 0) -> list[dict[str, Any]]:
    """Rows for ``split`` in {"test", "pilot"}; pilot draws the frozen train sample."""
    out = []
    for task in tasks:
        if split == "pilot":
            wanted = set(pilot_uids()[task])
            rows = [r for r in load_rows(task, "train") if r["uid"] in wanted]
        elif split == "test":
            rows = load_rows(task, "test")
        else:
            raise ValueError(f"unknown split {split!r}")
        rows.sort(key=lambda r: r["uid"])
        out.extend(rows[:limit] if limit else rows)
    return out


def render_prompt(row: dict[str, Any], version: str = "v2") -> str:
    task = row["task"]
    template = PROMPT_VERSIONS[version][task].read_text(encoding="utf-8").strip()
    if task == "solve":
        return render_template(template, {"QUESTION": row["question"]})
    if task == "judge":
        return render_template(template, {"JUDGE_INPUT": row["training"]["input"]})
    clues = row["public_input"]["clues"]
    return render_template(template, {
        "FINAL_ANSWER": row["public_input"]["final_answer"],
        "RENDERED_CLUES": "\n".join(f"{n}. {c}" for n, c in enumerate(clues, 1)),
    })


def build_requests(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requests = []
    for row in rows:
        prompt = render_prompt(row)
        if row["task"] == "reconstruct" and row["question"] in prompt:
            raise ValueError(f"source question leaked into prompt for {row['uid']}")
        requests.append({"uid": row["uid"], "task": row["task"], "prompt": prompt,
                         "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()})
    return requests


def prompt_hashes() -> dict[str, str]:
    return {t: hashlib.sha256(p.read_bytes()).hexdigest() for t, p in PROMPT_FILES.items()}


# ------------------------------------------------------------------ scoring

THINK_RE = re.compile(r"</?think>", re.I)


def parse_judge_response(text: str) -> tuple[str | None, str | None]:
    """Same regex as scripts/evaluate_judge_qwen.py, so results stay comparable."""
    decision = re.search(r"Decision:\s*[*_`]*\s*(correct|incorrect)\b", text or "", re.I)
    step = re.search(r"First wrong step:\s*[*_`]*\s*(S\d+|none)\b", text or "", re.I)
    step_id = None
    if step:
        step_id = "none" if step.group(1).lower() == "none" else step.group(1).upper()
    return (decision.group(1).lower() if decision else None), step_id


_FINAL_TAG = re.compile(r"<final_answer>\s*(.*?)\s*</final_answer>", re.DOTALL | re.IGNORECASE)


def extract_solve_answer(text: str) -> tuple[str | None, str]:
    """Study rule: with several ``<final_answer>`` tags, the last non-empty one is the answer.

    The repository extractor (``extract_final_answer``) rejects multiple tags; it is kept
    unchanged for the earlier runs that depend on it and is used for every other case.
    """
    tags = [t.strip() for t in _FINAL_TAG.findall(text or "") if t.strip()]
    if len(tags) > 1:
        return tags[-1], "last_of_multiple_tags"
    return extract_final_answer(text)


def score_response(row: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Deterministic score for one stored response. Never calls a model."""
    text = response.get("text") or ""
    base = {"uid": row["uid"], "task": row["task"], "broad_topic": row["broad_topic"],
            "difficulty": row["difficulty"], "finish_reason": response.get("finish_reason"),
            "completion_tokens": response.get("completion_tokens"),
            "hit_token_cap": response.get("finish_reason") == "length",
            "think_markup": bool(THINK_RE.search(text))}
    task = row["task"]
    if task == "solve":
        answer, method = extract_solve_answer(text)
        detail = compare_answer_detailed(row["final_answer"], answer)
        return {**base, "extracted_answer": answer, "extraction": method,
                "answer_status": detail["answer_status"], "verification_method": detail["verification_method"]}
    if task == "judge":
        decision, step = parse_judge_response(text)
        key = row["private"]
        key_step = key["first_error_step_id"] if key["label"] == "incorrect" else "none"
        return {**base, "label": key["label"], "error_position": key.get("error_position"),
                "decision": decision, "first_wrong_step": step,
                "parsed": decision is not None,
                "verdict_correct": decision == key["label"],
                "step_correct": decision == key["label"] and step == key_step}
    reconstruction, method = extract_reconstruction(text)
    return {**base, "parsed": reconstruction is not None, "strict_json": method == "strict",
            "extraction": method, "off_schema": method not in ("strict", None),
            "reconstructed_question": (reconstruction or {}).get("question")}


_FIELD_RE = {f: re.compile(rf'"{f}"\s*:\s*"((?:\\.|[^"\\])*)"', re.S) for f in ("question", "justification")}


def _json_string(raw: str) -> str:
    try:
        return json.loads(f'"{raw}"')
    except json.JSONDecodeError:  # e.g. an invalid escape like \' : keep the text as written
        return raw.replace('\\"', '"')


def extract_reconstruction(text: str) -> tuple[dict[str, Any] | None, str | None]:
    """Return (response, method) for a RECONSTRUCT answer.

    ``strict``/``repaired`` come from the repository parser. ``lenient`` recovers the
    ``question`` and ``justification`` strings from JSON whose surrounding structure is
    broken (unclosed arrays, stray brackets, invalid escapes). Field contents are never
    rewritten; a response without a recoverable question returns (None, None).
    """
    try:
        value, off_schema = parse_student_response(text)
        return value, ("repaired" if off_schema else "strict")
    except (ValueError, json.JSONDecodeError):
        pass
    question = _FIELD_RE["question"].search(text or "")
    if not question or not question.group(1).strip():
        return None, None
    justification = _FIELD_RE["justification"].search(text, question.end())
    assumptions = text[: question.start()]
    return {
        "assumptions": [assumptions.split('"assumptions"', 1)[-1].strip(' :[{,"\n')] if '"assumptions"' in assumptions else [],
        "question": _json_string(question.group(1)).strip(),
        "justification": _json_string(justification.group(1)).strip() if justification else "",
    }, "lenient"


def summarize(scores: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for task in TASKS:
        rows = [s for s in scores if s["task"] == task]
        if not rows:
            continue
        n = len(rows)
        common = {"n": n, "token_cap_rate": sum(s["hit_token_cap"] for s in rows) / n,
                  "think_markup_rate": sum(s["think_markup"] for s in rows) / n,
                  "mean_completion_tokens": sum(s["completion_tokens"] or 0 for s in rows) / n}
        if task == "solve":
            status = {k: sum(s["answer_status"] == k for s in rows) for k in ("correct", "incorrect", "unverified", "missing")}
            out[task] = {**common, "accuracy": status["correct"] / n, "status_counts": status}
        elif task == "judge":
            inc = [s for s in rows if s["label"] == "incorrect"]
            out[task] = {**common, "parse_rate": sum(s["parsed"] for s in rows) / n,
                         "verdict_accuracy": sum(s["verdict_correct"] for s in rows) / n,
                         "verdict_accuracy_on_correct": _rate([s for s in rows if s["label"] == "correct"], "verdict_correct"),
                         "verdict_accuracy_on_incorrect": _rate(inc, "verdict_correct"),
                         "first_step_accuracy_on_incorrect": _rate(inc, "step_correct")}
        else:
            out[task] = {**common, "parse_rate": sum(s["parsed"] for s in rows) / n,
                         "strict_json_rate": sum(s["strict_json"] for s in rows) / n,
                         "extraction_counts": {m: sum(s["extraction"] == m for s in rows) for m in ("strict", "repaired", "lenient", None)},
                         "note": "Quality scores need the PC-v4 judges; not computed here."}
    return out


def _rate(rows: list[dict[str, Any]], key: str) -> float | None:
    return sum(r[key] for r in rows) / len(rows) if rows else None


def run_key(model_key: str, max_tokens: int = SAMPLING["max_tokens"]) -> str:
    """Folder name for a run: the model key, plus the token cap when it is not the default."""
    return model_key if max_tokens == SAMPLING["max_tokens"] else f"{model_key}-cap{max_tokens // 1024}k"


def output_dir(split: str, key: str) -> Path:
    name = "pilot-train-100" if split == "pilot" else split
    return BASELINE_DIR / name / key


def score_dir(split: str, model_key: str) -> dict[str, Any]:
    """Score ``responses.jsonl`` in an output directory and write scores + summary."""
    directory = output_dir(split, model_key)
    responses = [json.loads(l) for l in (directory / "responses.jsonl").open(encoding="utf-8")]
    rows = {r["uid"]: r for r in rows_for(split, sorted({x["task"] for x in responses}))}
    scores = [score_response(rows[x["uid"]], x) for x in responses]
    with (directory / "scores.jsonl").open("w", encoding="utf-8") as handle:
        for s in scores:
            handle.write(json.dumps(s, ensure_ascii=False) + "\n")
    summary = summarize(scores)
    (directory / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


# ------------------------------------------------------------------ strict scoring (2026-10-06)

_OBJECT_START = re.compile(r"\{\s*\"")


def extract_reconstruction_last(text: str) -> tuple[dict[str, Any] | None, str | None]:
    """The LAST complete JSON object with a non-empty ``question``: the student's final answer.

    ``extract_reconstruction`` takes the first parseable object, the first fenced block or the first
    ``"question"`` field, which grades an early draft when the response holds several, and fails when
    reasoning before the JSON contains braces. This scans object starts from the end instead. If no object
    parses, the last ``"question"`` / ``"justification"`` strings are used (method ``lenient_last``).
    """
    s = text or ""
    decoder = json.JSONDecoder()
    for match in reversed(list(_OBJECT_START.finditer(s))):
        tail = s[match.start():]
        for candidate, method in ((tail, "last_json"), (repair_json_backslashes(tail), "last_json_repaired")):
            try:
                obj, _ = decoder.raw_decode(candidate)
            except ValueError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("question"), str) and obj["question"].strip():
                assumptions = obj.get("assumptions", [])
                return {"assumptions": [str(a) for a in (assumptions if isinstance(assumptions, list) else [assumptions])],
                        "question": obj["question"].strip(),
                        "justification": str(obj.get("justification") or "").strip()}, method
    questions = list(_FIELD_RE["question"].finditer(s))
    if not questions or not questions[-1].group(1).strip():
        return None, None
    last = questions[-1]
    justification = _FIELD_RE["justification"].search(s, last.end())
    return {"assumptions": [], "question": _json_string(last.group(1)).strip(),
            "justification": _json_string(justification.group(1)).strip() if justification else ""}, "lenient_last"


def score_response_strict(row: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """``score_response`` plus the strict gates (anlp_project.strict_gates) and the last-object extractor.

    A response that fails a gate scores as wrong (SOLVE, JUDGE) or is ``gated`` (RECONSTRUCT: score 0, never
    sent to a judge). ``format_flags`` are reported only.
    """
    from .strict_gates import judge_gate, reconstruct_format_flags, reconstruct_gate, solve_gate

    out = score_response(row, response)
    text = response.get("text") or ""
    task = row["task"]
    if task == "solve":
        out["gate"] = solve_gate(text)
        out["correct_strict"] = out["answer_status"] == "correct" and not out["gate"]
    elif task == "judge":
        out["gate"] = judge_gate(text)
        out["verdict_correct_strict"] = out["verdict_correct"] and not out["gate"]
        out["step_correct_strict"] = out["step_correct"] and not out["gate"]
    else:
        reconstruction, method = extract_reconstruction_last(text)
        out.update(extraction_strict=method, parsed_strict=reconstruction is not None,
                   reconstructed_question_strict=(reconstruction or {}).get("question"),
                   gate=reconstruct_gate(row["public_input"]["final_answer"], (reconstruction or {}).get("question"))
                   if reconstruction else ["unparseable"],
                   format_flags=reconstruct_format_flags(text))
    return out
