#!/usr/bin/env python3
"""Failure-driven cross-task GRPO pilot: failure buffer, auxiliary items, arm-B prompt lists.

    python phase2/failure_driven/fd.py buffer --rollouts <run>/rollouts --steps 1-8 --out <dir>
    python phase2/failure_driven/fd.py convert --buffer <dir>/buffer.json --out <dir>        # DeepSeek API, local
    python phase2/failure_driven/fd.py prompts --round 2 --items <dir>[,<dir>...] --out <dir>

The SOLVE pool is JUDGE-dataset train questions (build_pool.py), so every failed question already has a verified
JUDGE item and reference solutions. Nothing here re-implements an existing pipeline:
- Buffer: Yashas's dead-problem rule (phase2/scripts/hint_pilot.py `agents`): no strictly correct answer among the
  question's 8 rollouts, and at least 5 verified-wrong answers that finished and passed the strict gate. Truncated,
  unparseable and gated answers are counted but are not mathematical failures. The representative attempt is the
  shortest member of the most common wrong answer (`modal_wrong`, grouped by checker v3).
- JUDGE item: the question's FINAL-v3 JUDGE item as it is (direct conversion; no API call).
- Diagnosis (new): DeepSeek V4.1 Flash reads the representative attempt (prompts/diagnose.md). It counts as checked
  only when it is "diagnosed", names a misconception, and its quote is verbatim in the attempt.
- RECONSTRUCT item: the FINAL-v3 RECONSTRUCT pipeline (scripts/generate_reconstruct_dataset_v1.py) with the same
  prompts, model, decoding, caps and validators: convert (final_v1/convert.md, 16,384 tokens) -> audit + copy gate
  (8,192 each; accepted on ACCEPT + no_direct_reconstruction) -> otherwise one audit_correct_p1 call (16,384) whose
  decision is final. CHECKED_SOLUTION is reference_solutions[0], as in the dataset. Mistake-targeted conversion:
  with a checked diagnosis, the convert prompt gets a note on which condition to withhold; otherwise it is the
  unchanged (direct) prompt.
Every DeepSeek call is logged with its token usage (compute accounting). A call that fails in transport is sent at
most once more; an invalid output is never regenerated (the dataset pipeline's rule).
"""

from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
from anlp_project import baseline  # noqa: E402
from anlp_project import reconstruct as r  # noqa: E402
from anlp_project.solution_verification import compare_answer_detailed, extract_final_answer  # noqa: E402

_spec = importlib.util.spec_from_file_location("recon_v1", REPO / "scripts" / "generate_reconstruct_dataset_v1.py")
recon_v1 = importlib.util.module_from_spec(_spec)
_cwd = os.getcwd()
os.chdir(REPO)  # the script resolves its prompt and manifest paths relative to the repository root
try:
    _spec.loader.exec_module(recon_v1)
finally:
    os.chdir(_cwd)
m100 = recon_v1.m  # run_reconstruct_final100: validate_bank, validate_audit, validate_copy

DATA = HERE / "data"
RECON_PROMPTS = REPO / recon_v1.PROMPTS
CORRECT_PROMPT = REPO / recon_v1.CORRECT_PROMPT
MODEL, REASONING = r.DEFAULT_TEACHER_MODEL, "low"
CAPS = {"diagnose": 8192, "convert": 16384, "gate": 8192, "correct": 16384}
SAMPLES, MIN_WRONG = 8, 5  # hint_pilot: SAMPLES rollouts per question, --min-wrong 5
WORKERS = 6  # the user's limit for DeepSeek concurrency
AUX_PER_STEP, SOLVE_PER_STEP_B, STEPS_PER_ROUND = 8, 24, 8
TARGET_NOTE = ("\n\nTARGETING NOTE (for choosing what to withhold): a student solving this question made this mistake: "
               "{mistake} The idea they mishandled: {misconception} Prefer to withhold the condition, parameter or "
               "quantity involved in this mistake, so that reconstructing the question requires attending to it. "
               "Every rule above still applies.")


