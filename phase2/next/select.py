#!/usr/bin/env python3
"""Picking the final answer from 4 attempts: majority vote vs a judge, on every problem.

Solver: the mixed model, normal format, 4 attempts per problem (FINAL-v3 SOLVE dev slice: the existing attempts of
phase2/scripts/functional.py; FINAL-v3 SOLVE test set: generated here). Each attempt is rewritten by the same model into
5-8 numbered steps; every rewrite is kept as is (no answer check, no fallback). The judge sees each attempt twice, as
written and as rewritten.

Methods (all score the chosen answer against the dataset key with the repository checker):
  majority    most common final answer (ties: first seen)
  pointwise   votes weighted by 1 - P(incorrect) from the mixed model judging each rewrite (4 votes); also on originals
  pairwise    the two most common different answers; the mixed model sees one shortened solution for each side by
              side and says which is correct, 8 votes (4 per order); otherwise the majority answer

    python phase2/next/select.py run --split dev|test --out DIR --base <2B>
    python phase2/next/select.py report --out DIR
"""
import argparse, collections, json, random, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "phase2" / "scripts")); sys.path.insert(0, str(HERE))
import hint_pilot as hp  # noqa: E402
import functional as F  # noqa: E402
import stepformat as SF  # noqa: E402
from crossjudge import CONDENSE  # noqa: E402

PAIR = ("Two students solved the same mathematics problem and reached different final answers. At most one of them is "
        "correct.\n\nPROBLEM:\n{p}\n\nSOLUTION A:\n{a}\n\nSOLUTION B:\n{b}\n\nCheck both solutions step by step and "
        "decide which final answer is correct. Keep the reasoning brief. End with exactly one line:\n"
        "Correct solution: A\nor\nCorrect solution: B")
PAIR_RE = re.compile(r"Correct solution:\s*\**\s*([AB])\b")
JVOTES, PVOTES = 4, 4


def numbered(steps):
    return "\n".join(f"S{i}: {s}" for i, s in enumerate(steps, 1))


def run(a):
    from anlp_project import baseline, opd
    out = Path(a.out) / a.split; out.mkdir(parents=True, exist_ok=True)
    eng = hp.Engine(a.base, Path(a.adapters), 32768)
    rows = {r["uid"]: r for r in (opd.slice_rows("solve", "dev") if a.split == "dev" else baseline.load_rows("solve", "test"))}
    # 1. attempts
    p = out / "attempts.jsonl"
    if p.exists():
        atts = hp.read_jsonl([p])
    elif a.split == "dev":
        atts = [x for x in hp.read_jsonl(sorted((REPO / "runs-out" / "functional" / "drift").glob("attempts-shard*.jsonl")))]
        hp.write_jsonl(p, atts)
    else:
        rl = list(rows.values())
        outs = eng.chat([hp.solve_prompt(r) for r in rl], "mixed", 4, 16384)
        atts = []
        for r, samples in zip(rl, outs):
            for k, s in enumerate(samples):
                sc = hp.score(r, s)
                atts.append({"uid": r["uid"], "attempt": k, "problem": r["question"], "key": r["final_answer"],
                             "text": s["text"], "finish_reason": s["finish_reason"], "steps": hp.to_steps(s["text"]),
                             "answer": sc["extracted_answer"], "correct": sc["correct_strict"]})
        hp.write_jsonl(p, atts)
    # 2. rewrite dataset: the same model rewrites every attempt into short numbered steps; every rewrite is kept as is
    p = out / "rewrites.jsonl"
    if p.exists():
        short = hp.read_jsonl([p])
    else:
        outs = eng.chat([CONDENSE.format(p=x["problem"], s=x["text"]) for x in atts], "mixed", 1, 4096)
        short = []
        for x, o in zip(atts, outs):
            t = o[0]["text"]
            steps, parsed = SF.split_steps(t)
            short.append({**{k: x[k] for k in ("uid", "attempt", "answer", "correct")}, "orig_steps": x["steps"],
                          "rewrite": t, "short_steps": steps, "rewrite_parsed": parsed,
                          "rewrite_answer": baseline.extract_solve_answer(t)[0], "rewrite_tokens": o[0]["completion_tokens"]})
        hp.write_jsonl(p, short)
        print("rewrites", len(short), flush=True)
    prob = {x["uid"]: x["problem"] for x in atts}
    # 3. judge each attempt twice: as written and as rewritten
    p = out / "pointwise.jsonl"
    if not p.exists():
        todo = [x for x in short if x.get("answer")]
        o_orig = F.gen(eng, [F.judge_prompt(prob[x["uid"]], x["orig_steps"]) for x in todo], "mixed", JVOTES, 6144)
        o_rew = F.gen(eng, [F.judge_prompt(prob[x["uid"]], x["short_steps"]) for x in todo], "mixed", JVOTES, 6144)
        pi = lambda t: sum(d == "incorrect" for d, _ in F.judge_vote(t)["votes"]) / JVOTES  # noqa: E731
        hp.write_jsonl(p, [{"uid": x["uid"], "attempt": x["attempt"], "correct": x["correct"],
                            "p_incorrect_orig": pi(a_), "p_incorrect": pi(b_)} for x, a_, b_ in zip(todo, o_orig, o_rew)])
    # 4. pairwise between the two most common different answers
    p = out / "pairwise.jsonl"
    if not p.exists():
        by = collections.defaultdict(list)
        for x in short:
            if x.get("answer"):
                by[x["uid"]].append(x)
        jobs = []
        for u, xs in by.items():
            cl = clusters(xs)
            if len(cl) >= 2:
                a_, b_ = cl[0], cl[1]
                ra = min(a_, key=lambda x: sum(len(s) for s in x["short_steps"]))
                rb = min(b_, key=lambda x: sum(len(s) for s in x["short_steps"]))
                jobs.append((u, ra, rb))
        prompts = []
        for u, ra, rb in jobs:
            prompts.append(PAIR.format(p=prob[u], a=numbered(ra["short_steps"]), b=numbered(rb["short_steps"])))
            prompts.append(PAIR.format(p=prob[u], a=numbered(rb["short_steps"]), b=numbered(ra["short_steps"])))
        outs = F.gen(eng, prompts, "mixed", PVOTES, 6144)
        recs = []
        for i, (u, ra, rb) in enumerate(jobs):
            va = vb = 0
            for t in outs[2 * i]:
                m = PAIR_RE.findall(t)
                va += bool(m) and m[-1] == "A"; vb += bool(m) and m[-1] == "B"
            for t in outs[2 * i + 1]:
                m = PAIR_RE.findall(t)
                va += bool(m) and m[-1] == "B"; vb += bool(m) and m[-1] == "A"
            recs.append({"uid": u, "answer_a": ra["answer"], "answer_b": rb["answer"], "votes_a": int(va), "votes_b": int(vb)})
        hp.write_jsonl(p, recs)
    print("done", a.split, flush=True)


def clusters(xs):
    cl = []
    for x in xs:
        c = next((c for c in cl if F.same_answer(c[0]["answer"], x["answer"])), None)
        c.append(x) if c else cl.append([x])
    return sorted(cl, key=len, reverse=True)


def report(a):
    res = {}
    for split in ("dev", "test"):
        d = Path(a.out) / split
        if not (d / "pairwise.jsonl").exists():
            continue
        short = hp.read_jsonl([d / "rewrites.jsonl"])
        pwr = hp.read_jsonl([d / "pointwise.jsonl"])
        pw = {(x["uid"], x["attempt"]): x["p_incorrect"] for x in pwr}
        pwo = {(x["uid"], x["attempt"]): x["p_incorrect_orig"] for x in pwr}
        own = {"judge on original attempts (AUROC)": round(F.auroc([x["p_incorrect_orig"] for x in pwr if not x["correct"]],
                                                                  [x["p_incorrect_orig"] for x in pwr if x["correct"]]), 3),
               "judge on rewritten attempts (AUROC)": round(F.auroc([x["p_incorrect"] for x in pwr if not x["correct"]],
                                                                   [x["p_incorrect"] for x in pwr if x["correct"]]), 3)}
        pair = {x["uid"]: x for x in hp.read_jsonl([d / "pairwise.jsonl"])}
        by = collections.defaultdict(list)
        for x in short:
            by[x["uid"]].append(x)
        out = collections.defaultdict(dict)
        for u, xs in by.items():
            xa = [x for x in xs if x.get("answer")]
            cl = clusters(xa) if xa else []
            out["one attempt (average)"][u] = sum(x["correct"] for x in xs) / len(xs)
            out["best possible"][u] = float(any(x["correct"] for x in xs))
            out["majority"][u] = float(cl[0][0]["correct"]) if cl else 0.0
            if cl:
                best = max(cl, key=lambda c: sum(1 - pw.get((x["uid"], x["attempt"]), 0.5) + 1e-3 for x in c))
                out["pointwise judge"][u] = float(best[0]["correct"])
                besto = max(cl, key=lambda c: sum(1 - pwo.get((x["uid"], x["attempt"]), 0.5) + 1e-3 for x in c))
                out["pointwise judge on originals"][u] = float(besto[0]["correct"])
                if u in pair and len(cl) >= 2:
                    r = pair[u]
                    win = cl[0] if r["votes_a"] >= r["votes_b"] else cl[1]
                    out["pairwise judge"][u] = float(win[0]["correct"])
                else:
                    out["pairwise judge"][u] = float(cl[0][0]["correct"])
            else:
                out["pointwise judge"][u] = out["pairwise judge"][u] = out["pointwise judge on originals"][u] = 0.0
        qs = sorted(by); rng = random.Random(0)
        row = {"problems": len(qs), **own,
               "rewrite keeps the attempt's answer (%)": round(100 * sum(F.same_answer(x["rewrite_answer"], x["answer"])
                                                                  for x in short if x.get("answer")) / max(1, sum(1 for x in short if x.get("answer"))), 1),
               "rewrite mean tokens": round(sum(x["rewrite_tokens"] for x in short) / len(short)),
               "problems_with_2+_answers": sum(1 for u in qs if len(clusters([x for x in by[u] if x.get("answer")])) >= 2)}
        for m, v in out.items():
            acc = 100 * sum(v[u] for u in qs) / len(qs)
            if m in ("pointwise judge", "pairwise judge", "pointwise judge on originals"):
                diffs = [v[u] - out["majority"][u] for u in qs]
                bs = sorted(100 * sum(diffs[rng.randrange(len(qs))] for _ in qs) / len(qs) for _ in range(2000))
                row[m] = f"{acc:.1f} ({100 * sum(diffs) / len(qs):+.1f} vs majority, 95% CI [{bs[50]:+.1f}, {bs[1949]:+.1f}])"
            else:
                row[m] = round(acc, 1)
        res[split] = row
    (Path(a.out) / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run", "report"])
    ap.add_argument("--split", default="dev"); ap.add_argument("--out", required=True); ap.add_argument("--base", default="")
    ap.add_argument("--adapters", default=str(Path.home() / "anlp-final-adapters"))
    a = ap.parse_args()
    {"run": run, "report": report}[a.stage](a)
