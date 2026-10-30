"""Phase 3b CPU analyses on the cached attempts and judgments (no GPU).

    python phase3/cpu_analyses.py        (from phase3/: uses runs/graded, runs/main/judge, runs/main/attempts)

F0.1 shared bias: within-question AUROC of right attempts vs the solver's ATTRACTOR wrong answer (its most common wrong
     answer, >= 2 attempts) vs ONE-OFF wrong answers (1 attempt).
F0.2 within-answer-group error correlation (intraclass correlation of logit scores among attempts with the same answer).
F0.3 difficulty share: a question-only predictor (leave-one-out solve rate of the other 15 attempts) vs the judge, pooled;
     the judge's signal after removing difficulty (logistic regression; within-question AUROC).
F0.4 the same for judge-free trace features (length, self-corrections, guess phrases).
F0.6 free baselines: CISC with P(True) (softmax-weighted vote over the direct score, temperature tuned on dev) at
     N = 4, 8, 16; early-stopping self-consistency (window w); adaptive-consistency (from analyze.py) — all vs majority at
     matched cost on test ∪ extra.
Writes runs/cpu_analyses.json and runs/cpu_analyses.md.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import optimize, special

import analyze as A
from trace_features import GUESS, RETRACT

G, J, T = Path("runs/graded"), Path("runs/main/judge"), Path("runs/main/attempts")
L = lambda p: special.logit(np.clip(p, 1e-4, 1 - 1e-4))


def load_all():
    data = {s: A.load(G, J, s) for s in ("dev", "test", "extra")}
    for s, qs in data.items():
        feats = {}
        for f in sorted((T / s).glob("[0-9][0-9][0-9].jsonl")):
            for line in f.open():
                r = json.loads(line)
                feats[(r["uid"], r["k"])] = (len(RETRACT.findall(r["text"])), len(GUESS.findall(r["text"])))
        for q in data[s]:
            q["retr"] = np.array([feats[(q["uid"], k)][0] for k in range(q["n"])], float)
            q["guess"] = np.array([feats[(q["uid"], k)][1] for k in range(q["n"])], float)
            q["loo"] = np.array([(q["correct"].sum() - q["correct"][k]) / (q["n"] - 1) for k in range(q["n"])])
    return data


SCORES = {  # higher = more suspicious ("wrong")
    "judge chain": lambda q: q["p"][:, 0],
    "judge direct": lambda q: q["pdir"],
    "length": lambda q: q["tokens"],
    "self-corrections": lambda q: q["retr"],
    "guess phrases": lambda q: q["guess"],
    "difficulty only (LOO solve rate)": lambda q: -q["loo"],  # pooled only; 0.5 within by construction
}


def f01_attractor(qs, score, contested_only=False):
    """Within-question pair AUROC: right vs attractor-wrong, and right vs one-off-wrong."""
    att, one = [], []
    for q in qs:
        if contested_only and not A.contested(q):
            continue
        s = score(q)
        m = q["answered"] & ~np.isnan(s)
        cnt = Counter(q["group"][m & ~q["correct"]].tolist())
        right = s[m & q["correct"]]
        if not len(right):
            continue
        for i in np.where(m & ~q["correct"])[0]:
            bucket = att if cnt[q["group"][i]] >= 2 else one
            for r in right:
                bucket.append(1.0 if s[i] > r else 0.5 if s[i] == r else 0.0)
    return (float(np.mean(att)) if att else np.nan, len(att)), (float(np.mean(one)) if one else np.nan, len(one))


def f02_icc(qs, score):
    """Intraclass correlation of logit scores within answer groups (groups of >= 2), separately for right / wrong groups."""
    out = {}
    for label in (True, False):
        groups = []
        for q in qs:
            s = score(q)
            for g in set(q["group"][q["answered"]].tolist()):
                mem = np.where((q["group"] == g) & q["answered"] & ~np.isnan(s) & (q["correct"] == label))[0]
                if len(mem) >= 2:
                    groups.append(L(s[mem]) - np.mean(L(s[q["answered"] & ~np.isnan(s)])))  # centre per question
        if not groups:
            out["right" if label else "wrong"] = np.nan
            continue
        allv = np.concatenate(groups)
        within = np.mean([np.var(g, ddof=1) for g in groups])
        between = np.var([g.mean() for g in groups], ddof=1) - within / np.mean([len(g) for g in groups])
        out["right" if label else "wrong"] = float(max(0.0, between) / (max(0.0, between) + within))
        out[("right" if label else "wrong") + "_groups"] = len(groups)
    return out


def f03_difficulty(qs):
    """Pooled AUROC of a question-only predictor, and the judge's added value over it (logistic regression, pooled)."""
    rows = [(not q["correct"][k], -q["loo"][k], L(q["p"][k, 0]), L(q["pdir"][k]))
            for q in qs for k in range(q["n"]) if q["answered"][k] and not np.isnan(q["p"][k, 0])]
    R = np.array(rows, float)
    y, d, c, dr = R[:, 0].astype(bool), R[:, 1], R[:, 2], R[:, 3]

    def fit_auc(X):
        X = np.c_[X, np.ones(len(X))]
        f = lambda w: (np.mean(np.logaddexp(0, X @ w) - y * (X @ w)), X.T @ (special.expit(X @ w) - y) / len(y))
        w = optimize.minimize(f, np.zeros(X.shape[1]), jac=True).x
        return float(A.auroc(X @ w, y)), w.tolist()
    return {"pooled_auroc_difficulty_only": float(A.auroc(d, y)), "pooled_auroc_judge_chain": float(A.auroc(c, y)),
            "pooled_auroc_judge_direct": float(A.auroc(dr, y)),
            "difficulty+chain": fit_auc(np.c_[d, c])[0], "difficulty+direct": fit_auc(np.c_[d, dr])[0],
            "difficulty+chain+direct": fit_auc(np.c_[d, c, dr])[0]}


