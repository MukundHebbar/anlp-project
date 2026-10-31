#!/usr/bin/env python3
"""Two experiments with the functional specialists (JUDGE checks a derivation, RECONSTRUCT infers the question
from an answer and partial evidence, SOLVE writes the derivation).

TUTOR: mark a student's worked solution as correct, wrong at step k, or a misread question (the mathematics is right
but it answers a slightly different problem). JUDGE finds the wrong step; RECONSTRUCT rebuilds the question the
solution answers, and a comparator decides whether that is the problem the student was given.
  Items: the 400 JUDGE test solutions (200 correct, 200 with a labelled first wrong step) plus misread items made
  from the correct ones: the 27B changes one condition of the problem so the (unchanged) solution no longer
  answers it, and the change is kept only if the 27B's own answers to the new problem agree and differ from the
  solution's answer.

DRIFT: does RECONSTRUCT, run on growing prefixes of a solution, notice the solver drifting to a different problem,
including drift that JUDGE cannot see because no step is mathematically wrong? Solver: the mixed model on the
200-question SOLVE dev slice (never trained on), 4 attempts each. Flags are tested by repairing flagged attempts
from the flagged point (keep the earlier steps, regenerate the rest) and comparing with random and oracle flags.

Agents: two role sets, the specialists (JUDGE and RECONSTRUCT adapters) and the mixed model in both roles.
Comparator: Qwen3.8-27B served by vLLM, read as one Yes/No token (as in qwen_judging.py).

Stages (results under --out):
  tutor-build                  27B: misread items, student answers            -> tutor/items.jsonl
  tutor-run      --shard i/k   2B : JUDGE and RECONSTRUCT on every item        -> tutor/agents-shard*.jsonl
  tutor-compare                27B: rebuilt question vs given / solved problem -> tutor/compare.jsonl
  drift-attempts --shard i/k   2B : mixed model, 4 attempts per dev problem    -> drift/attempts-shard*.jsonl
  drift-critics  --shard i/k   2B : JUDGE on attempts, RECONSTRUCT on prefixes -> drift/critics-shard*.jsonl
  drift-compare                27B: rebuilt prefix questions vs the problem    -> drift/compare.jsonl
  drift-repair   --shard i/k   2B : repair flagged attempts                    -> drift/repair-shard*.jsonl
  report                             tutor/report.md, drift/report.md, summary.json
"""

from __future__ import annotations

import argparse
import collections
import json
import random
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE))
import hint_pilot as hp  # noqa: E402
from anlp_project import baseline, opd  # noqa: E402
from anlp_project.qwen_judging import SYSTEM, label_probs  # noqa: E402
from anlp_project.reconstruct import render_template  # noqa: E402
from anlp_project.solution_verification import compare_answer_detailed  # noqa: E402
from anlp_project.strict_gates import reconstruct_gate  # noqa: E402

ROLESETS = {"spec": {"judge": "judge", "recon": "reconstruct"}, "mixed": {"judge": "mixed", "recon": "mixed"}}
ATTEMPTS = 4
SOLVE_CAP = 16384
REPAIR_CAP = 12288
JUDGE_CAP = 8192
RECON_CAP = 4096
OBS_CHARS = 600

# Comparator: does the rebuilt question B contradict problem A? A rebuilt question often restates A loosely, leaves
# details out, or writes in values the solution derived; none of that counts. Read as P(Yes) = P(contradiction).
CONTRADICT = ("QUESTION A is a mathematics problem. QUESTION B was reconstructed from a worked solution, so it may "
              "restate A in other words, give fewer details, or include facts and intermediate values that the solution "
              "derived. Ignore those differences.\n\nQUESTION A:\n{a}\n\nQUESTION B:\n{b}\n\nDoes B contradict A: a "
              "different value for a quantity A gives, a different condition or constraint, or a different requested "
              "quantity?\n\nReply Yes if B contradicts A, or No if it does not.")
