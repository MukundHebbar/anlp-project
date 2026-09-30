#!/usr/bin/env python3
"""Write artifacts/baselines/final-v3/REPORT.md from the stored baseline files.

    python3 scripts/report_baseline.py

Reads, for each split (test, pilot) and model, scores.jsonl (deterministic) and
judged-scores.jsonl (DeepSeek judges). Every number in the report is computed here;
nothing is typed by hand. 95% intervals are percentile bootstraps over questions
(2,000 resamples, fixed seed).
"""

from __future__ import annotations

import json
import random
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from anlp_project.baseline import BASELINE_DIR, EVAL_SAMPLING, MODELS  # noqa: E402

NAMES = {"qwen3.5-2b": "Qwen3.5-2B", "qwen3.5-4b": "Qwen3.5-4B", "qwen3.8-27b": "Qwen3.8-27B"}
# (title, folder, student run, teacher run, token cap). The first section is the final protocol.
SECTIONS = [
    ("Test, final protocol v2: T 1.0, top_p 1.0, no top-k, 32k cap (400 per task)", "test", "qwen3.5-2b-final", "qwen3.8-27b-final", 32768),
    ("Test, protocol v1 at 32k cap: T 0.7, top_p 0.8, top_k 20 (400 per task)", "test", "qwen3.5-2b-cap32k", "qwen3.8-27b-cap32k", 32768),
    ("Test, 8k cap: earlier protocol, 4B student (400 per task)", "test", "qwen3.5-4b", "qwen3.8-27b", 8192),
    ("Train pilot, 8k cap: 4B student (100 per task)", "pilot-train-100", "qwen3.5-4b", "qwen3.8-27b", 8192),
]
BUDGETS = (8192, 16384)


def label(key: str) -> str:
    if key.endswith("-final"):
        base, tag = key[: -len("-final")], "v2"
    else:
        base, _, cap = key.partition("-cap")
        tag = f"v1, {cap or '8k'}"
    role = "Teacher" if base == "qwen3.8-27b" else "Student"
    return f"{role} {NAMES[base]} ({tag})"


def _within(s: dict, budget: int) -> bool:
    """Finished (not cut off) using at most ``budget`` generated tokens."""
    return s.get("finish_reason") != "length" and (s.get("completion_tokens") or 0) <= budget
DIMS = ("premise_fidelity", "target_fidelity", "evidence_integration", "mathematical_validity")


def load(folder: str, model: str, name: str) -> dict[str, dict]:
    path = BASELINE_DIR / folder / model / name
    return {x["uid"]: x for x in map(json.loads, path.open())} if path.exists() else {}


def boot(values: list[float], seed: int = 0) -> tuple[float, float, float] | None:
    if not values:
        return None
    rng = random.Random(seed)
    means = sorted(st.mean(rng.choices(values, k=len(values))) for _ in range(2000))
    return st.mean(values), means[49], means[1949]


def fmt(ci, pct=True, n=None) -> str:
    if ci is None:
        return "n/a"
    m, lo, hi = ci
    f = (lambda v: f"{100 * v:.1f}") if pct else (lambda v: f"{v:.1f}")
    unit = "%" if pct else ""
    return f"{f(m)}{unit} [{f(lo)}, {f(hi)}]" + (f" (n={n})" if n is not None else "")


