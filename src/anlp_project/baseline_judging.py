"""Model-judged scores for stored baseline responses, following the repository pipelines.

- JUDGE: DeepSeek V4.1 Flash rates V/L/E/M with ``data/prompts/judge/judge_eval_p1.md``
  (as ``scripts/evaluate_judge_qwen.py``); score = 6.25 * sum.
- RECONSTRUCT: PC-v4 source-aware fidelity (P, T) and source-blind validity (E, M)
  judges, certificate validation, and ``aggregate`` (6.25 * sum, shortcut -> 0), as in
  ``scripts/run_reconstruct_final100.py``.

Every call is made at most once and stored with its prompt and raw output; a failed
call is recorded and never retried automatically.
"""

from __future__ import annotations

import json
import os
import re
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from . import reconstruct as r
from .baseline import extract_reconstruction, output_dir, rows_for
from .paths import ENV_FILE, PROMPTS_DIR
from .reconstruct_judge_validation import validate_judgment
from .reconstruct_partial_credit import aggregate, balanced_rating_v4

JUDGE_MODEL = "deepseek-ai/DeepSeek-V4.1-Flash"
MAX_TOKENS = 8192
REASONING = "low"
MAX_CONCURRENCY = 16  # raised from the repository's earlier limit of 4 at the user's request
JUDGE_RATER = PROMPTS_DIR / "judge" / "judge_eval_p1.md"
PC_V4 = PROMPTS_DIR / "reconstruct" / "partial_credit_v4"
DIMENSIONS = ("V", "L", "E", "M")


_PLACEHOLDER = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def render(template: str, values: dict[str, Any]) -> str:
    """Fill the template's own placeholders in one pass.

    Same output as ``reconstruct.render_template`` except that text inside a filled-in
    value (for example a response containing ``{{1}}``) is never read as a placeholder.
    """
    missing = sorted(set(_PLACEHOLDER.findall(template)) - set(values))
    if missing:
        raise ValueError(f"Missing template values: {missing}")

    def value(match):
        v = values[match.group(1)]
        return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, indent=2)

    return _PLACEHOLDER.sub(value, template)


def _client():
    if not os.getenv("DEEPINFRA_API_KEY"):
        from dotenv import dotenv_values

        env = dotenv_values(ENV_FILE)
        key = env.get("DEEPINFRA_API_KEY") or env.get("DEEPINFRA_KEY")
        if not key:
            raise RuntimeError("Set DEEPINFRA_API_KEY (or DEEPINFRA_KEY) in .env")
        os.environ["DEEPINFRA_API_KEY"] = key
    return r.deepinfra_client(180)


# ------------------------------------------------------------------ JUDGE

def judge_rating_prompt(row: dict[str, Any], response_text: str) -> str:
    key = row["private"]
    answer_key = dict(label=key["label"], first_wrong_step=key["first_error_step_id"] or "none",
                      error_explanation=key["first_error_explanation"], error_type=key["error_type"],
                      reference_response=key["teacher_target_response"])
    return render(JUDGE_RATER.read_text(encoding="utf-8"), dict(
        PROBLEM=row["public"]["problem"],
        PROPOSED_SOLUTION="\n".join(f"{s['step_id']}: {s['text']}" for s in row["public"]["proposed_solution"]),
        ANSWER_KEY=json.dumps(answer_key, ensure_ascii=False, indent=1),
        STUDENT_RESPONSE=response_text or "(empty response)"))


def validate_rating(out: dict[str, Any], label: str) -> dict[str, Any]:
    """Same checks as scripts/evaluate_judge_qwen.py."""
    if out.get("status") not in ("scored", "needs_review"):
        raise ValueError("Invalid status")
    scores = {}
    for d in DIMENSIONS:
        s = (out.get(d) or {}).get("score", "missing")
        if not (s is None or (type(s) is int and 0 <= s <= 4)):
            raise ValueError(f"Invalid {d} score")
        if not isinstance((out.get(d) or {}).get("reason"), str):
            raise ValueError(f"{d} missing reason")
        scores[d] = s
    if out["status"] == "scored" and any(s is None for s in scores.values()):
        raise ValueError("scored with an unresolved dimension")
    if scores["V"] is not None and scores["V"] not in (0, 4):
        raise ValueError("V must be 0 or 4")
    if scores["L"] is not None and scores["L"] not in ((0, 2, 4) if label == "incorrect" else (0, 4)):
        raise ValueError("L outside the allowed values")
    if scores["V"] == 0 and not (scores["L"] in (0, None) and scores["E"] in (0, None)):
        raise ValueError("Wrong verdict must score L=0 and E=0")
    return out


# ------------------------------------------------------------ RECONSTRUCT