# Used only to check that a perturbed problem really differs from the original (both are complete problems).
SAME = ("QUESTION A:\n{a}\n\nQUESTION B:\n{b}\n\nDo A and B pose the same mathematical problem: the same given "
        "conditions (values, relations, constraints) and the same requested quantity? Rewording, renaming or an "
        "equivalent formulation counts as the same. A changed value, an added or dropped condition, or a different "
        "requested quantity counts as different.\n\nReply with Yes or No only.")
PERTURB = ("Here is a mathematics problem and a correct solution to it.\n\nPROBLEM:\n{p}\n\nSOLUTION:\n{s}\n\n"
           "Write a new version of the problem that changes exactly one condition (for example a number, a bound, a "
           "relation, or which quantity is requested) so that the solution above no longer solves it. Keep everything "
           "else, including the wording, the same. The new problem must be well posed and solvable. Output only the "
           "text of the new problem.")
EXTRACT = ("Here is a worked solution to a problem.\n\nPROBLEM:\n{p}\n\nSOLUTION:\n{s}\n\nWhat final answer does this "
           "solution arrive at? Reply with the final answer only, as a short mathematical expression or word.")


# ------------------------------------------------------------------ shared helpers

def numbered(steps: list[str]) -> str:
    return "\n".join(f"S{i}: {s}" for i, s in enumerate(steps, 1))


def judge_prompt(problem: str, steps: list[str]) -> str:
    tmpl = baseline.PROMPT_FILES["judge"].read_text(encoding="utf-8").strip()
    return render_template(tmpl, {"JUDGE_INPUT": f"Problem:\n{problem}\n\nProposed solution:\n{numbered(steps)}"
                                                 f"\n\n{hp.JUDGE_INSTRUCTION}"})


def recon_prompt(answer: str, obs: list[str]) -> str:
    tmpl = baseline.PROMPT_FILES["reconstruct"].read_text(encoding="utf-8").strip()
    return render_template(tmpl, {"FINAL_ANSWER": answer,
                                  "RENDERED_CLUES": "\n".join(f"{n}. {c}" for n, c in enumerate(obs, 1))})


def pick_obs(steps: list[str], idx: list[int]) -> list[str]:
    out = []
    for i in idx:
        if 0 <= i < len(steps) and i not in [j for j, _ in out]:
            out.append((i, steps[i]))
    return [re.sub(r"\s+", " ", s)[:OBS_CHARS] for _, s in sorted(out)[:4]]


def judge_vote(texts: list[str]) -> dict:
    parsed = [hp.parse_judge(t) for t in texts]
    ok = [p for p in parsed if p["decision"] and not p["gate"]]
    inc = [p for p in ok if p["decision"] == "incorrect" and p["step"] not in (None, "none")]
    verdict = None
    if ok:
        verdict = "incorrect" if len(inc) * 2 > len(ok) else "correct"
    step = collections.Counter(p["step"] for p in inc).most_common(1)[0][0] if verdict == "incorrect" else None
    expl = next((p["explanation"] for p in inc if p["step"] == step), None) if step else None
    return {"verdict": verdict, "step": step, "explanation": expl,
            "votes": [(p["decision"], p["step"]) for p in parsed]}


def recon_pick(texts: list[str], answer: str) -> str | None:
    for t in texts:
        rec, _ = baseline.extract_reconstruction_last(t)
        q = (rec or {}).get("question")
        if q and not reconstruct_gate(answer, q) and not hp.ADDRESSES_READER.search(q):
            return q
    return None


YESNO = {"yes": "yes", "true": "yes", "no": "no", "false": "no"}


def _yesno(x) -> str | None:
    m = re.match(r"\W*(?:\\text\{)?\s*([A-Za-z]+)", str(x))
    return YESNO.get(m.group(1).lower()) if m else None