def read_jsonl(path: Path) -> list[dict]:
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        for x in rows:
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")


def pool() -> dict:
    return json.loads((DATA / "pool.json").read_text())


def solve_rows() -> dict[str, dict]:
    return {x["uid"]: x for x in read_jsonl(DATA / "solve_rows.jsonl")}


def judge_rows() -> dict[str, dict]:
    return {x["uid"]: x for x in baseline.load_rows("judge", "train")}


# --------------------------------------------------------------------------------------------- buffer

def modal_wrong(samples: list[dict]) -> list[dict]:
    """hint_pilot.modal_wrong: group verified-wrong answers by checker-v3 equivalence; the largest group."""
    groups: list[list[dict]] = []
    for s in samples:
        for g in groups:
            if compare_answer_detailed(g[0]["extracted_answer"], s["extracted_answer"])["answer_status"] == "correct":
                g.append(s)
                break
        else:
            groups.append([s])
    return max(groups, key=len)


def cmd_buffer(a) -> None:
    lo, hi = map(int, a.steps.split("-"))
    rows, p = solve_rows(), pool()
    skip = set(json.loads(Path(a.skip).read_text())) if a.skip else set()
    by_uid = collections.defaultdict(list)
    for step in range(lo, hi + 1):
        for x in read_jsonl(Path(a.rollouts) / f"step{step}.jsonl"):
            if x["uid"] not in rows or x["uid"] in skip:  # auxiliary prompts (arm B) or replayed questions (arm D)
                continue
            s = baseline.score_response_strict(rows[x["uid"]], {"text": x["text"], "finish_reason": x["finish"]})
            by_uid[x["uid"]].append({"text": x["text"], "finish": x["finish"], "reward": x["reward"], "step": step,
                                     **{k: s[k] for k in ("extracted_answer", "answer_status", "gate", "correct_strict")}})
    summary, buffer = collections.Counter(), []
    for u, samples in by_uid.items():
        n_correct = sum(s["correct_strict"] for s in samples)
        wrong = [s for s in samples if s["answer_status"] == "incorrect" and s["finish"] == "stop" and not s["gate"]]
        kinds = collections.Counter("correct" if s["correct_strict"] else "truncated" if s["finish"] != "stop"
                                    else "gated" if s["gate"] else "wrong" if s["answer_status"] == "incorrect"
                                    else "unverified" for s in samples)
        summary["questions"] += 1
        summary["zero_correct"] += n_correct == 0
        for k, v in kinds.items():
            summary[f"rollouts_{k}"] += v
        if n_correct > a.max_correct or len(wrong) < MIN_WRONG:
            continue
        members = modal_wrong(wrong)
        rep = min(members, key=lambda s: len(s["text"]))
        buffer.append({"uid": u, "judge_uid": p["judge_uid"][u], "steps_seen": sorted({s["step"] for s in samples}),
                       "n_correct": n_correct, "strict_rule": n_correct == 0,
                       "kinds": dict(kinds), "n_wrong": len(wrong), "wrong_answer": rep["extracted_answer"],
                       "wrong_count": len(members), "attempt": rep["text"]})
    summary["buffer"] = len(buffer)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "buffer.json").write_text(json.dumps({"rollouts": a.rollouts, "steps": a.steps, "rule":
        f"<= {a.max_correct} strictly correct of {SAMPLES}; >= {MIN_WRONG} verified wrong, finished, not gated "
        f"(hint_pilot with max_correct 0)",
        "max_correct": a.max_correct,
        "summary": summary, "questions": buffer}, ensure_ascii=False, indent=1))
    print(json.dumps(summary))


# ------------------------------------------------------------------------------------------ DeepSeek