def metrics(det: dict, jud: dict, cap: int) -> dict:
    """All headline numbers for one split/model."""
    solve = [s for s in det.values() if s["task"] == "solve"]
    judge = [s for s in det.values() if s["task"] == "judge"]
    recon = [s for s in det.values() if s["task"] == "reconstruct"]
    m = {"n": {t: len(x) for t, x in (("solve", solve), ("judge", judge), ("reconstruct", recon))}}
    m["solve_acc"] = [s["answer_status"] == "correct" for s in solve]
    m["solve_status"] = {k: sum(s["answer_status"] == k for s in solve) for k in ("correct", "incorrect", "unverified", "missing")}
    m["solve_checkable_acc"] = [s["answer_status"] == "correct" for s in solve if s["answer_status"] in ("correct", "incorrect")]
    m["judge_verdict"] = [s["verdict_correct"] for s in judge]
    m["judge_verdict_on_correct"] = [s["verdict_correct"] for s in judge if s["label"] == "correct"]
    m["judge_verdict_on_incorrect"] = [s["verdict_correct"] for s in judge if s["label"] == "incorrect"]
    m["judge_step"] = [s["step_correct"] for s in judge if s["label"] == "incorrect"]
    jj = [jud[s["uid"]] for s in judge if s["uid"] in jud]
    m["judge_score"] = [x["score_100"] for x in jj if x["score_100"] is not None]
    m["judge_score_missing"] = sum(x["score_100"] is None for x in jj)
    rj = [jud[s["uid"]] for s in recon if s["uid"] in jud]
    unusable = [x for x in rj if x["status"] == "unusable_response"]
    unresolved = [x for x in rj if x["status"] == "unresolved"]
    scored = [x for x in rj if x["score_100"] is not None]
    m["recon_score_scored"] = [x["score_100"] for x in scored]
    m["recon_score_unusable0"] = [x["score_100"] for x in scored] + [0.0] * len(unusable)
    m["recon_same_question"] = [x.get("semantic_equivalent") is True for x in rj]
    m["recon_grounded"] = [bool(x.get("provisional_grounded_recovery")) for x in rj]
    m["recon_counts"] = {"usable": len(rj) - len(unusable), "unusable": len(unusable), "unresolved_judgment": len(unresolved),
                         "scored": len(scored), "shortcut": sum(bool(x.get("shortcut")) for x in rj),
                         "strict_json": sum(s.get("strict_json", False) for s in recon)}
    m["recon_dims"] = {d: (st.mean(v) if (v := [x["dimensions"][d] for x in scored if x["dimensions"][d] is not None]) else None)
                       for d in DIMS}
    m["judge_dims"] = {d: st.mean(x["dimensions"][d] for x in jj if x["score_100"] is not None) if m["judge_score"] else None
                       for d in "VLEM"}
    # Budget-limited accuracy from the same run: correct and finished within N tokens.
    m["budget"] = {}
    for n in (b for b in BUDGETS if b < cap):
        recon_n = [(jud[s["uid"]]["score_100"] if _within(s, n) else 0.0) for s in recon if s["uid"] in jud
                   and jud[s["uid"]]["score_100"] is not None] + [0.0] * len(unusable)
        m["budget"][n] = {"solve": [s["answer_status"] == "correct" and _within(s, n) for s in solve],
                          "judge": [s["verdict_correct"] and _within(s, n) for s in judge],
                          "recon": recon_n}
    for t, rows in (("solve", solve), ("judge", judge), ("reconstruct", recon)):
        m[f"cap_{t}"] = sum(s["hit_token_cap"] for s in rows)
        m[f"tokens_{t}"] = st.mean(s["completion_tokens"] or 0 for s in rows) if rows else None
    return m


def _avg(values, pct=False) -> str:
    values = list(values)
    if not values:
        return "n/a"
    return f"{100 * st.mean(values):.1f}%" if pct else f"{st.mean(values):.1f}"