def same_answer(a, b) -> bool:
    """Checker v3 equivalence, plus Yes/No answers compared by their first word ("Yes, k is finite" = "Yes")."""
    if a is None or b is None:
        return False
    ya, yb = _yesno(a), _yesno(b)
    if ya and yb:
        return ya == yb
    return compare_answer_detailed(str(a), str(b))["answer_status"] == "correct"


def auroc(pos: list[float], neg: list[float]) -> float | None:
    """Probability that a random positive scores above a random negative (ties count half)."""
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def shard_paths(out: Path, stem: str) -> list[Path]:
    return sorted(out.glob(f"{stem}-shard*.jsonl"))


class Big:
    """Client for the 27B served by vLLM (OpenAI completions API); the chat template is rendered here."""

    def __init__(self, path: str, port: int):
        from transformers import AutoTokenizer

        self.tok = AutoTokenizer.from_pretrained(path)
        self.url = f"http://127.0.0.1:{port}/v1/completions"

    def render(self, user: str, system: str | None = None, prefix: str = "") -> str:
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
        return self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                            enable_thinking=False) + prefix

    def _post(self, body: dict) -> dict:
        req = urllib.request.Request(self.url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=7200) as r:
                    return json.loads(r.read())
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(15)

    def complete(self, prompts: list[str], max_tokens: int, temperature: float = 0.0, n: int = 1,
                 logprobs: int | None = None, chunk: int = 8) -> list[list[dict]]:
        def one(i):
            batch = prompts[i:i + chunk]
            body = {"model": "big", "prompt": batch, "max_tokens": max_tokens, "temperature": temperature, "n": n}
            if logprobs:
                body["logprobs"] = logprobs
            res = [[None] * n for _ in batch]
            for c in self._post(body)["choices"]:
                res[c["index"] // n][c["index"] % n] = c
            return res
        with ThreadPoolExecutor(16) as ex:
            parts = list(ex.map(one, range(0, len(prompts), chunk)))
        return [r for p in parts for r in p]

    def p_yes(self, users: list[str]) -> list[float]:
        outs = self.complete([self.render(u, SYSTEM, "Answer: ") for u in users], 1, 0.0, 1, logprobs=20)
        return [label_probs(o[0]["logprobs"]["top_logprobs"][0], ["Yes", "No"])[0][0] for o in outs]

    def text(self, users: list[str], max_tokens: int, temperature: float = 0.0, n: int = 1,
             system: str | None = None) -> list[list[str]]:
        outs = self.complete([self.render(u, system) for u in users], max_tokens, temperature, n)
        return [[c["text"].strip() for c in o] for o in outs]


def big(a) -> Big:
    return Big(a.big_path, a.port)


def engine(a, max_len: int = 32768) -> hp.Engine:
    return hp.Engine(a.base, Path(a.adapters), max_len)


def gen(eng: hp.Engine, prompts: list[str], adapter: str, n: int, cap: int) -> list[list[str]]:
    return [[o["text"] for o in outs] for outs in eng.chat(prompts, adapter, n, cap)]


# ------------------------------------------------------------------ TUTOR

def tutor_build(a) -> None:
    out = Path(a.out) / "tutor"
    out.mkdir(parents=True, exist_ok=True)
    rows = baseline.load_rows("judge", "test")
    if a.limit:  # smoke test: the first `limit` correct and `limit` incorrect items
        rows = [r for r in rows if r["label"] == "correct"][:a.limit] + [r for r in rows if r["label"] != "correct"][:a.limit]
    items = []
    for r in rows:
        steps = [s["text"] for s in r["public"]["proposed_solution"]]
        base = {"source_uid": r["uid"], "problem": r["public"]["problem"], "steps": steps}
        if r["label"] == "correct":
            items.append({**base, "uid": f"{r['uid']}-correct", "label": "correct", "key": r["final_answer"],
                          "student_answer": r["final_answer"]})
        else:
            items.append({**base, "uid": f"{r['uid']}-step", "label": "step", "key": r["final_answer"],
                          "true_step": r["private"]["first_error_step_id"]})
    b = big(a)
    # The answer each step-error solution arrives at.
    steps_items = [it for it in items if it["label"] == "step"]
    for it, o in zip(steps_items, b.text([EXTRACT.format(p=it["problem"], s=numbered(it["steps"]))
                                          for it in steps_items], 96), strict=True):
        it["student_answer"] = o[0].splitlines()[0].strip().strip("$").strip() if o[0] else ""
    # Misread items: change one condition of a correct item's problem; keep it only if it verifiably matters.
    correct = [it for it in items if it["label"] == "correct"]
    perturbed = b.text([PERTURB.format(p=it["problem"], s=numbered(it["steps"])) for it in correct], 1024, 0.7)
    cands = [(it, o[0]) for it, o in zip(correct, perturbed, strict=True) if o[0] and o[0] != it["problem"]]
    solves = b.text([baseline.render_prompt({"task": "solve", "question": p}) for _, p in cands], 6144, 0.7, 4)
    differ = b.p_yes([SAME.format(a=it["problem"], b=p) for it, p in cands])
    for (it, p), answers, p_same in zip(cands, solves, differ, strict=True):
        ext = [baseline.extract_solve_answer(t)[0] for t in answers]
        groups: list[list[str]] = []
        for x in ext:
            if x is None:
                continue
            g = next((g for g in groups if same_answer(g[0], x)), None)
            g.append(x) if g else groups.append([x])
        best = max(groups, key=len, default=[])
        rec = {"source_uid": it["source_uid"], "candidate": p, "answers": ext, "p_same_as_original": p_same}
        if len(best) >= 3 and not same_answer(best[0], it["student_answer"]) and p_same < 0.5:
            items.append({"uid": f"{it['source_uid']}-misread", "source_uid": it["source_uid"], "label": "misread",
                          "problem": p, "steps": it["steps"], "key": best[0], "student_answer": it["student_answer"],
                          "solved_question": it["problem"], "build": rec})
        else:
            with (out / "misread-rejected.jsonl").open("a") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    hp.write_jsonl(out / "items.jsonl", items)
    print(collections.Counter(it["label"] for it in items), flush=True)


def tutor_run(a) -> None:
    out = Path(a.out) / "tutor"
    items = hp.read_jsonl([out / "items.jsonl"])[a.shard::a.nshards]
    eng = engine(a)
    for name, roles in ROLESETS.items():
        jt = gen(eng, [judge_prompt(it["problem"], it["steps"]) for it in items], roles["judge"], 4, JUDGE_CAP)
        rp = []
        for it in items:
            s = it["steps"]
            rp.append(recon_prompt(it["student_answer"] or "", pick_obs(s, [0, 1, len(s) // 2, len(s) - 1])))
        rt = gen(eng, rp, roles["recon"], 2, RECON_CAP)
        for it, j, r in zip(items, jt, rt, strict=True):
            it[f"{name}_judge"] = judge_vote(j)
            it[f"{name}_recon"] = recon_pick(r, it["student_answer"] or "")
            it[f"{name}_recon_raw"] = r
    hp.write_jsonl(out / f"agents-shard{a.shard}.jsonl", items)


def tutor_compare(a) -> None:
    out = Path(a.out) / "tutor"
    items = hp.read_jsonl(shard_paths(out, "agents"))
    b = big(a)
    jobs = []
    for it in items:
        for name in ROLESETS:
            q = it.get(f"{name}_recon")
            if q:
                jobs.append((it["uid"], name, "given", CONTRADICT.format(a=it["problem"], b=q)))
                if it["label"] == "misread":
                    jobs.append((it["uid"], name, "solved", CONTRADICT.format(a=it["solved_question"], b=q)))
    ps = [1.0 - p for p in b.p_yes([j[3] for j in jobs])]  # p_same = 1 - P(contradiction)
    hp.write_jsonl(out / "compare.jsonl", [{"uid": u, "roleset": n, "against": w, "p_same": p}
                                           for (u, n, w, _), p in zip(jobs, ps, strict=True)])


def tutor_report(out: Path) -> dict:
    items = hp.read_jsonl(shard_paths(out, "agents"))
    cmp_ = {(c["uid"], c["roleset"], c["against"]): c["p_same"] for c in hp.read_jsonl([out / "compare.jsonl"])}
    labels = ("correct", "step", "misread")
    summary = {"items": dict(collections.Counter(it["label"] for it in items))}
    lines = ["# Tutor experiment", "", f"Items: {summary['items']}", ""]
    for name in ROLESETS:
        rs = {}
        for lab in labels:
            sub = [it for it in items if it["label"] == lab]
            if not sub:
                continue
            n = len(sub)
            jv = [it[f"{name}_judge"] for it in sub]
            rec = [it for it in sub if it.get(f"{name}_recon")]
            flag = [it for it in rec if cmp_.get((it["uid"], name, "given"), 1.0) < 0.5]
            key_wrong = [it for it in sub if not same_answer(it["key"], it["student_answer"])]
            d = {"n": n,
                 "judge_says_incorrect": sum(j["verdict"] == "incorrect" for j in jv) / n,
                 "judge_no_verdict": sum(j["verdict"] is None for j in jv) / n,
                 "recon_question_rate": len(rec) / n,
                 "misread_flag_rate": len(flag) / n,
                 "student_answer_differs_from_key": len(key_wrong) / n}
            if lab == "step":
                d["judge_exact_step"] = sum(j["step"] == it["true_step"] for j, it in zip(jv, sub)) / n
            if lab == "misread":
                d["rebuilt_matches_solved_question"] = sum(
                    cmp_.get((it["uid"], name, "solved"), 0.0) >= 0.5 for it in rec) / n
                d["rebuilt_matches_given_problem"] = sum(
                    cmp_.get((it["uid"], name, "given"), 0.0) >= 0.5 for it in rec) / n
            # Tutor decisions. key-aware: a right final answer is "correct"; otherwise misread if flagged, else step.
            def decide(it, use_recon: bool, key_aware: bool) -> str:
                if key_aware and same_answer(it["key"], it["student_answer"]):
                    return "correct"
                if use_recon and it.get(f"{name}_recon") and cmp_.get((it["uid"], name, "given"), 1.0) < 0.5:
                    return "misread"
                j = it[f"{name}_judge"]
                return "step" if j["verdict"] == "incorrect" or (key_aware and j["verdict"] != "incorrect") else "correct"
            for tag, ur, ka in (("judge_only", False, False), ("judge+recon", True, False),
                                ("key+judge", False, True), ("key+judge+recon", True, True)):
                d[f"decision[{tag}]"] = dict(collections.Counter(decide(it, ur, ka) for it in sub))
            rs[lab] = d
        score = lambda it: (1.0 - cmp_[(it["uid"], name, "given")]) if (it["uid"], name, "given") in cmp_ else 0.0  # noqa: E731
        by_lab = {lab: [score(it) for it in items if it["label"] == lab] for lab in labels}
        rs["auroc_misread_vs_correct"] = auroc(by_lab["misread"], by_lab["correct"])
        rs["auroc_misread_vs_step"] = auroc(by_lab["misread"], by_lab["step"])
        summary[name] = rs
        lines += [f"## Agents: {name}", "", "```", json.dumps(rs, indent=1), "```", ""]
    lines += ["## Misread examples", ""]
    for it in [x for x in items if x["label"] == "misread"][:6]:
        lines += [f"**Given:** {it['problem']}", "", f"**Solution actually answers:** {it['solved_question']}", "",
                  f"**RECONSTRUCT (spec):** {it.get('spec_recon')} — p_same(given) "
                  f"{cmp_.get((it['uid'], 'spec', 'given'))}", "",
                  f"**RECONSTRUCT (mixed):** {it.get('mixed_recon')} — p_same(given) "
                  f"{cmp_.get((it['uid'], 'mixed', 'given'))}", "",
                  f"**JUDGE (spec / mixed):** {it['spec_judge']['verdict']} {it['spec_judge']['step']} / "
                  f"{it['mixed_judge']['verdict']} {it['mixed_judge']['step']}", "", "---", ""]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    return summary


# ------------------------------------------------------------------ DRIFT

def checkpoints(n: int) -> list[int]:
    """1-based prefix ends at about a quarter, half, three quarters and all of the steps."""
    return sorted({max(1, round(n * f)) for f in (0.25, 0.5, 0.75, 1.0)})


def drift_attempts(a) -> None:
    out = Path(a.out) / "drift"
    rows = opd.slice_rows("solve", "dev")[:a.limit or None][a.shard::a.nshards]
    eng = engine(a, SOLVE_CAP + 4096)
    outs = eng.chat([hp.solve_prompt(r) for r in rows], "mixed", ATTEMPTS, SOLVE_CAP)
    recs = []
    for r, samples in zip(rows, outs, strict=True):
        for k, s in enumerate(samples):
            sc = hp.score(r, s)
            recs.append({"uid": r["uid"], "attempt": k, "problem": r["question"], "key": r["final_answer"],
                         "text": s["text"], "finish_reason": s["finish_reason"], "steps": hp.to_steps(s["text"]),
                         "answer": sc["extracted_answer"], "correct": sc["correct_strict"],
                         "answer_status": sc["answer_status"]})
    hp.write_jsonl(out / f"attempts-shard{a.shard}.jsonl", recs)


def drift_critics(a) -> None:
    out = Path(a.out) / "drift"
    atts = hp.read_jsonl(shard_paths(out, "attempts"))[a.shard::a.nshards]
    eng = engine(a)
    for name, roles in ROLESETS.items():
        jt = gen(eng, [judge_prompt(x["problem"], x["steps"]) for x in atts], roles["judge"], 2, JUDGE_CAP)
        jobs = []
        for i, x in enumerate(atts):
            if not x["answer"] or x["finish_reason"] != "stop":
                continue
            for c in checkpoints(len(x["steps"])):
                obs = pick_obs(x["steps"], [0, 1, c - 2, c - 1])
                jobs.append((i, c, recon_prompt(x["answer"], obs)))
        rt = gen(eng, [j[2] for j in jobs], roles["recon"], 1, RECON_CAP)
        for x, j in zip(atts, jt, strict=True):
            x[f"{name}_judge"] = judge_vote(j)
            x[f"{name}_recon"] = {}
        for (i, c, _), r in zip(jobs, rt, strict=True):
            atts[i][f"{name}_recon"][str(c)] = recon_pick(r, atts[i]["answer"])
    for x in atts:
        x.pop("text", None)
    hp.write_jsonl(out / f"critics-shard{a.shard}.jsonl", atts)


def drift_compare(a) -> None:
    out = Path(a.out) / "drift"
    atts = hp.read_jsonl(shard_paths(out, "critics"))
    b = big(a)
    jobs = [(x["uid"], x["attempt"], name, c, CONTRADICT.format(a=x["problem"], b=q))
            for x in atts for name in ROLESETS for c, q in x[f"{name}_recon"].items() if q]
    ps = [1.0 - p for p in b.p_yes([j[4] for j in jobs])]  # p = 1 - P(contradiction)
    hp.write_jsonl(out / "compare.jsonl", [{"uid": u, "attempt": k, "roleset": n, "checkpoint": int(c), "p": p}
                                           for (u, k, n, c, _), p in zip(jobs, ps, strict=True)])


def drift_flags(out: Path) -> tuple[list[dict], dict]:
    """Per attempt and role set: JUDGE flag and cut, drift flag and cut, and the variants' cut points."""
    atts = hp.read_jsonl(shard_paths(out, "critics"))
    cmp_ = collections.defaultdict(dict)
    for c in hp.read_jsonl([out / "compare.jsonl"]):
        cmp_[(c["uid"], c["attempt"], c["roleset"])][c["checkpoint"]] = c["p"]
    rng = random.Random(20261011)
    cuts = {}  # (uid, attempt, variant) -> number of steps kept
    for name in ROLESETS:
        for x in atts:
            key = (x["uid"], x["attempt"])
            j = x[f"{name}_judge"]
            jcut = int(j["step"][1:]) - 1 if j["verdict"] == "incorrect" and j["step"] else None
            x[f"{name}_judge_cut"] = jcut
            ps = cmp_.get((x["uid"], x["attempt"], name), {})
            dcut, prev = None, 0
            for c in checkpoints(len(x["steps"])):
                if c in ps and ps[c] < 0.5:
                    dcut = prev
                    break
                prev = c
            x[f"{name}_drift_cut"] = dcut
            x[f"{name}_drift_checkpoints"] = ps
            if jcut is not None:
                cuts[key + (f"{name}:judge",)] = jcut
            if dcut is not None:
                cuts[key + (f"{name}:drift",)] = dcut
            if jcut is not None or dcut is not None:
                cuts[key + (f"{name}:either",)] = min(c for c in (jcut, dcut) if c is not None)
        flagged = sum(1 for k in cuts if k[2] == f"{name}:either")
        for x in rng.sample(atts, flagged):  # random flags at the same rate as "either"
            cuts[(x["uid"], x["attempt"], f"{name}:random")] = rng.randrange(len(x["steps"]))
    for x in atts:  # oracle: every wrong attempt, random cut
        if not x["correct"]:
            cuts[(x["uid"], x["attempt"], "oracle")] = rng.randrange(len(x["steps"]))
    return atts, cuts


def drift_repair(a) -> None:
    out = Path(a.out) / "drift"
    atts, cuts = drift_flags(out)
    by = {(x["uid"], x["attempt"]): x for x in atts}
    pairs = sorted({(u, k, c) for (u, k, _), c in cuts.items()})[a.shard::a.nshards]
    rows = {r["uid"]: r for r in opd.slice_rows("solve", "dev")}
    eng = engine(a, SOLVE_CAP + 8192)
    tok = eng.llm.get_tokenizer()
    from vllm import SamplingParams
    texts = []
    for u, k, c in pairs:
        head = tok.apply_chat_template([{"role": "user", "content": hp.solve_prompt(rows[u])}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False)
        prefix = "\n\n".join(by[(u, k)]["steps"][:c])
        texts.append((head, prefix + ("\n\n" if prefix else "")))
    s = baseline.EVAL_SAMPLING
    params = SamplingParams(n=1, temperature=s["temperature"], top_p=s["top_p"], top_k=s["top_k"],
                            max_tokens=REPAIR_CAP, seed=2)
    outs = eng.llm.generate([h + p for h, p in texts], params, lora_request=eng.lora["mixed"], use_tqdm=False)
    recs = []
    for (u, k, c), (h, p), o in zip(pairs, texts, outs, strict=True):
        full = p + o.outputs[0].text
        sc = hp.score(rows[u], {"text": full, "finish_reason": str(o.outputs[0].finish_reason),
                                "completion_tokens": len(o.outputs[0].token_ids)})
        recs.append({"uid": u, "attempt": k, "cut": c, "correct": sc["correct_strict"], "answer": sc["extracted_answer"]})
    hp.write_jsonl(out / f"repair-shard{a.shard}.jsonl", recs)


def drift_report(out: Path) -> dict:
    atts, cuts = drift_flags(out)
    rep = {(r["uid"], r["attempt"], r["cut"]): r["correct"] for r in hp.read_jsonl(shard_paths(out, "repair"))}
    n = len(atts)
    wrong = [x for x in atts if not x["correct"]]
    right = [x for x in atts if x["correct"]]
    summary = {"attempts": n, "accuracy_none": len(right) / n, "wrong_attempts": len(wrong)}
    for name in ROLESETS:
        jf = lambda x: x[f"{name}_judge_cut"] is not None  # noqa: E731
        df = lambda x: x[f"{name}_drift_cut"] is not None  # noqa: E731
        summary[name] = {
            "judge_flag_rate_on_wrong": sum(map(jf, wrong)) / max(1, len(wrong)),
            "judge_flag_rate_on_correct": sum(map(jf, right)) / max(1, len(right)),
            "drift_flag_rate_on_wrong": sum(map(df, wrong)) / max(1, len(wrong)),
            "drift_flag_rate_on_correct": sum(map(df, right)) / max(1, len(right)),
            "wrong_with_drift_but_no_judge_flag": sum(df(x) and not jf(x) for x in wrong),
            "correct_with_drift_flag": sum(map(df, right)),
            "checkpoints_judged": sum(len(x[f"{name}_drift_checkpoints"]) for x in atts),
            # Threshold-free: highest contradiction probability over an attempt's checkpoints, wrong vs right.
            "auroc_drift_wrong_vs_correct": auroc(
                [max((1 - p for p in x[f"{name}_drift_checkpoints"].values()), default=0.0) for x in wrong],
                [max((1 - p for p in x[f"{name}_drift_checkpoints"].values()), default=0.0) for x in right]),
            "auroc_judge_flag_wrong_vs_correct": auroc([float(jf(x)) for x in wrong], [float(jf(x)) for x in right]),
        }
    variants = sorted({v for (_, _, v) in cuts})
    acc = {}
    for v in variants:
        total = 0
        for x in atts:
            c = cuts.get((x["uid"], x["attempt"], v))
            total += rep.get((x["uid"], x["attempt"], c), x["correct"]) if c is not None else x["correct"]
        acc[v] = {"accuracy": total / n, "repaired": sum(1 for k in cuts if k[2] == v)}
    summary["accuracy_after_one_repair"] = acc
    lines = ["# Drift experiment", "", "```", json.dumps(summary, indent=1), "```", "", "## Wrong attempts flagged by "
             "drift but not by JUDGE (mixed role set)", ""]
    for x in [x for x in wrong if x["mixed_drift_cut"] is not None and x["mixed_judge_cut"] is None][:5]:
        lines += [f"**{x['uid']}** attempt {x['attempt']} answer {x['answer']} (key {x['key']}); "
                  f"drift checkpoints {x['mixed_drift_checkpoints']}", "",
                  f"Problem: {x['problem'][:500]}", "", "Rebuilt questions:", ""]
        lines += [f"- step {c}: {q}" for c, q in x["mixed_recon"].items()] + ["", "---", ""]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    return summary


def report(a) -> None:
    out = Path(a.out)
    summary = {}
    if (out / "tutor" / "compare.jsonl").exists():
        summary["tutor"] = tutor_report(out / "tutor")
    if (out / "drift" / "compare.jsonl").exists():
        summary["drift"] = drift_report(out / "drift")
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


STAGES = {"tutor-build": tutor_build, "tutor-run": tutor_run, "tutor-compare": tutor_compare,
          "drift-attempts": drift_attempts, "drift-critics": drift_critics, "drift-compare": drift_compare,
          "drift-repair": drift_repair, "report": report}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=list(STAGES))
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default="", help="local path of Qwen/Qwen3.5-2B")
    ap.add_argument("--big-path", default="", help="local path of Qwen/Qwen3.8-27B (tokenizer for the 27B client)")
    ap.add_argument("--port", type=int, default=8002)
    ap.add_argument("--adapters", default=str(Path.home() / "anlp-final-adapters"))
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="smoke test: items per label (tutor) / dev problems (drift)")
    STAGES[ap.parse_args().stage](ap.parse_args())


if __name__ == "__main__":
    main()