# ------------------------------------------------------------------ free baselines

def cisc_rule(q, order, n, temp, rng):
    """CISC with P(True): softmax(confidence / T) weights summed per answer; confidence = logit P(correct)."""
    a, g = q["answered"][order][:n], q["group"][order][:n]
    pc = 1 - np.nan_to_num(q["pdir"][order][:n], nan=0.5)
    w = np.exp(L(pc) / temp)
    w = np.where(a, w, 0.0)
    return A.pick_groups(g, w / max(w.sum(), 1e-12), a, rng)


def esc_rule(q, order, window, nmax, rng):
    """Early-stopping self-consistency: sample in windows of w; stop when a window is unanimous (answered)."""
    a, g = q["answered"][order], q["group"][order]
    n = nmax
    for start in range(0, nmax, window):
        wa, wg = a[start:start + window], g[start:start + window]
        if len(wg) == window and wa.all() and len(set(wg.tolist())) == 1:
            n = start + window
            break
    return A.pick_groups(g[:n], np.ones(n), a[:n], rng), n


def evaluate_free(qs, temps, seed=5, R=100):
    rng = np.random.default_rng(seed)
    acc, cost = defaultdict(list), defaultdict(list)
    for q in qs:
        ta, tc = defaultdict(float), defaultdict(float)
        for _ in range(R):
            o = rng.permutation(q["n"])
            right = lambda gr: gr is not None and q["group_right"].get(gr, False)
            for n in (1, 2, 4, 6, 8, 10, 12, 14, 16):
                ta[f"majority@{n}"] += right(A.pick_groups(q["group"][o][:n], np.ones(n), q["answered"][o][:n], rng))
                tc[f"majority@{n}"] += n
            for n in (4, 8, 16):
                for t in temps:
                    k = f"cisc@{n},T{t}"
                    ta[k] += right(cisc_rule(q, o, n, t, rng))
                    tc[k] += n + A.COST_DIRECT * q["answered"][o][:n].sum()
            for w in (2, 4, 8):
                gr, used = esc_rule(q, o, w, 16, rng)
                ta[f"esc@w{w}"] += right(gr)
                tc[f"esc@w{w}"] += used
        for k in ta:
            acc[k].append(ta[k] / R)
            cost[k].append(tc[k] / R)
    return {k: np.array(v) for k, v in acc.items()}, {k: np.array(v) for k, v in cost.items()}


