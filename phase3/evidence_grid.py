"""Phase 3b checkpoint: the evidence grid, the sampling results (T1-T3) and the downstream check (CPU).

    PYTHONPATH=../src python evidence_grid.py        (from phase3/; wave-1 outputs copied to runs/ev)

Group-level view (the unit that selection acts on): every source gives each answer group a suspicion score (higher =
more likely wrong). Attempt-level sources are averaged over the group's attempts.
- top-2 AUROC: questions whose two largest answer groups are one right and one wrong; P(wrong group scored higher).
  This is the comparison every source covers, and the one that decides contested picks.
- attractor / one-off: on contested questions, right group vs the attractor (largest wrong group, >= 2 attempts) and
  vs one-off wrong groups (1 attempt), all pairs that the source scores.
- downstream: pick argmax over groups of n_g + w * logit(1 - suspicion_g) (w tuned on dev, neutral where a group has no
  score), against majority@16, on test ∪ extra; questions whose first two attempts agree stop there (ESC window 2).
Writes runs/evidence_grid.json and runs/evidence_grid.md.
"""

import json
import os
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy import special

import analyze as A
import common
from grade import same

G, J, EV = Path("runs/graded"), Path("runs/main/judge"), Path(os.environ.get("EV", "runs/ev"))
SETS = ("dev", "test", "extra")
L = lambda p: special.logit(np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4))
ROWS = common.rows_by_uid()


@lru_cache(maxsize=None)
def eq(a, b):
    return a is not None and b is not None and same(a, b)


def records(kind, s):
    d = EV / kind / s
    return [json.loads(line) for f in sorted(d.glob("[0-9][0-9][0-9].jsonl")) for line in f.open()] if d.exists() else []


# ------------------------------------------------------------------ loading

def load():
    data = {s: A.load(G, J, s) for s in SETS}
    ans = {}
    for s in SETS:
        for line in (G / f"{s}.jsonl").open():
            r = json.loads(line)
            if r["group"] >= 0:
                ans.setdefault((r["uid"], r["group"]), r["answer"])
    for s, qs in data.items():
        lp = {(r["uid"], r["k"]): r for r in records("logprob", s)}
        dg = {a: {(r["uid"], r["k"]): r["p_direct"] for r in records(f"direct-{a}", s)} for a in ("global", "perq")}
        for q in qs:
            u, n = q["uid"], q["n"]
            q["ans"] = {g: ans[(u, g)] for g in q["group_right"]}
            q["size"] = Counter(q["group"][q["answered"]].tolist())
            att = {}
            for key in ("mean_lp", "sum_lp", "max_group_unc", "tail_unc", "mean_unc", "answer_lp"):
                att[key] = np.array([lp.get((u, k), {}).get(key, np.nan) for k in range(n)], float)
            q["lp"] = att
            q["att_scores"] = {
                "self: judge chain": q["p"][:, 0], "self: direct P(incorrect)": q["pdir"],
                "trained judge (global), direct": np.array([np.nan if (v := dg["global"].get((u, k))) is None else v
                                                            for k in range(n)], float),
                "trained judge (per-question), direct": np.array([np.nan if (v := dg["perq"].get((u, k))) is None else v
                                                                  for k in range(n)], float),
                "solver: -mean log p": -att["mean_lp"], "solver: -sum log p": -att["sum_lp"],
                "solver: max window uncertainty": att["max_group_unc"], "solver: tail uncertainty": att["tail_unc"],
                "length": q["tokens"]}
            q["grp"] = {name: group_mean(q, v) for name, v in q["att_scores"].items()}
        add_group_sources(s, qs)
    return data


def group_mean(q, v):
    out = {}
    for g in q["group_right"]:
        m = (q["group"] == g) & q["answered"] & ~np.isnan(v)
        if m.any():
            out[g] = float(np.mean(v[m]))
    return out


def add_group_sources(s, qs):
    by = {q["uid"]: q for q in qs}
    for r in records("answer", s):
        if r["p_yes"] is not None:
            by[r["uid"]]["grp"].setdefault("answer-only (P no)", {})[r["group"]] = 1 - r["p_yes"]
    pw = defaultdict(list)
    for r in records("pairwise", s):
        if r["p_g1"] is not None:
            pw[(r["uid"], r["g1"], r["g2"])].append(r["p_g1"])
    for (u, g1, g2), v in pw.items():
        d = by[u]["grp"].setdefault("pairwise A/B", {})
        d[g1], d[g2] = 1 - float(np.mean(v)), float(np.mean(v))
    bw = defaultdict(list)
    for r in records("backward", s):
        for c in r["outputs"]:
            if c["finish_reason"] == "stop":
                a = common.baseline.extract_solve_answer(c["text"])[0]
                bw[(r["uid"], r["group"])].append(float(eq(a, r["value"])))
    for (u, g), v in bw.items():
        by[u]["grp"].setdefault("backward check (1 - recovery)", {})[g] = 1 - float(np.mean(v))
    for r in records("program", s):
        v = [c["last_line"].strip().upper() for c in r["outputs"] if c["status"] == "ok" and c["last_line"]]
        v = [x for x in v if x in ("CORRECT", "INCORRECT")]
        if v:
            by[r["uid"]]["grp"].setdefault("program check (share INCORRECT)", {})[r["group"]] = v.count("INCORRECT") / len(v)
    for r in records("pot", s):
        q = by[r["uid"]]
        outs = [c["last_line"] for c in r["outputs"] if c["status"] == "ok" and c["last_line"]]
        q["pot"] = outs
        if outs:
            q["grp"]["program-of-thought agreement (PROVE)"] = {
                g: 1 - float(np.mean([eq(o, a) for o in outs])) for g, a in q["ans"].items()}


# ------------------------------------------------------------------ metrics

def top2(q):
    gs = sorted(q["size"], key=lambda g: (-q["size"][g], g))[:2]
    return gs if len(gs) == 2 and q["group_right"][gs[0]] != q["group_right"][gs[1]] else None


def auc(pairs):
    return (float(np.mean(pairs)), len(pairs)) if pairs else (np.nan, 0)


def grid_row(qs, name):
    t2, att, one, covered, total = [], [], [], 0, 0
    for q in qs:
        sc = q["grp"].get(name, {})
        p = top2(q)
        if p:
            total += 1
            if all(g in sc for g in p):
                covered += 1
                r, w = (p[0], p[1]) if q["group_right"][p[0]] else (p[1], p[0])
                t2.append(1.0 if sc[w] > sc[r] else 0.5 if sc[w] == sc[r] else 0.0)
        if not A.contested(q):
            continue
        right = [g for g, ok in q["group_right"].items() if ok and g in q["size"]]
        if not right or right[0] not in sc:
            continue
        rs = sc[right[0]]
        wrong = {g: c for g, c in q["size"].items() if not q["group_right"][g]}
        top_w = max(wrong, key=lambda g: (wrong[g], -g)) if wrong else None
        for g, c in wrong.items():
            if g not in sc:
                continue
            v = 1.0 if sc[g] > rs else 0.5 if sc[g] == rs else 0.0
            if g == top_w and c >= 2:
                att.append(v)
            elif c == 1:
                one.append(v)
    return {"top2_auroc": auc(t2), "coverage_top2": covered / max(total, 1), "right_vs_attractor": auc(att),
            "right_vs_oneoff": auc(one)}


def pick(q, name, w):
    """Expected correctness of argmax_g n_g + w * logit(1 - suspicion_g), ties broken at random."""
    if not q["size"]:
        return 0.0
    sc = q["grp"].get(name, {}) if name else {}
    if name and not is_prob(name) and sc:
        # not a probability: standardised score, centred within the question (scale from all groups in the data)
        mu = np.mean(list(sc.values()))
        val = {g: c - (w * (sc[g] - mu) / SCALE[name] if g in sc else 0.0) for g, c in q["size"].items()}
    else:
        val = {g: c + (w * float(L(1 - sc[g])) if g in sc else 0.0) for g, c in q["size"].items()}
    top = max(val.values())
    tied = [g for g, v in val.items() if v >= top - 1e-9]
    return float(np.mean([q["group_right"][g] for g in tied]))


SCALE = {}


def is_prob(name):
    return not (name.startswith("solver:") or name == "length")


def set_scales(qs):
    names = {n for q in qs for n in q["grp"]}
    for n in names:
        if not is_prob(n):
            v = [x for q in qs for x in q["grp"].get(n, {}).values()]
            SCALE[n] = float(np.std(v)) if len(v) > 1 and np.std(v) > 0 else 1.0


def esc_parts(q):
    """ESC window 2 under a random order: P(first two answered and agree), P(right | stop)."""
    n = q["n"]
    pairs = {g: c * (c - 1) for g, c in q["size"].items()}
    stop = sum(pairs.values()) / (n * (n - 1))
    right = sum(v for g, v in pairs.items() if q["group_right"][g]) / max(sum(pairs.values()), 1)
    return stop, right