def reconstruct_prompts(row: dict[str, Any], response: dict[str, Any]) -> dict[str, tuple[str, dict]]:
    clues = row["public_input"]["clues"]
    rendered = "\n".join(f"{n}. {c}" for n, c in enumerate(clues, 1))
    fidelity = dict(SOURCE_QUESTION=row["question"], CANDIDATE_QUESTION=response["question"])
    validity = dict(FINAL_ANSWER=row["public_input"]["final_answer"], RENDERED_CLUES=rendered,
                    STUDENT_RESPONSE=response)
    return {role: (render((PC_V4 / f"judge_{role}.md").read_text(encoding="utf-8"), args), args)
            for role, args in (("fidelity", fidelity), ("validity", validity))}


# ---------------------------------------------------------------- driver

def _resolve(split: str, key: str) -> tuple[Path, dict[str, dict[str, Any]]]:
    """Run folder and question rows. ``split="dev"`` means an OPD dev evaluation, artifacts/opd/evals/<key>."""
    if split == "dev":
        from .opd import slice_rows
        from .paths import ARTIFACTS_DIR

        rows = {r["uid"]: r for t in ("judge", "reconstruct") for r in slice_rows(t, "dev")}
        return ARTIFACTS_DIR / "opd" / "evals" / key, rows
    return output_dir(split, key), {x["uid"]: x for x in rows_for(split, ("judge", "reconstruct"))}


def _jobs(split: str, model_key: str) -> list[dict[str, Any]]:
    directory, rows = _resolve(split, model_key)
    responses = [json.loads(l) for l in (directory / "responses.jsonl").open(encoding="utf-8")]
    jobs = []
    for resp in responses:
        row = rows.get(resp["uid"])
        if row is None:
            continue
        if row["task"] == "judge":
            jobs.append(dict(key=f"judge:{row['uid']}", uid=row["uid"], role="rater",
                             prompt=judge_rating_prompt(row, resp["text"]),
                             check=lambda out, row=row: validate_rating(out, row["private"]["label"])))
            continue
        response, method = extract_reconstruction(resp["text"])
        if response is None:
            continue  # unusable response: a failed attempt, not a judge call
        for role, (prompt, args) in reconstruct_prompts(row, response).items():
            jobs.append(dict(key=f"reconstruct-{role}:{row['uid']}", uid=row["uid"], role=role, prompt=prompt,
                             extraction=method,
                             check=lambda out, role=role, response=response: validate_judgment(
                                 out, role, question=response["question"], response=response, clue_count=4)))
    return jobs


TRANSPORT_ATTEMPTS = 2  # a call that never returned a judgment may be sent once more


def _settled(records: list[dict[str, Any]]) -> bool:
    """A key is final once the judge returned output (valid or not) or transport retries ran out."""
    returned = any(x.get("ok") or "validation_error" in x for x in records)
    return returned or len(records) >= TRANSPORT_ATTEMPTS


def _call_with_backoff(client, prompt: str) -> dict[str, Any]:
    """Provider back-pressure (429 'Model busy') and dropped connections are transient:
    wait and resend within the same attempt instead of recording a failure."""
    import time

    for attempt in range(6):
        try:
            return r.teacher_call(client, prompt, JUDGE_MODEL, MAX_TOKENS, REASONING)
        except Exception as exc:
            transient = "429" in str(exc) or type(exc).__name__ == "APIConnectionError"
            if not transient or attempt == 5:
                raise
            time.sleep(min(60, 5 * 2 ** attempt))


def run(split: str, model_key: str, limit: int = 0, workers: int = MAX_CONCURRENCY) -> dict[str, int]:
    path = _resolve(split, model_key)[0] / "judgments.jsonl"
    history: dict[str, list[dict[str, Any]]] = {}
    if path.exists():
        for line in path.open(encoding="utf-8"):
            rec = json.loads(line)
            history.setdefault(rec["key"], []).append(rec)
    todo = [j for j in _jobs(split, model_key) if not _settled(history.get(j["key"], []))]
    todo = todo[:limit] if limit else todo
    client, lock, counts = _client(), threading.Lock(), {"ok": 0, "invalid": 0, "error": 0}

    def work(job):
        rec = {k: job[k] for k in ("key", "uid", "role")} | {"model": JUDGE_MODEL, "extraction": job.get("extraction"),
                                                            "prompt_sha256": r.stable_hash(job["prompt"])}
        try:
            raw = _call_with_backoff(client, job["prompt"])
            rec["raw"] = raw
            try:
                out = r.extract_json_object(raw["content"])
                job["check"](out)
                rec.update(ok=True, output=out)
                status = "ok"
            except Exception as exc:  # judgment returned but failed validation: stays unresolved
                rec.update(ok=False, validation_error=str(exc))
                status = "invalid"
        except Exception as exc:
            rec.update(ok=False, error=f"{type(exc).__name__}: {exc}")
            status = "error"
        with lock:
            counts[status] += 1
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, todo))
    return {**counts, "attempted_now": len(todo), "previously_recorded_keys": len(history)}