def main():
    data = load_all()
    ev = data["test"] + data["extra"]
    out = {"F0.1": {}, "F0.2": {}, "F0.4_pooled_within_contested": {}}
    for name, fn in SCORES.items():
        if name.startswith("difficulty only"):
            # question-level score: 0.5 within a question by construction (leave-one-out would leak the label); pooled only
            lab = np.concatenate([~q["correct"][q["answered"]] for q in ev])
            sc = np.concatenate([fn(q)[q["answered"]] for q in ev])
            out["F0.4_pooled_within_contested"][name] = {"pooled": float(A.auroc(sc, lab)), "within": 0.5, "contested": 0.5}
            continue
        (att, na), (one, no) = f01_attractor(ev, fn)
        (catt, cna), (cone, cno) = f01_attractor(ev, fn, contested_only=True)
        out["F0.1"][name] = {"right_vs_attractor": att, "pairs_attractor": na, "right_vs_oneoff": one, "pairs_oneoff": no,
                             "contested_right_vs_attractor": catt, "contested_right_vs_oneoff": cone}
        lab = np.concatenate([~q["correct"][q["answered"]] for q in ev])
        sc = np.concatenate([fn(q)[q["answered"]] for q in ev])
        ok = ~np.isnan(sc)
        out["F0.4_pooled_within_contested"][name] = {
            "pooled": float(A.auroc(sc[ok], lab[ok])), "within": A.boot_ratio(A.within_pairs(ev, fn), B=500)[0],
            "contested": A.boot_ratio(A.within_pairs(ev, fn, contested_only=True), B=500)[0]}
    for name in ("judge chain", "judge direct"):
        out["F0.2"][name] = f02_icc(ev, SCORES[name])
    out["F0.3"] = f03_difficulty(ev)

    # free baselines: tune CISC temperature and ESC window on dev, evaluate on test ∪ extra
    temps = [0.25, 0.5, 1.0, 2.0, 4.0]
    dacc, _ = evaluate_free(data["dev"], temps, seed=2)
    best_t = {n: max(temps, key=lambda t: dacc[f"cisc@{n},T{t}"].mean()) for n in (4, 8, 16)}
    acc, cost = evaluate_free(ev, temps, seed=11)
    base = {}
    for n in (4, 8, 16):
        k = f"cisc@{n},T{best_t[n]}"
        maj = A.matched_majority(acc, cost, cost[k].mean())
        base[f"CISC-P(True) N={n} (T={best_t[n]})"] = {"acc": float(acc[k].mean()), "cost": float(cost[k].mean()),
                                                      "vs_majority_same_cost": A.boot_mean(acc[k] - maj),
                                                      "vs_majority_same_N": A.boot_mean(acc[k] - acc[f"majority@{n}"])}
    for w in (2, 4, 8):
        k = f"esc@w{w}"
        maj = A.matched_majority(acc, cost, cost[k].mean())
        base[f"ESC window {w}"] = {"acc": float(acc[k].mean()), "cost": float(cost[k].mean()),
                                   "vs_majority_same_cost": A.boot_mean(acc[k] - maj)}
    base["majority@16"] = {"acc": float(acc["majority@16"].mean()), "cost": 16.0}
    out["F0.6_free_baselines"] = base

    Path("runs/cpu_analyses.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    f3 = lambda x: "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.3f}"
    md = ["# Phase 3b CPU analyses (test ∪ extra, 800 questions)", "",
          "## F0.4 Pooled vs within-question vs contested AUROC (higher = flags wrong attempts)", "",
          "| Signal | Pooled | Within question | Contested |", "|---|---|---|---|"]
    for k, v in out["F0.4_pooled_within_contested"].items():
        md.append(f"| {k} | {f3(v['pooled'])} | {f3(v['within'])} | {f3(v['contested'])} |")
    md += ["", "## F0.1 Shared bias: right vs the solver's attractor wrong answer vs one-off wrong answers", "",
           "| Signal | right vs attractor | right vs one-off | contested: attractor | contested: one-off |", "|---|---|---|---|---|"]
    for k, v in out["F0.1"].items():
        md.append(f"| {k} | {f3(v['right_vs_attractor'])} ({v['pairs_attractor']} pairs) | {f3(v['right_vs_oneoff'])} "
                  f"({v['pairs_oneoff']}) | {f3(v['contested_right_vs_attractor'])} | {f3(v['contested_right_vs_oneoff'])} |")
    md += ["", "## F0.2 Within-answer-group error correlation (intraclass correlation of logit scores)", ""]
    for k, v in out["F0.2"].items():
        md.append(f"- {k}: right groups {f3(v.get('right'))} ({v.get('right_groups')} groups), wrong groups "
                  f"{f3(v.get('wrong'))} ({v.get('wrong_groups')} groups)")
    md += ["", "## F0.3 Difficulty share (pooled AUROC)", ""]
    for k, v in out["F0.3"].items():
        md.append(f"- {k}: {v:.3f}")
    md += ["", "## F0.6 Free baselines (dev-tuned, test ∪ extra)", "", "| Rule | Accuracy | Cost | vs majority at same cost |",
           "|---|---|---|---|"]
    for k, v in base.items():
        d = v.get("vs_majority_same_cost")
        md.append(f"| {k} | {100*v['acc']:.1f} | {v['cost']:.2f} | "
                  + (f"{100*d[0]:+.2f} [{100*d[1][0]:+.2f}, {100*d[1][1]:+.2f}]" if d else "—") + " |")
    Path("runs/cpu_analyses.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