def paired(dets: dict, juds: dict) -> list[str]:
    """Compare both models on questions that are checkable for both."""
    a, b = list(dets)
    out = ["| Task | Questions checkable for both | Metric | " + " | ".join(label(x) for x in (a, b)) + " |",
           "|---|---:|---|---:|---:|"]
    both = [u for u, s in dets[a].items() if s["task"] == "solve" and s["answer_status"] in ("correct", "incorrect")
            and dets[b].get(u, {}).get("answer_status") in ("correct", "incorrect")]
    out.append(f"| SOLVE | {len(both)} | Accuracy | " + " | ".join(
        _avg((dets[m][u]['answer_status'] == 'correct' for u in both), pct=True) for m in (a, b)) + " |")
    both = [u for u, s in dets[a].items() if s["task"] == "judge" and s["parsed"] and not s["hit_token_cap"]
            and dets[b].get(u, {}).get("parsed") and not dets[b][u]["hit_token_cap"]]
    out.append(f"| JUDGE | {len(both)} | Verdict accuracy | " + " | ".join(
        _avg((dets[m][u]['verdict_correct'] for u in both), pct=True) for m in (a, b)) + " |")
    inc = [u for u in both if dets[a][u]["label"] == "incorrect"]
    out.append(f"| JUDGE | {len(inc)} incorrect | First wrong step | " + " | ".join(
        _avg((dets[m][u]['step_correct'] for u in inc), pct=True) for m in (a, b)) + " |")
    bj = [u for u in both if all(juds[m].get(u, {}).get("score_100") is not None for m in (a, b))]
    out.append(f"| JUDGE | {len(bj)} | V/L/E/M score /100 | " + " | ".join(
        _avg(juds[m][u]['score_100'] for u in bj) for m in (a, b)) + " |")
    br = [u for u, x in juds[a].items() if x["task"] == "reconstruct" and x["score_100"] is not None
          and juds[b].get(u, {}).get("score_100") is not None]
    if br:
        out.append(f"| RECONSTRUCT | {len(br)} | PC-v4 score /100 | " + " | ".join(
            _avg(juds[m][u]['score_100'] for u in br) for m in (a, b)) + " |")
        out.append(f"| RECONSTRUCT | {len(br)} | Same original question | " + " | ".join(
            _avg((juds[m][u].get('semantic_equivalent') is True for u in br), pct=True) for m in (a, b)) + " |")
    return out


def breakdown(dets: dict) -> list[str]:
    out = ["| Group | " + " | ".join(f"{label(m)} SOLVE acc." for m in dets) + " | "
           + " | ".join(f"{label(m)} JUDGE verdict" for m in dets) + " |",
           "|---|" + "---:|" * (2 * len(dets))]
    groups = {}
    for m, det in dets.items():
        for s in det.values():
            band = "difficulty 7.0–8.0" if s["difficulty"] >= 7 else "difficulty 5.0–6.5"
            for g in (s["broad_topic"], band):
                groups.setdefault(g, {}).setdefault((m, s["task"]), []).append(s)
    order = sorted(k for k in groups if not k.startswith("difficulty")) + sorted(k for k in groups if k.startswith("difficulty"))
    for g in order:
        cells = []
        for task, key in (("solve", lambda s: s["answer_status"] == "correct"), ("judge", lambda s: s["verdict_correct"])):
            for m in dets:
                rows = groups[g].get((m, task), [])
                cells.append(f"{100 * st.mean(map(key, rows)):.1f}% (n={len(rows)})" if rows else "n/a")
        solve_cells, judge_cells = cells[: len(dets)], cells[len(dets):]
        out.append(f"| {g} | " + " | ".join(solve_cells + judge_cells) + " |")
    return out


def budget_rows(M: dict, cols: list, head: str, sep: str) -> list[str]:
    budgets = sorted({n for m in cols for n in M[m]["budget"]})
    if not budgets:
        return []
    out = ["", "### Budget-limited results (same run; an answer counts only if it finished within the budget)", "", head, sep]
    for n in budgets:
        out.append(f"| SOLVE accuracy within {n // 1024}k tokens | " + " | ".join(fmt(boot(M[m]["budget"][n]["solve"])) for m in cols) + " |")
        out.append(f"| JUDGE verdict accuracy within {n // 1024}k tokens | " + " | ".join(fmt(boot(M[m]["budget"][n]["judge"])) for m in cols) + " |")
        out.append(f"| RECONSTRUCT PC-v4 /100 within {n // 1024}k tokens (unusable = 0) | " + " | ".join(fmt(boot(M[m]["budget"][n]["recon"]), pct=False) for m in cols) + " |")
    return out


def section(title: str, folder: str, keys: tuple[str, str], cap: int) -> list[str]:
    dets = {m: load(folder, m, "scores.jsonl") for m in keys}
    juds = {m: load(folder, m, "judged-scores.jsonl") for m in keys}
    dets = {m: d for m, d in dets.items() if d}
    if not dets:
        return [f"## {title}", "", "Not run yet.", ""]
    M = {m: metrics(dets[m], juds.get(m, {}), cap) for m in dets}
    cols = list(M)
    head = "| Metric | " + " | ".join(label(m) for m in cols) + " |"
    sep = "|---|" + "---:|" * len(cols)

    def row(name, fn):
        return f"| {name} | " + " | ".join(fn(M[m]) for m in cols) + " |"

    L = [f"## {title}", "", "### Headline results (all questions; failures count as wrong)", "", head, sep,
         row("SOLVE accuracy", lambda x: fmt(boot(x["solve_acc"]), n=len(x["solve_acc"]))),
         row("JUDGE verdict accuracy", lambda x: fmt(boot(x["judge_verdict"]), n=len(x["judge_verdict"]))),
         row("… on correct solutions", lambda x: fmt(boot(x["judge_verdict_on_correct"]), n=len(x["judge_verdict_on_correct"]))),
         row("… on incorrect solutions", lambda x: fmt(boot(x["judge_verdict_on_incorrect"]), n=len(x["judge_verdict_on_incorrect"]))),
         row("JUDGE first wrong step (incorrect solutions)", lambda x: fmt(boot(x["judge_step"]), n=len(x["judge_step"]))),
         row("JUDGE V/L/E/M score /100 (judged items)", lambda x: fmt(boot(x["judge_score"]), pct=False, n=len(x["judge_score"]))),
         row("RECONSTRUCT PC-v4 score /100 (scored items)", lambda x: fmt(boot(x["recon_score_scored"]), pct=False, n=len(x["recon_score_scored"]))),
         row("RECONSTRUCT PC-v4 score /100 (unusable = 0; unresolved excluded)", lambda x: fmt(boot(x["recon_score_unusable0"]), pct=False, n=len(x["recon_score_unusable0"]))),
         row("RECONSTRUCT same original question", lambda x: fmt(boot(x["recon_same_question"]), n=len(x["recon_same_question"]))),
         row("RECONSTRUCT grounded recovery (provisional)", lambda x: fmt(boot(x["recon_grounded"]), n=len(x["recon_grounded"]))),
         *budget_rows(M, cols, head, sep),
         "", "### Checkable answers only", "",
         "Each model on its own checkable answers:", "", head, sep,
         row("SOLVE accuracy (verifier decided correct/incorrect)", lambda x: fmt(boot(x["solve_checkable_acc"]), n=len(x["solve_checkable_acc"]))),
         "", "Both models on the questions checkable for both (the fairer comparison):", "",
         *(paired(dets, juds) if len(dets) == 2 else ["(needs both models)"]),
         "", "### Missing and malformed responses", "", head, sep,
         row("SOLVE correct / incorrect / unverified / missing", lambda x: " / ".join(str(v) for v in x["solve_status"].values())),
         row(f"Hit {cap:,}-token cap: SOLVE / JUDGE / RECONSTRUCT", lambda x: f"{x['cap_solve']} / {x['cap_judge']} / {x['cap_reconstruct']}"),
         row("Mean answer tokens: SOLVE / JUDGE / RECONSTRUCT", lambda x: " / ".join(f"{x[f'tokens_{t}']:.0f}" for t in ("solve", "judge", "reconstruct"))),
         row("JUDGE items without a judge score", lambda x: str(x["judge_score_missing"])),
         row("RECONSTRUCT strict JSON", lambda x: str(x["recon_counts"]["strict_json"])),
         row("RECONSTRUCT usable / unusable", lambda x: f"{x['recon_counts']['usable']} / {x['recon_counts']['unusable']}"),
         row("RECONSTRUCT scored / unresolved judgment", lambda x: f"{x['recon_counts']['scored']} / {x['recon_counts']['unresolved_judgment']}"),
         row("RECONSTRUCT shortcuts (score 0)", lambda x: str(x["recon_counts"]["shortcut"])),
         "", "### Rubric dimensions (means, 0–4, scored items)", "", head, sep,
         row("JUDGE V / L / E / M", lambda x: " / ".join(f"{v:.2f}" for v in x["judge_dims"].values()) if x["judge_score"] else "n/a"),
         row("RECONSTRUCT P / T / E / M", lambda x: " / ".join(f"{v:.2f}" for v in x["recon_dims"].values()) if x["recon_score_scored"] else "n/a"),
         "", "### By topic and difficulty (all questions)", "", *breakdown(dets), ""]
    return L


def main():
    meta = {}
    for m in SECTIONS[0][2:4]:
        p = BASELINE_DIR / "test" / m / "metadata.json"
        if p.exists():
            meta[m] = json.loads(p.read_text())
    lines = ["# FINAL-v3 zero-training baselines: report", "",
             "Generated by `scripts/report_baseline.py` from the files in this folder; see [README.md](README.md) for the method.", "",
             "## Setup", "",
             f"- **Final protocol v2:** student `{MODELS['qwen3.5-2b']}`, teacher `{MODELS['qwen3.8-27b']}`; bf16, text-only, non-thinking chat template, vLLM 0.30.0 on one H100 per model (Modal).",
             f"- One sample per question: temperature {EVAL_SAMPLING['temperature']}, top_p {EVAL_SAMPLING['top_p']} (off), top_k off, no penalties, seed {EVAL_SAMPLING['seed']}, at most {EVAL_SAMPLING['max_tokens']:,} new tokens. This matches the OPD training rollouts.",
             "- **Protocol v1,** kept for reference: temperature 0.7, top_p 0.8, top_k 20 (Qwen's general non-thinking defaults), with 8k and 32k caps and the earlier Qwen3.5-4B student. See RUN_LOG.md for why the protocol changed.",
             "- Scoring:",
             "  - SOLVE: deterministic verifier v2 against the DeepMath answer.",
             "  - JUDGE: the verdict and first wrong step are parsed from the answer; DeepSeek V4.1 Flash scores V/L/E/M against the key.",
             "  - RECONSTRUCT: DeepSeek V4.1 Flash PC-v4 judges score P/T/E/M. The fidelity judge sees the source; the validity judge does not.",
             "- Judge calls: at most two attempts per call; a second attempt is made only after a transport failure (e.g. rate limiting). Judgments that fail validation stay unresolved.",
             "- Intervals are 95% bootstrap intervals over questions. They reflect question sampling only, not variation between runs or seeds (one sample per question).",
             ""]
    if meta:
        lines += ["| Run | vLLM | GPU | Load (s) | Generate (s) |", "|---|---|---|---:|---:|"]
        for m, x in meta.items():
            lines.append(f"| {label(m)} test | {x.get('vllm')} | {x.get('gpu', '').split(',')[0]} | {x.get('load_seconds')} | {x.get('generate_seconds')} |")
        lines.append("")
    lines += ["## Reading notes", "",
              "- **Failures count.** Headline SOLVE and JUDGE numbers include answers that are cut off, unparsed or unverifiable, counted as wrong. The judged means (JUDGE V/L/E/M, RECONSTRUCT PC-v4) cover judged items only; their denominators are shown.",
              "- **Two kinds of RECONSTRUCT missingness.** An *unusable* answer has no extractable question; it is the student's failure and counts as 0 in the second PC-v4 row. An *unresolved judgment* is a judge failure; it is excluded, not counted as 0.",
              "- **Checkable-only comparisons select easier questions.** The questions a model fails to finish are likely the harder ones.",
              "- **Grounded recoveries are provisional.** The protocol requires case review before they are reported as verified.",
              "- **Budget-limited results** come from the same 32k run. They are not a separate capped run; vLLM runs are not bit-identical across caps.",
              "- **One sample per question.** Most OPD papers average over several samples per question, so these numbers are noisier than avg@k.",
              ""]
    for title, folder, student, teacher, cap in SECTIONS:
        lines += section(title, folder, (student, teacher), cap)
    out = BASELINE_DIR / "REPORT.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