def downstream(qs, name, w, gated=True):
    """Per-question expected accuracy and cost (units = attempts) of the evidence rule."""
    acc, cost = [], []
    for q in qs:
        full = pick(q, name, w)
        if gated:
            stop, right = esc_parts(q)
            acc.append(stop * right + (1 - stop) * full)
            cost.append(2 * stop + q["n"] * (1 - stop))
        else:
            acc.append(full)
            cost.append(q["n"])
    return np.array(acc), np.array(cost)


def majority(qs, gated=True):
    return downstream(qs, None, 0.0, gated)


# ------------------------------------------------------------------ combination (registered: fitted on dev, used once)

COMBO = "combination (dev-fitted logistic, top-3 dev sources)"


def feature(q, name, g):
    """Within-question centred score of group g (logit for probabilities, standardised otherwise); 0 if unscored."""
    sc = q["grp"].get(name, {})
    if g not in sc:
        return 0.0
    x = {h: float(L(v)) if is_prob(name) else v / SCALE[name] for h, v in sc.items()}
    return x[g] - np.mean(list(x.values()))


def fit_logistic(X, y, l2=1.0, iters=50):
    X = np.hstack([X, np.ones((len(X), 1))])
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = special.expit(X @ b)
        H = X.T @ (X * (p * (1 - p))[:, None]) + l2 * np.eye(len(b))
        b -= np.linalg.solve(H, X.T @ (p - y) + l2 * b)
    return b


def add_combination(data, names, k=3):
    """Pick the k sources with the best dev top-2 AUROC (coverage >= 50% on dev), fit P(group wrong) on dev groups of
    contested questions, and add the fitted probability to every question as one more group source."""
    dev = data["dev"]
    cand = [(grid_row(dev, n), n) for n in names]
    cand = [(r["top2_auroc"][0], n) for r, n in cand if r["coverage_top2"] >= 0.5 and not np.isnan(r["top2_auroc"][0])]
    chosen = [n for _, n in sorted(cand, reverse=True)[:k]]
    X, y = [], []
    for q in dev:
        if not A.contested(q):
            continue
        for g in q["size"]:
            X.append([feature(q, n, g) for n in chosen])
            y.append(float(not q["group_right"][g]))
    b = fit_logistic(np.array(X), np.array(y))
    for qs in data.values():
        for q in qs:
            q["grp"][COMBO] = {g: float(special.expit(np.dot(b[:-1], [feature(q, n, g) for n in chosen]) + b[-1]))
                               for g in q["size"]}
    return {"sources": chosen, "coef": b.tolist(), "dev_groups": len(y)}


# ------------------------------------------------------------------ T1: importance-weighted vote toward p^alpha

def is_vote(q, alpha, per_token=False):
    a = q["answered"] & ~np.isnan(q["lp"]["sum_lp"])
    if not a.any():
        return None, np.nan
    x = q["lp"]["mean_lp"] if per_token else q["lp"]["sum_lp"]
    lw = (alpha - 1) * x[a]
    w = np.exp(lw - lw.max())
    ess = w.sum() ** 2 / (w ** 2).sum()
    tot = defaultdict(float)
    for g, wi in zip(q["group"][a], w):
        tot[g] += wi
    return max(tot, key=tot.get), ess


# ------------------------------------------------------------------ T2 / T3 grading

def classify(uid, text, attractor_answer):
    a = common.baseline.extract_solve_answer(text)[0]
    if a is None:
        return "none"
    if eq(ROWS[uid]["final_answer"], a):
        return "right"
    if eq(attractor_answer, a):
        return "attractor"
    return "other"


def t2(data):
    rows = records("samp/resample", "test") + records("samp/resample", "extra")
    if not rows:
        return None
    by = {q["uid"]: q for s in ("test", "extra") for q in data[s]}
    tab = defaultdict(Counter)
    fresh = Counter()
    seen = set()
    for r in rows:
        q = by[r["uid"]]
        att_ans = q["ans"][r["attractor_group"]]
        prefix_text_cut = r["prefix_chars"]  # noqa: F841 (kept for the record)
        for c in r["outputs"]:
            tab[(r["role"], r["cut"])][classify(r["uid"], c["text"], att_ans) if c["finish_reason"] == "stop" else "none"] += 1
        if r["uid"] not in seen:
            seen.add(r["uid"])
            for k in range(q["n"]):
                g = q["group"][k]
                fresh["none" if g < 0 else "right" if q["group_right"][g] else
                      "attractor" if g == r["attractor_group"] else "other"] += 1
    norm = lambda c: {k: c[k] / max(sum(c.values()), 1) for k in ("right", "attractor", "other", "none")}
    return {"questions": len(seen), "fresh": norm(fresh),
            "resample": {f"{role} @ {cut:.2f}": norm(c) for (role, cut), c in sorted(tab.items())}}