def _mean_known(values):
    """Mean over resolved values; a shortcut can score 0 while a dimension is unresolved."""
    known = [v for v in values if v is not None]
    return statistics.mean(known) if known else None


def summarize(split: str, model_key: str) -> dict[str, Any]:
    directory, rows = _resolve(split, model_key)
    judgments, cost, transport_failures = {}, 0.0, 0
    for line in (directory / "judgments.jsonl").open(encoding="utf-8"):
        rec = json.loads(line)
        cost += ((rec.get("raw") or {}).get("usage") or {}).get("estimated_cost") or 0.0
        transport_failures += "error" in rec
        current = judgments.get(rec["key"])
        # The first returned judgment is the recorded one; a transport failure is replaced by a later attempt.
        if current is None or "error" in current:
            judgments[rec["key"]] = rec
    responses = {x["uid"]: x for x in map(json.loads, (directory / "responses.jsonl").open(encoding="utf-8"))}

    judge_items = []
    for uid, row in rows.items():
        if row["task"] != "judge" or uid not in responses:
            continue
        rec = judgments.get(f"judge:{uid}")
        out = rec["output"] if rec and rec.get("ok") else None
        dims = {d: (out[d]["score"] if out else None) for d in DIMENSIONS}
        score = 6.25 * sum(dims.values()) if out and None not in dims.values() else None
        judge_items.append(dict(uid=uid, task="judge", label=row["private"]["label"], dimensions=dims,
                                score_100=score, rating_1_to_5=balanced_rating_v4(score)))

    recon_items = []
    for uid, row in rows.items():
        if row["task"] != "reconstruct" or uid not in responses:
            continue
        response, method = extract_reconstruction(responses[uid]["text"])
        f = judgments.get(f"reconstruct-fidelity:{uid}")
        v = judgments.get(f"reconstruct-validity:{uid}")
        if response is None:
            recon_items.append(dict(uid=uid, task="reconstruct", status="unusable_response", score_100=None,
                                    extraction=None))
            continue
        agg = aggregate(f["output"] if f and f.get("ok") else None, v["output"] if v and v.get("ok") else None)
        semantic = (f or {}).get("output", {}).get("semantic_equivalent") if f and f.get("ok") else None
        d = agg["dimensions"]
        grounded = bool(semantic is True and agg["score_100"] is not None and agg["shortcut"] is False
                        and d["premise_fidelity"] == 4 and d["target_fidelity"] == 4
                        and d["evidence_integration"] == 4 and d["mathematical_validity"] in (3, 4))
        recon_items.append(dict(uid=uid, task="reconstruct", status="scored" if agg["score_100"] is not None else "unresolved",
                                extraction=method, dimensions=d, shortcut=agg["shortcut"],
                                semantic_equivalent=semantic, provisional_grounded_recovery=grounded,
                                score_100=agg["score_100"], rating_1_to_5=balanced_rating_v4(agg["score_100"])))
    per_item = judge_items + recon_items
    with (directory / "judged-scores.jsonl").open("w", encoding="utf-8") as handle:
        for item in per_item:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    def stats(items, dims):
        scored = [i for i in items if i["score_100"] is not None]
        s = [i["score_100"] for i in scored]
        out = {"n": len(items), "scored": len(scored), "missing": len(items) - len(scored)}
        if s:
            out.update(mean=statistics.mean(s), median=statistics.median(s),
                       mean_counting_missing_as_0=sum(s) / len(items),
                       rating_histogram_1_to_5=[sum(i["rating_1_to_5"] == k for i in scored) for k in range(1, 6)],
                       dimension_means={d: _mean_known(i["dimensions"][d] for i in scored) for d in dims})
        return out

    summary = {"judge_model": JUDGE_MODEL, "judge": stats(judge_items, DIMENSIONS),
               "reconstruct": stats(recon_items, ("premise_fidelity", "target_fidelity",
                                                  "evidence_integration", "mathematical_validity"))}
    summary["reconstruct"].update(
        unusable_responses=sum(i["status"] == "unusable_response" for i in recon_items),
        unresolved_judgments=sum(i["status"] == "unresolved" for i in recon_items),
        shortcuts=sum(bool(i.get("shortcut")) for i in recon_items),
        semantic_equivalent=sum(i.get("semantic_equivalent") is True for i in recon_items),
        provisional_grounded_recoveries=sum(i.get("provisional_grounded_recovery", False) for i in recon_items))
    summary["judge_calls"] = {"keys": len(judgments), "valid": sum(j.get("ok", False) for j in judgments.values()),
                              "validation_failures": sum("validation_error" in j for j in judgments.values()),
                              "unresolved_transport_failures": sum("error" in j for j in judgments.values()),
                              "transport_failures_retried": transport_failures - sum("error" in j for j in judgments.values()),
                              "estimated_cost_usd": round(cost, 4)}
    (directory / "judged-summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary
