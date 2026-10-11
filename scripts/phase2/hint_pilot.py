#!/usr/bin/env python3
"""Phase-2 pilot: can the Phase-1 specialists turn a dead (0/8) SOLVE problem into a learnable one?

For each SOLVE problem the mixed model (step 75) gets wrong in all 8 samples:
  1. the most common wrong answer and one attempt that reached it are picked;
  2. the JUDGE specialist reads that attempt as a numbered proposed solution (its native format) and names the
     first wrong step and why;
  3. the RECONSTRUCT specialist receives the wrong answer and observations taken from the attempt (its native
     format) and rebuilds the question that the wrong answer actually answers;
  4. the SOLVE specialist solves the rebuilt question blind, to check it really has the wrong answer;
  5. hints are built from (2) and (3), and the mixed model retries the original problem with each hint.

Stages (each writes JSONL under --out and can be rerun independently):

    census  --shard i --nshards k   mixed model, 8 samples on its seen SOLVE pool
    agents                          JUDGE / RECONSTRUCT / SOLVE specialists on the dead problems
    test    --shard i --nshards k   mixed model, 8 samples per problem and hint arm
    report                          summary.json and report.md

All four adapters are LoRA (r 64) on Qwen/Qwen3.5-2B and are served from one vLLM engine.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from anlp_project import baseline  # noqa: E402
from anlp_project.paths import PROMPTS_DIR  # noqa: E402
from anlp_project.reconstruct import render_template  # noqa: E402
from anlp_project.solution_verification import compare_answer_detailed  # noqa: E402
from anlp_project.strict_gates import _answer_written, judge_gate, reconstruct_gate  # noqa: E402

ADAPTER_NAMES = {"mixed": 1, "solve": 2, "judge": 3, "reconstruct": 4}
ADAPTER_DIRS = {"mixed": "mixed-step75", "solve": "solve-step66", "judge": "judge-step26",
                "reconstruct": "reconstruct-step104"}
SAMPLES = 8
SOLVE_CAP = 16384
AGENT_CAP = 4096
AGENT_SAMPLES = 4
MAX_STEPS = 12
OBS_CHARS = 600
ARMS = ("none", "judge", "recon", "both")
JUDGE_INSTRUCTION = ("Decide whether the proposed solution is correct. If it is incorrect, identify the first wrong "
                     "step and explain the mathematical error.")


# ------------------------------------------------------------------ io helpers

def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(paths) -> list[dict]:
    out = []
    for p in paths:
        out.extend(json.loads(line) for line in Path(p).open(encoding="utf-8"))
    return out


def solve_rows() -> dict[str, dict]:
    return {r["uid"]: r for r in baseline.load_rows("solve", "train")}


def seen_pool(n: int) -> list[str]:
    """The SOLVE questions the mixed model trained on: the first n SOLVE uids of its interleaved order
    (75 steps x 10 SOLVE prompts = 750)."""
    order = json.loads((baseline.FINAL_V3_DIR / "grpo-mixed-1134.json").read_text())["uids"]
    return [u for u in order if u.startswith("solve-")][:n]


# ------------------------------------------------------------------ vLLM

class Engine:
    def __init__(self, base: str, adapters: Path, max_model_len: int):
        from vllm import LLM
        from vllm.lora.request import LoRARequest

        self.llm = LLM(model=base, dtype="bfloat16", language_model_only=True, max_model_len=max_model_len,
                       gpu_memory_utilization=0.90, max_num_seqs=256, seed=0, enable_lora=True,
                       max_lora_rank=64, max_loras=4)
        self.lora = {k: LoRARequest(k, i, str(adapters / ADAPTER_DIRS[k])) for k, i in ADAPTER_NAMES.items()}

    def chat(self, prompts: list[str], adapter: str, n: int, max_tokens: int, seed: int = 0) -> list[list[dict]]:
        from vllm import SamplingParams

        if not prompts:
            return []
        s = baseline.EVAL_SAMPLING
        params = SamplingParams(n=n, temperature=s["temperature"], top_p=s["top_p"], top_k=s["top_k"],
                                max_tokens=max_tokens, seed=seed)
        outs = self.llm.chat([[{"role": "user", "content": p}] for p in prompts], params,
                             lora_request=self.lora[adapter], use_tqdm=False,
                             chat_template_kwargs={"enable_thinking": False})
        return [[{"text": c.text, "finish_reason": str(c.finish_reason), "completion_tokens": len(c.token_ids)}
                 for c in o.outputs] for o in outs]


def solve_prompt(row: dict, hint: str | None = None) -> str:
    question = row["question"] if not hint else f"{row['question']}\n\n{hint}"
    return baseline.render_prompt({**row, "question": question})


def score(row: dict, resp: dict) -> dict:
    s = baseline.score_response_strict(row, resp)
    return {k: s[k] for k in ("extracted_answer", "answer_status", "verification_method", "gate", "correct_strict",
                              "hit_token_cap")}


# ------------------------------------------------------------------ stage 1: census

def census(a) -> None:
    rows = solve_rows()
    uids = seen_pool(a.pool)[a.shard::a.nshards]
    eng = Engine(a.base, Path(a.adapters), SOLVE_CAP + 4096)
    outs = eng.chat([solve_prompt(rows[u]) for u in uids], "mixed", SAMPLES, SOLVE_CAP)
    records = []
    for u, samples in zip(uids, outs, strict=True):
        for k, resp in enumerate(samples):
            records.append({"uid": u, "sample": k, **resp, **score(rows[u], resp)})
    write_jsonl(Path(a.out) / "census" / f"shard{a.shard}.jsonl", records)


# ------------------------------------------------------------------ stage 2: agents

FINAL_TAG = re.compile(r"<final_answer>\s*(.*?)\s*</final_answer>", re.S | re.I)
# A rebuilt question must be a standalone problem, not a note about the attempt it was built from.
ADDRESSES_READER = re.compile(r"\b(you|your|the user|the response|the attempt|the solver|provided (text|response|steps))\b",
                              re.I)
EXPLANATION = re.compile(r"Explanation:\s*(.+)\Z", re.S | re.I)


def to_steps(text: str) -> list[str]:
    """Split an attempt into at most MAX_STEPS numbered steps: paragraphs, merged in order when there are more."""
    text = FINAL_TAG.sub(lambda m: f"Final answer: {m.group(1)}", text.strip())
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paras) <= MAX_STEPS:
        return paras
    size = -(-len(paras) // MAX_STEPS)
    return ["\n".join(paras[i:i + size]) for i in range(0, len(paras), size)]


def modal_wrong(samples: list[dict]) -> tuple[str, list[dict]]:
    """Group verified-wrong answers by equivalence (checker v3); return the largest group's answer and members."""
    groups: list[list[dict]] = []
    for s in samples:
        for g in groups:
            if compare_answer_detailed(g[0]["extracted_answer"], s["extracted_answer"])["answer_status"] == "correct":
                g.append(s)
                break
        else:
            groups.append([s])
    best = max(groups, key=len)
    return best[0]["extracted_answer"], best


def observations(steps: list[str], flagged: int | None) -> list[str]:
    """Four observations from the wrong attempt: its first two steps (how it read the problem), the step JUDGE
    flagged, and the last step before the answer."""
    picks = [0, 1] + ([flagged] if flagged is not None else []) + [len(steps) - 2, 2, 3]
    out, used = [], set()
    for i in picks:
        if 0 <= i < len(steps) and i not in used and len(out) < 4:
            used.add(i)
            out.append((i, steps[i]))
    return [re.sub(r"\s+", " ", s)[:OBS_CHARS] for _, s in sorted(out)]


def parse_judge(text: str) -> dict:
    decision, step = baseline.parse_judge_response(text)
    m = EXPLANATION.search(text or "")
    return {"decision": decision, "step": step, "gate": judge_gate(text),
            "explanation": re.sub(r"\s+", " ", m.group(1)).strip() if m else None}


def agents(a) -> None:
    out = Path(a.out)
    rows = solve_rows()
    census_rows = read_jsonl(sorted((out / "census").glob("shard*.jsonl")))
    by_uid = collections.defaultdict(list)
    for r in census_rows:
        by_uid[r["uid"]].append(r)
    dead = []
    for u, samples in by_uid.items():
        if any(s["correct_strict"] for s in samples) and not a.any_wrong:
            continue
        wrong = [s for s in samples if s["answer_status"] == "incorrect" and s["finish_reason"] == "stop"
                 and not s["gate"]]
        if len(wrong) >= (1 if a.any_wrong else a.min_wrong):  # failures are real wrong answers, not caps or unverifiable formats
            dead.append((u, wrong))
    print(f"census: {len(by_uid)} problems, {len(dead)} eligible dead problems", flush=True)

    items = []
    for u, wrong in dead:
        answer, members = modal_wrong(wrong)
        rep = min(members, key=lambda s: len(s["text"]))
        steps = to_steps(rep["text"])
        items.append({"uid": u, "question": rows[u]["question"], "true_answer": rows[u]["final_answer"],
                      "wrong_answer": answer, "wrong_count": len(members), "n_wrong": len(wrong),
                      "attempt_sample": rep["sample"], "steps": steps})

    eng = Engine(a.base, Path(a.adapters), 32768)
    # JUDGE: the attempt as a numbered proposed solution.
    tmpl = baseline.PROMPT_FILES["judge"].read_text(encoding="utf-8").strip()
    judge_prompts = []
    for it in items:
        judge_input = (f"Problem:\n{it['question']}\n\nProposed solution:\n"
                       + "\n".join(f"S{i}: {s}" for i, s in enumerate(it["steps"], 1)) + f"\n\n{JUDGE_INSTRUCTION}")
        judge_prompts.append(render_template(tmpl, {"JUDGE_INPUT": judge_input}))
    for it, outs in zip(items, eng.chat(judge_prompts, "judge", AGENT_SAMPLES, AGENT_CAP), strict=True):
        parsed = [parse_judge(o["text"]) for o in outs]
        flagged = [p for p in parsed if p["decision"] == "incorrect" and p["step"] not in (None, "none")
                   and not p["gate"] and p["explanation"]]
        it["judge_raw"] = [{"text": o["text"], **p} for o, p in zip(outs, parsed)]
        it["judge_said_incorrect"] = len(flagged)
        if flagged:
            step = collections.Counter(p["step"] for p in flagged).most_common(1)[0][0]
            choice = next(p for p in flagged if p["step"] == step)
            it["judge_step"], it["judge_explanation"] = step, choice["explanation"]
        else:
            it["judge_step"], it["judge_explanation"] = None, None

    # RECONSTRUCT: the wrong answer plus observations from the attempt -> the question it answers.
    tmpl = baseline.PROMPT_FILES["reconstruct"].read_text(encoding="utf-8").strip()
    recon_prompts = []
    for it in items:
        flagged = int(it["judge_step"][1:]) - 1 if it["judge_step"] else None
        it["observations"] = observations(it["steps"], flagged)
        recon_prompts.append(render_template(tmpl, {
            "FINAL_ANSWER": it["wrong_answer"],
            "RENDERED_CLUES": "\n".join(f"{n}. {c}" for n, c in enumerate(it["observations"], 1))}))
    for it, outs in zip(items, eng.chat(recon_prompts, "reconstruct", AGENT_SAMPLES, AGENT_CAP), strict=True):
        cands = []
        for o in outs:
            rec, method = baseline.extract_reconstruction_last(o["text"])
            q = (rec or {}).get("question")
            cands.append({"text": o["text"], "method": method, "question": q,
                          "gate": reconstruct_gate(it["wrong_answer"], q) if q else ["unparseable"]})
        for c in cands:
            if c["question"] and ADDRESSES_READER.search(c["question"]):
                c["gate"] = c["gate"] + ["addresses_reader"]
        # Distinct gate-passing questions; each is checked below.
        it["recon_raw"] = cands
        it["recon_candidates"] = list(dict.fromkeys(c["question"] for c in cands if c["question"] and not c["gate"]))

    # SOLVE specialist: which rebuilt question really has the wrong answer (and not the true one)?
    todo = [(it, q) for it in items for q in it["recon_candidates"]]
    probe = {"task": "solve", "uid": "probe", "broad_topic": "", "difficulty": 0}
    outs = eng.chat([solve_prompt({**probe, "question": q}) for _, q in todo], "solve", AGENT_SAMPLES, SOLVE_CAP)
    for it in items:
        it["recon_checks"] = []
    for (it, q), samples in zip(todo, outs, strict=True):
        answers = [baseline.extract_solve_answer(s["text"])[0] for s in samples]
        it["recon_checks"].append({
            "question": q, "answers": answers,
            "wrong": sum(compare_answer_detailed(it["wrong_answer"], x)["answer_status"] == "correct" for x in answers),
            "true": sum(compare_answer_detailed(it["true_answer"], x)["answer_status"] == "correct" for x in answers)})
    for it in items:
        best = max(it["recon_checks"], key=lambda c: (c["wrong"] - c["true"], c["wrong"]), default=None)
        it["recon_question"] = best["question"] if best else None
        it["recon_check_wrong"] = best["wrong"] if best else None
        it["recon_check_true"] = best["true"] if best else None
        # Certified: the SOLVE specialist reaches the wrong answer more often than the true one, at least twice
        # (or once with the true answer never reached).
        it["recon_certified"] = bool(best) and best["wrong"] > best["true"] and (best["wrong"] >= 2 or best["true"] == 0)

    for it in items:
        it["hints"] = build_hints(it)
    write_jsonl(out / "agents.jsonl", items)


def build_hints(it: dict) -> dict:
    """Hints are templates around the agents' outputs; a hint that writes the true answer is dropped."""
    judge = recon = None
    if it.get("judge_explanation"):
        judge = (f"Hint: an earlier attempt at this problem went wrong at the following point. "
                 f"{it['judge_explanation']}")
    if it.get("recon_question") and it.get("recon_certified"):
        recon = (f"Hint: an earlier attempt actually solved a different problem, namely \"{it['recon_question']}\" "
                 f"and got {it['wrong_answer']}, which is not the answer here. Compare that problem with the one "
                 f"above and use every condition exactly as stated.")
    hints = {"none": None, "judge": judge, "recon": recon,
             "both": f"{recon}\n{judge}" if judge and recon else None}
    for k, h in hints.items():
        if h and leaks(it["true_answer"], h, it.get("question", "")):
            hints[k] = None
            it.setdefault("leaked_arms", []).append(k)
    return hints


CORRECT_PHRASE = re.compile(r"\b(correct|right|true|actual)\s+(answer|value|result|limit|sum)\s+(is|should be|=|equals)",
                            re.I)


def leaks(true_answer: str, hint: str, question: str) -> bool:
    """The repository rule (LaTeX form of the answer in the text) plus three cases it skips on purpose for questions:
    a plain a/b form of a fraction, a "the correct value is" phrase, and a short integer answer that the hint
    writes although the problem itself does not."""
    if _answer_written(true_answer, hint) or CORRECT_PHRASE.search(hint):
        return True
    norm = lambda s: re.sub(r"[\s$]|\\[,;!]|\\left|\\right", "", s.replace("\\dfrac", "\\frac")).lower()  # noqa: E731
    a = norm(true_answer)
    plain = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"\1/\2", a)
    if plain != a and len(plain) >= 3 and plain in norm(hint):
        return True
    if re.fullmatch(r"-?\d{1,2}", a):
        has = lambda s: re.search(rf"(?<![\d.]){re.escape(a)}(?![\d.])", s) is not None  # noqa: E731
        return has(hint) and not has(question)
    return False


# ------------------------------------------------------------------ follow-up (after the first test)

FOLLOWUP_ARMS = ("wrong_only", "judge16k")


def followup_agents(a) -> None:
    """Two checks on the first result: JUDGE again with a 16k cap (most 4k answers were cut off mid-reasoning),
    and a control hint that only says the earlier wrong answer is wrong, to separate RECONSTRUCT's contribution
    from that sentence, which the RECONSTRUCT hint also contains."""
    out = Path(a.out)
    items = read_jsonl([out / "agents.jsonl"])
    tmpl = baseline.PROMPT_FILES["judge"].read_text(encoding="utf-8").strip()
    prompts = [render_template(tmpl, {"JUDGE_INPUT": (
        f"Problem:\n{it['question']}\n\nProposed solution:\n"
        + "\n".join(f"S{i}: {s}" for i, s in enumerate(it["steps"], 1)) + f"\n\n{JUDGE_INSTRUCTION}")})
        for it in items]
    eng = Engine(a.base, Path(a.adapters), 32768)
    for it, outs in zip(items, eng.chat(prompts, "judge", AGENT_SAMPLES, SOLVE_CAP), strict=True):
        parsed = [parse_judge(o["text"]) for o in outs]
        flagged = [p for p in parsed if p["decision"] == "incorrect" and p["step"] not in (None, "none")
                   and not p["gate"] and p["explanation"]]
        it["judge16k_raw"] = [{"text": o["text"], "finish_reason": o["finish_reason"], **p} for o, p in zip(outs, parsed)]
        if flagged:
            step = collections.Counter(p["step"] for p in flagged).most_common(1)[0][0]
            it["judge16k_step"] = step
            it["judge16k_explanation"] = next(p for p in flagged if p["step"] == step)["explanation"]
        hints = {
            "wrong_only": f"Hint: an earlier attempt at this problem got {it['wrong_answer']}, which is not the answer here.",
            "judge16k": (f"Hint: an earlier attempt at this problem went wrong at the following point. "
                         f"{it['judge16k_explanation']}") if it.get("judge16k_explanation") else None}
        for k, h in hints.items():
            if h and leaks(it["true_answer"], h, it["question"]):
                hints[k] = None
                it.setdefault("followup_leaked_arms", []).append(k)
        it["followup_hints"] = hints
    write_jsonl(out / "agents_followup.jsonl", items)


def followup_test(a) -> None:
    out = Path(a.out)
    rows = solve_rows()
    items = read_jsonl([out / "agents_followup.jsonl"])[a.shard::a.nshards]
    jobs = [(it["uid"], arm, it["followup_hints"][arm]) for it in items for arm in FOLLOWUP_ARMS
            if it["followup_hints"].get(arm)]
    eng = Engine(a.base, Path(a.adapters), SOLVE_CAP + 8192)
    outs = eng.chat([solve_prompt(rows[u], h) for u, _, h in jobs], "mixed", SAMPLES, SOLVE_CAP, seed=1)
    records = [{"uid": u, "arm": arm, "sample": k, "hint": hint, **resp, **score(rows[u], resp)}
               for (u, arm, hint), samples in zip(jobs, outs, strict=True) for k, resp in enumerate(samples)]
    write_jsonl(out / "test_followup" / f"shard{a.shard}.jsonl", records)


# ------------------------------------------------------------------ stage 3: test

def test(a) -> None:
    out = Path(a.out)
    rows = solve_rows()
    items = read_jsonl([out / "agents.jsonl"])[a.shard::a.nshards]
    jobs = [(it["uid"], arm, it["hints"].get(arm)) for it in items for arm in ARMS
            if arm == "none" or it["hints"].get(arm)]
    eng = Engine(a.base, Path(a.adapters), SOLVE_CAP + 8192)
    outs = eng.chat([solve_prompt(rows[u], h) for u, _, h in jobs], "mixed", SAMPLES, SOLVE_CAP, seed=1)
    records = []
    for (u, arm, hint), samples in zip(jobs, outs, strict=True):
        for k, resp in enumerate(samples):
            records.append({"uid": u, "arm": arm, "sample": k, "hint": hint, **resp, **score(rows[u], resp)})
    write_jsonl(out / "test" / f"shard{a.shard}.jsonl", records)


# ------------------------------------------------------------------ stage 4: report

def report(a) -> None:
    out = Path(a.out)
    census_rows = read_jsonl(sorted((out / "census").glob("shard*.jsonl")))
    per_uid = collections.defaultdict(int)
    for r in census_rows:
        per_uid[r["uid"]] += r["correct_strict"]
    hist = collections.Counter(per_uid.values())
    items = read_jsonl([out / "agents.jsonl"])
    tests = read_jsonl(sorted((out / "test").glob("shard*.jsonl")) + sorted((out / "test_followup").glob("shard*.jsonl")))
    by = collections.defaultdict(list)
    for r in tests:
        by[(r["uid"], r["arm"])].append(r["correct_strict"])

    arms = {}
    for arm in ARMS + FOLLOWUP_ARMS:
        groups = [v for (u, ar), v in by.items() if ar == arm]
        if not groups:
            continue
        k = [sum(v) for v in groups]
        arms[arm] = {"problems": len(groups), "mean_accuracy": sum(k) / (SAMPLES * len(groups)),
                     "solved_at_least_once": sum(x > 0 for x in k), "learnable_1_to_7": sum(0 < x < SAMPLES for x in k),
                     "always_solved": sum(x == SAMPLES for x in k)}
    # Paired view: problems that have the no-hint control, the RECONSTRUCT hint and the wrong-answer-only control.
    paired_arms = ("none", "wrong_only", "recon")
    full = [it["uid"] for it in items if all((it["uid"], arm) in by for arm in paired_arms)]
    paired = {arm: sum(sum(by[(u, arm)]) for u in full) / (SAMPLES * len(full)) if full else None for arm in paired_arms}
    paired_solved = {arm: sum(sum(by[(u, arm)]) > 0 for u in full) for arm in paired_arms}
    # A hint saying "Yes is not the answer" gives the answer away on a Yes/No problem; report those separately.
    binary = {it["uid"] for it in items if re.sub(r"[^a-z]", "", it["true_answer"].lower()) in ("yes", "no", "true", "false")}
    split = {}
    for name, keep in (("binary_answer", lambda u: u in binary), ("other_answer", lambda u: u not in binary)):
        us = [u for u in full if keep(u)]
        split[name] = {"problems": len(us), **{arm: {"correct": sum(sum(by[(u, arm)]) for u in us),
                                                     "solved_at_least_once": sum(sum(by[(u, arm)]) > 0 for u in us)}
                                               for arm in paired_arms}}

    rec = [it for it in items if it.get("recon_question")]
    summary = {
        "census": {"problems": len(per_uid), "samples": len(census_rows),
                   "histogram_correct_of_8": {str(k): hist.get(k, 0) for k in range(SAMPLES + 1)},
                   "dead_hard": hist.get(0, 0), "dead_easy": hist.get(SAMPLES, 0)},
        "agents": {"eligible_dead": len(items),
                   "judge_flagged_a_step": sum(bool(it.get("judge_step")) for it in items),
                   "judge_said_correct_majority": sum(
                       sum(j["decision"] == "correct" for j in it.get("judge_raw", [])) >= 3 for it in items),
                   "recon_any_valid_question": len(rec),
                   "recon_certified_wrong_answer": sum(bool(it.get("recon_certified")) for it in items),
                   "recon_best_has_true_answer": sum((it.get("recon_check_true") or 0) >= 2 for it in rec),
                   "hints_dropped_for_leak": sum(len(it.get("leaked_arms", [])) for it in items)},
        "arms": arms, "paired_problems": len(full), "paired_accuracy": paired, "paired_solved_at_least_once": paired_solved,
        "paired_by_answer_type": split,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    lines = ["# Phase-2 hint pilot", "", "## Census (mixed step 75, 8 samples, seen SOLVE pool)", "",
             f"{summary['census']['problems']} problems. Correct-of-8 histogram: "
             + ", ".join(f"{k}: {v}" for k, v in summary["census"]["histogram_correct_of_8"].items()), "",
             "## Agents", "", json.dumps(summary["agents"], indent=1), "", "## Hint arms", "",
             "| Arm | Problems | Mean acc | Solved ≥1/8 | 1–7/8 | 8/8 |", "|---|---|---|---|---|---|"]
    for arm, s in arms.items():
        lines.append(f"| {arm} | {s['problems']} | {s['mean_accuracy']:.3f} | {s['solved_at_least_once']} | "
                     f"{s['learnable_1_to_7']} | {s['always_solved']} |")
    lines += ["", f"Paired over {len(full)} problems with the none / wrong_only / recon arms: "
              + ", ".join(f"{k} {v:.3f}" for k, v in paired.items() if v is not None), "",
              "By answer type (correct samples out of 8 per problem; solved at least once):", "",
              "```", json.dumps(split, indent=1), "```", "", "## Examples", ""]
    for it in items[:8]:
        acc = {arm: sum(by.get((it["uid"], arm), [])) for arm in ARMS if (it["uid"], arm) in by}
        lines += [f"### {it['uid']}", "", f"**Problem:** {it['question']}", "",
                  f"**True answer:** {it['true_answer']} · **modal wrong answer:** {it['wrong_answer']} "
                  f"({it['wrong_count']}/{it['n_wrong']} wrong attempts)", "",
                  f"**JUDGE:** step {it.get('judge_step')} — {it.get('judge_explanation')}", "",
                  f"**RECONSTRUCT:** {it.get('recon_question')} (SOLVE check: wrong answer "
                  f"{it.get('recon_check_wrong')}/4, true answer {it.get('recon_check_true')}/4, "
                  f"certified {it.get('recon_certified')})", "",
                  f"**Correct of 8 by arm:** {acc}", ""]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["census", "agents", "test", "followup-agents", "followup-test", "report"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default="", help="local path of Qwen/Qwen3.5-2B")
    ap.add_argument("--adapters", default=str(Path.home() / "anlp-final-adapters"))
    ap.add_argument("--pool", type=int, default=750)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--min-wrong", type=int, default=5,
                    help="a dead problem needs at least this many verified-wrong, uncapped, ungated answers")
    ap.add_argument("--any-wrong", action="store_true", help="smoke test only: use any problem with a wrong answer")
    a = ap.parse_args()
    {"census": census, "agents": agents, "test": test, "followup-agents": followup_agents,
     "followup-test": followup_test, "report": report}[a.stage](a)


if __name__ == "__main__":
    main()