def group_answers(uid, answers):
    reps, gid = [], []
    for a in answers:
        if a is None:
            gid.append(-1)
            continue
        g = next((j for j, rep in enumerate(reps) if eq(rep, a)), None)
        if g is None:
            reps.append(a)
            g = len(reps) - 1
        gid.append(g)
    right = {j for j, rep in enumerate(reps) if eq(ROWS[uid]["final_answer"], rep)}
    return np.array(gid), right


def vote_stats(per_q, rng, R=200):
    """per_q: list of (group ids array, right set). Single acc, attractor share, pass, majority (random tie-break)."""
    single, attr, pas, maj = [], [], [], []
    for gid, right in per_q:
        n = len(gid)
        single.append(np.mean([g in right for g in gid]))
        wrong = Counter(g for g in gid if g >= 0 and g not in right)
        attr.append(wrong.most_common(1)[0][1] / n if wrong else 0.0)
        pas.append(float(any(g in right for g in gid)))
        cnt = Counter(g for g in gid if g >= 0)
        if not cnt:
            maj.append(0.0)
            continue
        top = max(cnt.values())
        tied = [g for g, c in cnt.items() if c == top]
        maj.append(np.mean([g in right for g in tied]))
    return {"single": float(np.mean(single)), "attractor_share": float(np.mean(attr)), "pass@8": float(np.mean(pas)),
            "majority@8": float(np.mean(maj)), "maj_per_q": np.array(maj)}


def t3(data):
    """Each sampler vs the cached T 1.0 attempts (first 8) on the same questions; paired bootstrap of the majority@8
    difference."""
    out = {}
    halves = ({}, {})
    for q in data["test"]:
        right = {g for g, ok in q["group_right"].items() if ok}
        for h, sl in zip(halves, (slice(0, 8), slice(8, 16))):
            h[q["uid"]] = (np.where(q["answered"][sl], q["group"][sl], -1), right)
    rng = np.random.default_rng(0)
    out["T 1.0 (cached, attempts 0-7)"] = vote_stats(list(halves[0].values()), rng)
    out["T 1.0 (cached, attempts 8-15)"] = vote_stats(list(halves[1].values()), rng)
    base = halves[0]
    for cfg in ("t07", "t13", "hot"):
        rs = records(f"samp/temp-{cfg}", "test")
        if not rs:
            continue
        by = defaultdict(list)
        for r in rs:
            a = common.baseline.extract_solve_answer(r["text"])[0] if r["finish_reason"] == "stop" else None
            by[r["uid"]].append(a)
        us = [u for u in base if u in by]
        v = vote_stats([group_answers(u, by[u]) for u in us], rng)
        b0, b1 = (vote_stats([h[u] for u in us], rng) for h in halves)
        b = {k: (b0[k] + b1[k]) / 2 for k in ("majority@8", "single", "maj_per_q")}  # both cached draws, averaged
        v["questions"] = len(us)
        v["paired_base_majority@8"] = b["majority@8"]
        v["paired_base_single"] = b["single"]
        v["majority_diff"] = A.boot_mean(v["maj_per_q"] - b["maj_per_q"])
        out[{"t07": "T 0.7", "t13": "T 1.3, min-p 0.05", "hot": "hot start (1.3 → 0.8)"}[cfg]] = v
    return out


# ------------------------------------------------------------------ PoT: a decorrelated voter?

def pot_vote(q, lam):
    """Majority over the 16 language attempts plus each PoT output (matched to a group) weighted lam; expected acc."""
    val = {g: float(c) for g, c in q["size"].items()}
    for o in q.get("pot", []):
        g = next((g for g, a in q["ans"].items() if g in val and eq(o, a)), None)
        if g is not None:
            val[g] += lam
    if not val:
        return 0.0
    top = max(val.values())
    return float(np.mean([q["group_right"][g] for g, v in val.items() if v >= top - 1e-9]))