class DeepSeek:
    """The dataset pipeline's client and call (temperature 0, reasoning low). Logs every call's usage."""

    def __init__(self, log_path: Path):
        if not os.getenv("DEEPINFRA_API_KEY"):
            from dotenv import dotenv_values
            env = dotenv_values(REPO / ".env")
            key = env.get("DEEPINFRA_API_KEY") or env.get("DEEPINFRA_KEY")
            if not key:
                raise RuntimeError("no DeepInfra key in .env")
            os.environ["DEEPINFRA_API_KEY"] = key
        self.client, self.log_path, self.lock = r.deepinfra_client(900), log_path, threading.Lock()

    def __call__(self, prompt: str, cap: int, tag: str) -> dict:
        raw, rec = None, {}
        for attempt in (1, 2):  # one retry, for transport failures only
            t0 = time.time()
            try:
                raw = r.teacher_call(self.client, prompt, MODEL, cap, REASONING)
                rec = {"tag": tag, "ok": True, "usage": raw.get("usage"), "finish_reason": raw.get("finish_reason"),
                       "seconds": round(time.time() - t0, 1), "attempt": attempt}
                break
            except Exception as exc:
                rec = {"tag": tag, "ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                       "seconds": round(time.time() - t0, 1), "attempt": attempt}
                if attempt == 1:
                    time.sleep(10)
        with self.lock, self.log_path.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
        if raw is None:
            raise RuntimeError(rec["error"])
        return r.extract_json_object(raw["content"])


# ------------------------------------------------------------------------------------------ conversion

def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def trusted_solution(row: dict) -> str:
    """For the diagnosis: the final part (after </think>) of the first reference solution checker v3 accepts."""
    for s in row["reference_solutions"]:
        final = s.split("</think>")[-1].strip()
        ans = extract_final_answer(final)[0]
        if len(final) >= 200 and ans and compare_answer_detailed(row["final_answer"], ans)["answer_status"] == "correct":
            return final
    return row["reference_solutions"][0].split("</think>")[-1].strip()


def diagnose(ds: DeepSeek, row: dict, q: dict) -> dict:
    prompt = r.render_template((HERE / "prompts" / "diagnose.md").read_text(), {
        "PROBLEM": row["question"], "CORRECT_ANSWER": row["final_answer"], "TRUSTED_SOLUTION": trusted_solution(row),
        "STUDENT_ANSWER": q["wrong_answer"] or "", "STUDENT_ATTEMPT": q["attempt"]})
    d = ds(prompt, CAPS["diagnose"], f"diagnose:{q['uid']}")
    quote = _ws(d.get("first_wrong_quote", ""))
    verbatim = len(quote) >= 10 and quote in _ws(q["attempt"])
    checked = d.get("status") == "diagnosed" and verbatim and bool(_ws(d.get("misconception")))
    reason = ("checked" if checked else "quote not verbatim in the attempt" if d.get("status") == "diagnosed"
              else "diagnosis uncertain")
    return {"output": d, "checked": checked, "reason": reason}


def make_reconstruct(ds: DeepSeek, row: dict, uid: str, diag: dict | None) -> dict:
    """generate_reconstruct_dataset_v1: convert -> audit + copy -> audit_correct_p1 for anything not accepted."""
    checked_solution = row["reference_solutions"][0]
    src = {"SOURCE_QUESTION": row["question"], "FINAL_ANSWER": row["final_answer"], "CHECKED_SOLUTION": checked_solution}
    prompt = r.render_template((RECON_PROMPTS / "convert.md").read_text(), src)
    targeted = bool(diag and diag["checked"])
    if targeted:
        prompt += TARGET_NOTE.format(**{k: diag["output"][k] for k in ("mistake", "misconception")})
    out = {"mode": "targeted" if targeted else "direct", "accepted": False}
    try:
        bank = ds(prompt, CAPS["convert"], f"recon_convert:{uid}")
        m100.validate_bank(bank)
        out["bank"] = bank
        if bank["status"] == "NOT_SUITABLE":
            out["reason"] = f"NOT_SUITABLE: {str(bank.get('reason', ''))[:200]}"
            return out
        clues = [{"id": c["id"], "sentence": c["sentence"]} for c in bank["clues"][:4]]
        ev = {"final_answer": row["final_answer"], "clues": clues,
              "rendered_clues": "\n".join(f"{n}. {c['sentence']}" for n, c in enumerate(clues, 1))}
        audit = copy = None
        errors = {}
        try:
            audit = ds(r.render_template((RECON_PROMPTS / "audit.md").read_text(),
                                         {**src, "RENDERED_CLUES": ev["rendered_clues"]}), CAPS["gate"], f"recon_audit:{uid}")
            m100.validate_audit(audit, ev)
        except Exception as exc:
            audit, errors["audit"] = None, f"{type(exc).__name__}: {str(exc)[:200]}"
        try:
            copy = ds(r.render_template((RECON_PROMPTS / "copy.md").read_text(),
                                        {"FINAL_ANSWER": row["final_answer"], "PUBLIC_BANK": ev["rendered_clues"]}),
                      CAPS["gate"], f"recon_copy:{uid}")
            m100.validate_copy(copy, ev)
        except Exception as exc:
            copy, errors["copy"] = None, f"{type(exc).__name__}: {str(exc)[:200]}"
        out.update(audit=audit, copy=copy, gate_errors=errors)
        if audit and audit["status"] == "ACCEPT" and copy and copy["status"] == "no_direct_reconstruction":
            out.update(accepted=True, accepted_by="v1_audit_and_copy", clues=[c["sentence"] for c in clues],
                       reason="accepted")
            return out
        spare = "\n".join(f"- {c['sentence']}" for c in bank["clues"][4:]) or "(none)"
        prior = json.dumps({"audit": audit or {"unavailable": errors.get("audit")},
                            "copy_challenge": copy or {"unavailable": errors.get("copy")}}, ensure_ascii=False, indent=1)
        corr = ds(r.render_template(CORRECT_PROMPT.read_text(), {
            **src, "RENDERED_CLUES": ev["rendered_clues"], "SPARE_CLUES": spare, "PRIOR_REVIEWS": prior}),
            CAPS["correct"], f"recon_correct:{uid}")
        recon_v1.validate_correction(corr, ev, row["question"])
        out["audit_correct"] = corr
        if corr["decision"] == "UNREPAIRABLE":
            out["reason"] = f"UNREPAIRABLE: {corr['reason'][:200]}"
        elif corr["decision"] == "ACCEPT_UNCHANGED":
            out.update(accepted=True, accepted_by="audit_correct_unchanged", clues=[c["sentence"] for c in clues],
                       reason="accepted")
        else:
            out.update(accepted=True, accepted_by="audit_correct_corrected", reason="accepted",
                       clues=[c["sentence"] for c in corr["corrected_clues"]])
    except Exception as exc:
        out["reason"] = f"{type(exc).__name__}: {str(exc)[:200]}"
    return out


def cmd_convert(a) -> None:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    buf = json.loads(Path(a.buffer).read_text())["questions"]
    if a.limit:
        buf = buf[:a.limit]
    rows, judge = solve_rows(), judge_rows()
    items_path = out / "items.jsonl"
    done = {x["uid"] for x in read_jsonl(items_path)} if items_path.exists() else set()
    todo = [q for q in buf if q["uid"] not in done]
    ds, lock = DeepSeek(out / "calls.jsonl"), threading.Lock()
    print(f"{len(buf)} buffered questions, {len(done)} already converted, {len(todo)} to do", flush=True)

    def work(q):
        row = {**rows[q["uid"]], "reference_solutions": judge[q["judge_uid"]]["reference_solutions"]}
        rec = {"uid": q["uid"], "judge_uid": q["judge_uid"]}
        try:
            rec["diagnosis"] = diagnose(ds, row, q)
        except Exception as exc:
            rec["diagnosis"] = {"checked": False, "reason": f"{type(exc).__name__}: {str(exc)[:200]}"}
        rec["reconstruct"] = make_reconstruct(ds, row, q["uid"], rec["diagnosis"])
        with lock, items_path.open("a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(q["uid"], "| diagnosis", rec["diagnosis"]["reason"], "| reconstruct", rec["reconstruct"]["mode"],
              rec["reconstruct"]["reason"][:80], flush=True)

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(work, todo))
    summarize(out)


def summarize(out: Path) -> dict:
    items = read_jsonl(out / "items.jsonl")
    calls = read_jsonl(out / "calls.jsonl") if (out / "calls.jsonl").exists() else []
    tok = collections.Counter()
    for c in calls:
        for k, v in (c.get("usage") or {}).items():
            if isinstance(v, int):
                tok[k] += v
    s = {"questions": len(items),
         "diagnosis": dict(collections.Counter(x["diagnosis"]["reason"] for x in items)),
         "reconstruct_accepted": sum(x["reconstruct"]["accepted"] for x in items),
         "reconstruct_by_route": dict(collections.Counter(x["reconstruct"].get("accepted_by") or
                                                         x["reconstruct"]["reason"].split(":")[0] for x in items)),
         "reconstruct_mode_accepted": dict(collections.Counter(x["reconstruct"]["mode"] for x in items
                                                              if x["reconstruct"]["accepted"])),
         "judge_items": len(items), "calls": len(calls), "failed_calls": sum(not c["ok"] for c in calls),
         "tokens": dict(tok)}
    (out / "summary.json").write_text(json.dumps(s, indent=1))
    print(json.dumps(s))
    return s


# --------------------------------------------------------------------------------------------- recheck

def cmd_recheck(a) -> None:
    """Unaided re-solve of buffered questions (eval_matrix --split uids, 8 samples, folders s0..s7): a question stays
    in the buffer while at most `max_correct` of its samples are strictly correct; the rest have recovered."""
    buf = json.loads(Path(a.buffer).read_text())["questions"]
    correct = collections.defaultdict(list)
    for d in sorted(Path(a.eval_dir).glob("s[0-9]*")):
        for x in read_jsonl(d / "scores.jsonl"):
            correct[x["uid"]].append(bool(x["correct_strict"]))
    missing = [q["uid"] for q in buf if q["uid"] not in correct]
    if missing:
        raise SystemExit(f"{len(missing)} buffered questions have no recheck samples, e.g. {missing[:3]}")
    keep = [q["uid"] for q in buf if sum(correct[q["uid"]]) <= a.max_correct]
    rec = {"buffer": a.buffer, "eval_dir": a.eval_dir, "max_correct": a.max_correct, "questions": len(buf),
           "still_failing": len(keep), "recovered": len(buf) - len(keep),
           "correct_of_samples": {q["uid"]: f"{sum(correct[q['uid']])}/{len(correct[q['uid']])}" for q in buf},
           "keep": keep}
    Path(a.out).write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ("questions", "still_failing", "recovered")}))