def pot_plurality(outs):
    reps, cnt = [], []
    for o in outs:
        i = next((i for i, r in enumerate(reps) if eq(r, o)), None)
        if i is None:
            reps.append(o)
            cnt.append(0)
            i = len(reps) - 1
        cnt[i] += 1
    return reps[int(np.argmax(cnt))]


def pot_probe(data):
    ev = [q for q in data["test"] + data["extra"] if q.get("pot")]
    wrong_plural, differs, pot_right = 0, 0, 0
    for q in ev:
        if not q["size"]:
            continue
        top = max(q["size"].values())
        tied = [g for g, c in q["size"].items() if c == top]
        if len(tied) != 1 or q["group_right"][tied[0]]:
            continue
        wrong_plural += 1
        att = q["ans"][tied[0]]
        pp = pot_plurality(q["pot"])
        differs += not eq(pp, att)
        pot_right += eq(pp, ROWS[q["uid"]]["final_answer"])
    lams = (0.5, 1, 2, 4)
    dev = [q for q in data["dev"] if q.get("pot")]
    lam = max(lams, key=lambda l: np.mean([pot_vote(q, l) for q in dev]))
    base = np.array([pot_vote(q, 0.0) for q in ev])
    mix = np.array([pot_vote(q, lam) for q in ev])
    pot_only = np.mean([eq(pot_plurality(q["pot"]), ROWS[q["uid"]]["final_answer"]) for q in ev])
    return {"questions_with_pot": len(ev), "wrong_plurality": wrong_plural,
            "pot_plurality_differs": differs / max(wrong_plural, 1), "pot_plurality_right": pot_right / max(wrong_plural, 1),
            "pot_majority_alone": float(pot_only), "lambda": lam, "majority16": float(base.mean()),
            "mixed": float(mix.mean()), "mixed_vs_majority": A.boot_mean(mix - base)}


# ------------------------------------------------------------------ main

def main():
    data = load()
    ev = data["test"] + data["extra"]
    names = sorted({n for q in ev for n in q["grp"]})
    set_scales(data["dev"] + ev)
    res = {"grid": {}, "downstream": {}}
    res["combination"] = add_combination(data, names)
    names.append(COMBO)
    for n in names:
        res["grid"][n] = grid_row(ev, n)
        res["grid"][n]["dev"] = grid_row(data["dev"], n)

    for gated in (True, False):
        key = "downstream_esc2" if gated else "downstream_all16"
        res[key] = {}
        maj, mcost = majority(ev, gated)
        for n in names:
            ws = [0.25, 0.5, 1, 2, 4, 8]
            w = max(ws, key=lambda w: downstream(data["dev"], n, w, gated)[0].mean())
            acc, _ = downstream(ev, n, w, gated)
            res[key][n] = {"w": w, "acc": float(acc.mean()), "vs_majority": A.boot_mean(acc - maj)}
        res[key]["majority"] = {"acc": float(maj.mean()), "cost": float(mcost.mean())}
    res.pop("downstream")

    # T1: importance-weighted vote toward p^alpha
    t1 = {}
    for per_token in (False, True):
        for alpha in ((1, 1.02, 1.05, 1.1, 1.25, 1.5, 2) if not per_token else (1, 5, 10, 20, 50, 100)):
            accs, ess = [], []
            for q in ev:
                g, e = is_vote(q, alpha, per_token)
                accs.append(float(g is not None and q["group_right"].get(g, False)))
                ess.append(e)
            t1[f"{'per-token' if per_token else 'sequence'} alpha={alpha}"] = {
                "acc": float(np.mean(accs)), "median_ess": float(np.nanmedian(ess)),
                "share_ess_lt4": float(np.nanmean(np.array(ess) < 4))}
    res["T1_importance_vote"] = t1
    res["T2_lockin"] = t2(data)
    res["PoT_probe"] = pot_probe(data)
    res["T3_temperature"] = {k: {kk: vv for kk, vv in v.items() if kk != "maj_per_q"} for k, v in t3(data).items()}
    Path("runs/evidence_grid.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    write_md(res)


def write_md(res):
    f = lambda x: "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.3f}"
    md = ["# Phase 3b checkpoint: evidence grid and sampling (test ∪ extra)", "",
          "## Evidence grid (group level; higher AUROC = flags the wrong group)", "",
          "| Source | top-2 AUROC (pairs) | coverage | right vs attractor | right vs one-off | dev top-2 |",
          "|---|---|---|---|---|---|"]
    for n, v in sorted(res["grid"].items(), key=lambda kv: -np.nan_to_num(kv[1]["top2_auroc"][0])):
        md.append(f"| {n} | {f(v['top2_auroc'][0])} ({v['top2_auroc'][1]}) | {100 * v['coverage_top2']:.0f}% | "
                  f"{f(v['right_vs_attractor'][0])} ({v['right_vs_attractor'][1]}) | "
                  f"{f(v['right_vs_oneoff'][0])} ({v['right_vs_oneoff'][1]}) | {f(v['dev']['top2_auroc'][0])} |")
    c = res["combination"]
    md += ["", f"Combination: {', '.join(c['sources'])}; coefficients {', '.join(f'{x:+.2f}' for x in c['coef'])} "
               f"(last = intercept), fitted on {c['dev_groups']} dev groups of contested questions."]
    for key, title in (("downstream_esc2", "ESC-2 gated (stop when the first two attempts agree)"),
                       ("downstream_all16", "all 16 attempts (vs majority@16: beyond the vote ceiling?)")):
        md += ["", f"## Downstream, {title}: argmax n_g + w·logit(1 − suspicion), w tuned on dev", "",
               "| Source | w | accuracy | vs majority [95% CI] |", "|---|---|---|---|"]
        for n, v in res[key].items():
            d = v.get("vs_majority")
            md.append(f"| {n} | {v.get('w', '—')} | {100 * v['acc']:.2f} | "
                      + (f"{100 * d[0]:+.2f} [{100 * d[1][0]:+.2f}, {100 * d[1][1]:+.2f}]" if d else
                         f"cost {v.get('cost', 0):.2f}") + " |")
    md += ["", "## T1 Importance-weighted vote toward p^α (16 attempts, self-normalised)", "",
           "| Target | accuracy | median ESS | share ESS < 4 |", "|---|---|---|---|"]
    for k, v in res["T1_importance_vote"].items():
        md.append(f"| {k} | {100 * v['acc']:.1f} | {v['median_ess']:.2f} | {100 * v['share_ess_lt4']:.0f}% |")
    if res["T2_lockin"]:
        t = res["T2_lockin"]
        md += ["", f"## T2 Lock-in: continuations from a prefix ({t['questions']} questions)", "",
               "| Source | right | attractor | other | no answer |", "|---|---|---|---|---|",
               "| fresh attempts (cached 16) | " + " | ".join(f"{100 * t['fresh'][k]:.1f}" for k in
                                                       ("right", "attractor", "other", "none")) + " |"]
        for k, v in t["resample"].items():
            md.append(f"| {k} | " + " | ".join(f"{100 * v[x]:.1f}" for x in ("right", "attractor", "other", "none")) + " |")
    p = res["PoT_probe"]
    d = p["mixed_vs_majority"]
    md += ["", f"## Program-of-thought as a second voter ({p['questions_with_pot']} questions, 4 programs each)", "",
           f"- language plurality is a single wrong group on {p['wrong_plurality']} questions; there the PoT plurality "
           f"differs from it {100 * p['pot_plurality_differs']:.0f}% of the time and is right "
           f"{100 * p['pot_plurality_right']:.0f}% of the time",
           f"- PoT plurality alone: {100 * p['pot_majority_alone']:.1f}%",
           f"- majority@16 + PoT votes (weight {p['lambda']}, tuned on dev): {100 * p['mixed']:.2f} vs "
           f"{100 * p['majority16']:.2f}, {100 * d[0]:+.2f} [{100 * d[1][0]:+.2f}, {100 * d[1][1]:+.2f}]"]
    md += ["", "## T3 Temperature (400 test questions × 8)", "",
           "| Sampler | questions | single | attractor share | pass@8 | majority@8 | Δ majority vs T 1.0 (mean of both cached draws) "
           "[95% CI] |", "|---|---|---|---|---|---|---|"]
    for k, v in res["T3_temperature"].items():
        d = v.get("majority_diff")
        md.append(f"| {k} | {v.get('questions', 400)} | {100 * v['single']:.1f} | {100 * v['attractor_share']:.1f} | "
                  f"{100 * v['pass@8']:.1f} | {100 * v['majority@8']:.1f} | "
                  + (f"{100 * d[0]:+.2f} [{100 * d[1][0]:+.2f}, {100 * d[1][1]:+.2f}] (base {100 * v['paired_base_majority@8']:.1f})"
                     if d else "—") + " |")
    Path("runs/evidence_grid.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