# --------------------------------------------------------------------------------------------- prompts

def reconstruct_row(row: dict, rec: dict) -> dict:
    """A FINAL-v3-shaped RECONSTRUCT row for the reward (jev_judging reads uid, task, question, public_input)."""
    return {"task": "reconstruct", "split": "train", "uid": f"fdrc-{row['dataset_row_index']}",
            "question": row["question"], "final_answer": row["final_answer"],
            "public_input": {"final_answer": row["final_answer"], "clues": rec["clues"]},
            "broad_topic": row["broad_topic"], "difficulty": row["difficulty"],
            "fd": {"source_uid": row["uid"], "mode": rec["mode"], "accepted_by": rec["accepted_by"]}}


def cmd_prompts(a) -> None:
    """Arm B's prompts for one round: per step 24 SOLVE (the pool's arm-B order) + 8 auxiliary prompts.

    Auxiliary slots alternate JUDGE and RECONSTRUCT items of the current buffer. With fewer than 64 items, items
    repeat (a replay buffer) in a seeded order, never twice in one step (GRPO groups are keyed by uid)."""
    p, rows, judge = pool(), solve_rows(), judge_rows()
    k = a.round - 2  # rounds 2 and 3 are arm B's steps 9-16 and 17-24
    per_round = SOLVE_PER_STEP_B * STEPS_PER_ROUND
    solve = p["armB_solve"][k * per_round:(k + 1) * per_round]
    items, recon_rows = [], {}
    for d in a.items.split(","):
        for x in read_jsonl(Path(d) / "items.jsonl"):
            if a.keep and x["uid"] not in set(json.loads(Path(a.keep).read_text())):
                continue
            items.append(("judge", x["judge_uid"]))
            if x["reconstruct"]["accepted"]:
                rr = reconstruct_row(rows[x["uid"]], x["reconstruct"])
                recon_rows[rr["uid"]] = rr
                items.append(("reconstruct", rr["uid"]))
    items = list(dict.fromkeys(items))
    judges = [i for i in items if i[0] == "judge"]
    recons = [i for i in items if i[0] == "reconstruct"]
    rng = random.Random(f"fd-aux-r{a.round}")
    rng.shuffle(judges)
    rng.shuffle(recons)
    order = [x for pair in zip(judges, recons) for x in pair] + judges[len(recons):] + recons[len(judges):]
    need = AUX_PER_STEP * STEPS_PER_ROUND
    if not order:
        raise SystemExit("no auxiliary items")
    seq = (order * (need // len(order) + 1))[:need]
    steps_aux = [seq[i * AUX_PER_STEP:(i + 1) * AUX_PER_STEP] for i in range(STEPS_PER_ROUND)]
    for st in steps_aux:
        if len(set(st)) != len(st):
            raise SystemExit(f"only {len(order)} items: an item would repeat within one step; lower AUX_PER_STEP")
    out_prompts = []
    for i in range(STEPS_PER_ROUND):
        for u in solve[i * SOLVE_PER_STEP_B:(i + 1) * SOLVE_PER_STEP_B]:
            out_prompts.append({"uid": u, "prompt": baseline.render_prompt(rows[u]), "task": "solve",
                                "final_answer": rows[u]["final_answer"]})
        for task, u in steps_aux[i]:
            row = judge[u] if task == "judge" else recon_rows[u]
            item = {"uid": u, "prompt": baseline.render_prompt(row), "task": task}
            if task == "reconstruct" and row["question"] in item["prompt"]:
                raise SystemExit(f"source question leaked into the RECONSTRUCT prompt for {u}")
            if task == "judge":
                item["label"] = row["private"]["label"]
                item["first_error_step"] = row["private"]["first_error_step_id"] if row["private"]["label"] == "incorrect" else "none"
            out_prompts.append(item)
    out = Path(a.out)
    write_jsonl(out / f"prompts-B-r{a.round}.jsonl", out_prompts)
    # answer keys: the pool's SOLVE rows + every accepted RECONSTRUCT row (JUDGE items are in the judge train split)
    prev = {x["uid"]: x for x in read_jsonl(out / "reward_rows.jsonl")} if (out / "reward_rows.jsonl").exists() else {}
    write_jsonl(out / "reward_rows.jsonl", list({**rows, **prev, **recon_rows}.values()))
    counts = collections.Counter(t for t, _ in seq)
    stats = {"round": a.round, "prompts": len(out_prompts), "solve": len(solve), "aux_slots": need,
             "distinct_items": len(order), "judge_items": len(judges), "reconstruct_items": len(recons),
             "aux_slots_by_task": dict(counts), "max_uses_per_item": max(collections.Counter(seq).values())}
    (out / f"prompts-B-r{a.round}.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats))


def cmd_replay_prompts(a) -> None:
    """Arm D (same-form retry): like arm B's prompts, but the 8 extra slots per step hold the buffered failed
    questions again as plain SOLVE prompts. Same SOLVE questions and slot order rule as arm B; a question repeats
    across steps when the buffer has fewer than 64, never twice in one step."""
    p, rows = pool(), solve_rows()
    k = a.round - 2
    per_round = SOLVE_PER_STEP_B * STEPS_PER_ROUND
    solve = p["armB_solve"][k * per_round:(k + 1) * per_round]
    keep = set(json.loads(Path(a.keep).read_text())) if a.keep else None
    order = []
    for b in a.buffers.split(","):
        order += [q["uid"] for q in json.loads(Path(b).read_text())["questions"] if keep is None or q["uid"] in keep]
    order = list(dict.fromkeys(order))
    if set(order) & set(solve):
        raise SystemExit("a replayed question is also a fresh SOLVE question of this round")
    random.Random(f"fd-replay-r{a.round}").shuffle(order)
    need = AUX_PER_STEP * STEPS_PER_ROUND
    seq = (order * (need // len(order) + 1))[:need]
    steps_aux = [seq[i * AUX_PER_STEP:(i + 1) * AUX_PER_STEP] for i in range(STEPS_PER_ROUND)]
    if any(len(set(st)) != len(st) for st in steps_aux):
        raise SystemExit(f"only {len(order)} questions: one would repeat within a step")
    item = lambda u: {"uid": u, "prompt": baseline.render_prompt(rows[u]), "task": "solve",
                      "final_answer": rows[u]["final_answer"]}
    out_prompts = []
    for i in range(STEPS_PER_ROUND):
        out_prompts += [item(u) for u in solve[i * SOLVE_PER_STEP_B:(i + 1) * SOLVE_PER_STEP_B]]
        out_prompts += [item(u) for u in steps_aux[i]]
    out = Path(a.out)
    write_jsonl(out / f"prompts-D-r{a.round}.jsonl", out_prompts)
    (out / f"replayed-r{a.round}.json").write_text(json.dumps(order))
    stats = {"round": a.round, "prompts": len(out_prompts), "solve": len(solve), "replay_slots": need,
             "distinct_replayed": len(order), "max_uses_per_question": max(collections.Counter(seq).values())}
    (out / f"prompts-D-r{a.round}.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("buffer")
    b.add_argument("--rollouts", required=True)
    b.add_argument("--steps", required=True, help="e.g. 1-8")
    b.add_argument("--out", required=True)
    b.add_argument("--max-correct", type=int, default=0, help="0 = Yashas's rule; 1 = also questions with 1/8 right")
    b.add_argument("--skip", default="", help="JSON list of uids to leave out (arm D: the replayed questions)")
    c = sub.add_parser("convert")
    c.add_argument("--buffer", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--limit", type=int, default=0)
    rc = sub.add_parser("recheck")
    rc.add_argument("--buffer", required=True)
    rc.add_argument("--eval-dir", required=True)
    rc.add_argument("--max-correct", type=int, default=1)
    rc.add_argument("--out", required=True)
    rp = sub.add_parser("replay-prompts")
    rp.add_argument("--round", type=int, required=True, choices=[2, 3])
    rp.add_argument("--buffers", required=True, help="comma-separated buffer.json files")
    rp.add_argument("--keep", default="")
    rp.add_argument("--out", required=True)
    pr = sub.add_parser("prompts")
    pr.add_argument("--round", type=int, required=True, choices=[2, 3])
    pr.add_argument("--items", required=True, help="comma-separated convert output folders")
    pr.add_argument("--keep", default="", help="JSON list of question uids still in the buffer (after a recheck)")
    pr.add_argument("--out", required=True)
    a = ap.parse_args()
    {"buffer": cmd_buffer, "convert": cmd_convert, "recheck": cmd_recheck, "prompts": cmd_prompts,
     "replay-prompts": cmd_replay_prompts}[a.cmd](a)


if __name__ == "__main__":
    main()
