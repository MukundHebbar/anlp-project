"""Phase-3 analysis on cached attempts and judge chains (CPU, numpy/scipy only).

    python phase3/analyze.py --graded runs/graded --judge runs/judge --out runs/analysis

Everything is computed on the same cached pools. Selection rules are averaged over R random orders of each
question's attempts (so N < 16 rules see random subsets), and differences are bootstrapped over questions.
Costs: attempt = 1 unit, judge chain = 0.3 units (pre-registered); token costs are reported alongside.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import special, stats

COST_JUDGE = 0.3   # one reasoning chain (pre-registered unit cost)
COST_DIRECT = 0.05  # one prefill-only verdict read (deviation: added after the smoke test, see PREREGISTRATION.md)
R = 100  # random orders per question (semisynth uses the same)
# P(p1 > p2) under Beta(c1 + 1, c2 + 1) posteriors, the adaptive-consistency stopping statistic, for counts <= 16
_AC = np.array([[stats.beta.sf(0.5, c1 + 1, c2 + 1) for c2 in range(17)] for c1 in range(17)])


# ------------------------------------------------------------------ loading

def load(graded: Path, judge: Path, name: str) -> list[dict]:
    """Per question: arrays over attempts k = 0..N-1."""
    att = defaultdict(dict)
    for line in (graded / f"{name}.jsonl").open():
        r = json.loads(line)
        att[r["uid"]][r["k"]] = r
    chains = defaultdict(lambda: defaultdict(dict))
    for f in sorted((judge / name).glob("[0-9][0-9][0-9].jsonl")):
        for line in f.open():
            c = json.loads(line)
            chains[c["uid"]][c["k"]][c["chain"]] = c
    qs = []
    for uid, d in att.items():
        n = max(d) + 1
        ks = range(n)
        answered = np.array([d[k]["group"] >= 0 for k in ks])
        p = np.full((n, 4), np.nan)
        pdir = np.full(n, np.nan)
        reached = np.zeros((n, 4), bool)
        jtok = np.zeros((n, 4))
        for k in ks:
            for j, c in chains[uid].get(k, {}).items():
                if c["p_incorrect"] is not None:
                    p[k, j] = c["p_incorrect"]
                if c.get("p_direct") is not None:
                    pdir[k] = c["p_direct"]
                reached[k, j] = c["reached_label"]
                jtok[k, j] = c["chain_tokens"]
        groups = np.array([d[k]["group"] for k in ks])
        matches = np.array([d[k]["answer_matches"] for k in ks])
        right_groups = set(groups[matches & (groups >= 0)].tolist())
        qs.append({"uid": uid, "n": n, "correct": np.array([d[k]["correct"] for k in ks]), "answered": answered,
                   "group": groups, "group_right": {g: g in right_groups for g in set(groups.tolist()) if g >= 0},
                   "tokens": np.array([d[k]["tokens"] for k in ks], float), "p": p, "pdir": pdir, "reached": reached,
                   "jtok": jtok})
    return qs


# ------------------------------------------------------------------ learned combiner (exploratory; fit on dev only)

def add_features(qs, attempts_dir: Path, name: str) -> None:
    """Per attempt: logit P(incorrect) after a chain and direct, log length, log self-corrections, log guesses, tags."""
    from trace_features import GUESS, RETRACT, TAG
    texts = {}
    for f in sorted((attempts_dir / name).glob("[0-9][0-9][0-9].jsonl")):
        for line in f.open():
            r = json.loads(line)
            texts[(r["uid"], r["k"])] = r["text"]
    lg = lambda p: special.logit(np.clip(np.nan_to_num(p, nan=0.5), 1e-4, 1 - 1e-4))
    for q in qs:
        t = [texts[(q["uid"], k)] for k in range(q["n"])]
        q["X"] = np.stack([lg(q["p"][:, 0]), lg(q["pdir"]), np.log1p(q["tokens"]),
                           np.log1p([len(RETRACT.findall(x)) for x in t]), np.log1p([len(GUESS.findall(x)) for x in t]),
                           np.array([len(TAG.findall(x)) for x in t], float)], 1)


def fit_combiner(qs, cols, lam=1e-2):
    """Pairwise logistic regression on same-question (wrong - right) feature differences."""
    from scipy import optimize
    D = [q["X"][i][cols] - q["X"][j][cols] for q in qs
         for i in np.where(q["answered"] & ~q["correct"])[0] for j in np.where(q["answered"] & q["correct"])[0]]
    X = np.r_[np.array(D), -np.array(D)]
    y = np.r_[np.ones(len(D)), np.zeros(len(D))]
    f = lambda w: (np.mean(np.logaddexp(0, X @ w) - y * (X @ w)) + lam * w @ w,
                   X.T @ (special.expit(X @ w) - y) / len(y) + 2 * lam * w)
    return optimize.minimize(f, np.zeros(X.shape[1]), jac=True).x


def apply_combiner(qs, cols, w, key) -> None:
    for q in qs:
        q[key] = np.where(q["answered"], special.expit(q["X"][:, cols] @ w), np.nan)


# ------------------------------------------------------------------ AUROC helpers

def auroc(score, label):
    score, label = np.asarray(score, float), np.asarray(label, bool)
    ok = ~np.isnan(score)
    score, label = score[ok], label[ok]
    n1, n0 = label.sum(), (~label).sum()
    if n1 == 0 or n0 == 0:
        return np.nan
    r = stats.rankdata(score)
    return (r[label].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def within_pairs(qs, score_fn, contested_only=False):
    """(concordant + ties/2, pairs) per question for wrong-vs-right attempts of the same question."""
    out = []
    for q in qs:
        s = score_fn(q)
        m = q["answered"] & ~np.isnan(s)
        w, r = s[m & ~q["correct"]], s[m & q["correct"]]
        if contested_only and not contested(q):
            continue
        if len(w) and len(r):
            conc = (w[:, None] > r[None, :]).sum() + 0.5 * (w[:, None] == r[None, :]).sum()
            out.append((conc, len(w) * len(r)))
    return np.array(out) if out else np.zeros((0, 2))


def contested(q):
    """No strict majority for the right answer among answered attempts (where picking can matter)."""
    g = q["group"][q["answered"]]
    if not len(g):
        return False
    cnt = Counter(g.tolist())
    right = [c for gg, c in cnt.items() if q["group_right"].get(gg)]
    top_wrong = max([c for gg, c in cnt.items() if not q["group_right"].get(gg)], default=0)
    return bool(right) and right[0] <= top_wrong


def boot_ratio(arr, B=2000, seed=0):
    rng = np.random.default_rng(seed)
    if not len(arr):
        return np.nan, (np.nan, np.nan)
    est = arr[:, 0].sum() / arr[:, 1].sum()
    idx = rng.integers(0, len(arr), (B, len(arr)))
    bs = arr[idx, 0].sum(1) / arr[idx, 1].sum(1)
    return est, tuple(np.percentile(bs, [2.5, 97.5]))


def boot_mean(x, B=2000, seed=0):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    bs = x[rng.integers(0, len(x), (B, len(x)))].mean(1)
    return x.mean(), tuple(np.percentile(bs, [2.5, 97.5]))


# ------------------------------------------------------------------ selection rules on one ordered pool

def pick_groups(groups, weights, answered, rng):
    """Group with the largest summed weight among answered attempts; random tie-break. None if nothing answered."""
    tot = defaultdict(float)
    for g, w, a in zip(groups, weights, answered):
        if a:
            tot[g] += w
    if not tot:
        return None
    best = max(tot.values())
    cands = [g for g, v in tot.items() if np.isclose(v, best)]
    return cands[rng.integers(len(cands))]


def logit_right(p):
    return special.logit(np.clip(1 - p, 1e-4, 1 - 1e-4))


def run_order(q, order, rng, beta_bayes, cav_cfgs, ac_thresholds, Ns):
    """All rules on one random order of the question's attempts. Returns {rule: (right, cost)}."""
    g, a, p0 = q["group"][order], q["answered"][order], q["p"][order, 0]
    right = lambda gr: gr is not None and q["group_right"].get(gr, False)
    res = {}
    for n in Ns:
        tk = q["tokens"][order][:n].sum()
        jk = q["jtok"][order, 0][:n].sum()
        res[f"majority@{n}"] = (right(pick_groups(g[:n], np.ones(n), a[:n], rng)), n, tk)
        res[f"oracle@{n}"] = (any(q["group_right"].get(x, False) for x, y in zip(g[:n], a[:n]) if y), n, tk)
        lo = np.where(np.isnan(p0[:n]), 0.0, logit_right(np.nan_to_num(p0[:n], nan=0.5)))
        nj = int(a[:n].sum())
        res[f"bayes@{n}"] = (right(pick_groups(g[:n], beta_bayes + lo, a[:n], rng)), n + COST_JUDGE * nj, tk + jk)
        cand = np.where(a[:n] & ~np.isnan(p0[:n]))[0]
        pick = cand[np.argmin(p0[:n][cand])] if len(cand) else None
        res[f"argmax@{n}"] = (pick is not None and right(g[:n][pick]), n + COST_JUDGE * nj, tk + jk)
    # adaptive-consistency (Aggarwal et al. 2023, Beta stopping on the top two answer counts)
    for t in ac_thresholds:
        n_used = len(order)
        for n in range(2, len(order) + 1):
            cnt = sorted(Counter(g[:n][a[:n]].tolist()).values(), reverse=True) + [0, 0]
            if _AC[cnt[0], cnt[1]] > t:
                n_used = n
                break
        res[f"ac@{t}"] = (right(pick_groups(g[:n_used], np.ones(n_used), a[:n_used], rng)), n_used,
                          q["tokens"][order][:n_used].sum())
    # contest-adaptive verification
    first = g[:4][a[:4]]
    unanimous = a[:4].all() and len(set(first.tolist())) == 1
    tok, jt = q["tokens"][order], q["jtok"][order, 0]
    for (n1, m, beta, src) in cav_cfgs:
        key = f"cav-{src}@{n1},{m},{beta}"
        if unanimous:
            res[key] = (right(first[0]), 4, tok[:4].sum())
            continue
        gg, aa = g[:n1], a[:n1]
        pp = {"chain": p0, "direct": q["pdir"][order], "combo": q.get("pcombo", q["pdir"])[order],
              "combo-cheap": q.get("pcheap", q["pdir"])[order]}[src][:n1]
        unit = COST_JUDGE if src in ("chain", "combo") else COST_DIRECT
        sizes = Counter(gg[aa].tolist())
        if not sizes:
            res[key] = (False, n1, tok[:n1].sum())
            continue
        ranked = sorted(sizes, key=lambda x: (-sizes[x], rng.random()))[:2]
        cost, tcost, best, best_s = n1, tok[:n1].sum(), None, -np.inf
        for gr in ranked:
            members = np.where(aa & (gg == gr))[0][:m]
            vals = pp[members]
            vals = vals[~np.isnan(vals)]
            cost += unit * len(members)
            if src in ("chain", "combo"):
                tcost += jt[members].sum()
            ev = logit_right(vals).mean() if len(vals) else 0.0
            s = sizes[gr] * (beta + ev) + rng.random() * 1e-9
            if s > best_s:
                best, best_s = gr, s
        res[key] = (right(best), cost, tcost)
    return res


def evaluate(qs, beta_bayes, cav_cfgs, ac_thresholds, Ns, seed=1):
    """Per-question expected accuracy and cost of every rule, averaged over R random orders."""
    rng = np.random.default_rng(seed)
    acc, cost, tcost = defaultdict(list), defaultdict(list), defaultdict(list)
    for q in qs:
        tot_a, tot_c, tot_t = defaultdict(float), defaultdict(float), defaultdict(float)
        for _ in range(R):
            res = run_order(q, rng.permutation(q["n"]), rng, beta_bayes, cav_cfgs, ac_thresholds, Ns)
            for k, (r, c, t) in res.items():
                tot_a[k] += r
                tot_c[k] += c
                tot_t[k] += t
        for k in tot_a:
            acc[k].append(tot_a[k] / R)
            cost[k].append(tot_c[k] / R)
            tcost[k].append(tot_t[k] / R)
    evaluate.tokens = {k: np.array(v) for k, v in tcost.items()}
    return {k: np.array(v) for k, v in acc.items()}, {k: np.array(v) for k, v in cost.items()}


# ------------------------------------------------------------------ reports

def judge_block(qs) -> dict:
    """Test set, first 4 attempts with 4 chains each: leniency, sampled vs probability scoring, verdict dispersion."""
    rng = np.random.default_rng(7)
    lab, p4, s4, pd = [], [], [], []
    for q in qs:
        for k in range(min(4, q["n"])):
            if not q["answered"][k] or np.isnan(q["p"][k]).any():
                continue
            lab.append(not q["correct"][k])
            p4.append(q["p"][k])
            pd.append(q["pdir"][k])
            s4.append(rng.random(4) < q["p"][k])          # one sampled verdict per chain ("incorrect" = True)
    lab, p4, s4, pd = np.array(lab), np.array(p4), np.array(s4), np.array(pd)
    h, f = s4[lab, 0].mean(), s4[~lab, 0].mean()
    k_inc = s4.sum(1)
    out = {
        "n_attempts": int(len(lab)), "share_wrong": float(lab.mean()),
        "incorrect_share_sampled": float(s4.mean()),
        "hit_rate": float(h), "false_alarm_rate": float(f),
        "dprime": float(stats.norm.ppf(np.clip(h, 1e-4, 1 - 1e-4)) - stats.norm.ppf(np.clip(f, 1e-4, 1 - 1e-4))),
        "auroc_1_sampled": float(auroc(s4[:, 0].astype(float), lab)),
        "auroc_4_sampled_share": float(auroc(s4.mean(1), lab)),
        "auroc_prob_1chain": float(auroc(p4[:, 0], lab)),
        "auroc_prob_mean4": float(auroc(p4.mean(1), lab)),
        "auroc_direct": float(auroc(pd, lab)),
        "direct_incorrect_mean": float(np.nanmean(pd)),
        "verdict_count_dist_wrong": np.bincount(k_inc[lab], minlength=5).tolist(),
        "verdict_count_dist_right": np.bincount(k_inc[~lab], minlength=5).tolist(),
        "binomial_p4of4_wrong": float(s4[lab].mean() ** 4),
        "observed_p4of4_wrong": float((k_inc[lab] == 4).mean()),
        "chain_corr_p": float(np.corrcoef(p4[:, 0], p4[:, 1])[0, 1]),
    }
    reached = np.concatenate([q["reached"][:4][q["answered"][:4]].ravel() for q in qs])
    out["reached_label_rate"] = float(reached.mean())
    return out


def auroc_block(qs) -> dict:
    lab, sc = [], []
    for q in qs:
        m = q["answered"] & ~np.isnan(q["p"][:, 0])
        lab += (~q["correct"][m]).tolist()
        sc += q["p"][m, 0].tolist()
    w_all = within_pairs(qs, lambda q: q["p"][:, 0])
    w_con = within_pairs(qs, lambda q: q["p"][:, 0], contested_only=True)
    d_all = within_pairs(qs, lambda q: q["pdir"])
    d_con = within_pairs(qs, lambda q: q["pdir"], contested_only=True)
    length = within_pairs(qs, lambda q: q["tokens"])
    keep = [q["answered"] & ~np.isnan(q["p"][:, 0]) for q in qs]
    sd = [x for q, m in zip(qs, keep) for x in q["pdir"][m]]
    sl = [x for q, m in zip(qs, keep) for x in q["tokens"][m]]
    return {"global_auroc_prob": float(auroc(sc, lab)), "within_auroc_prob": [*boot_ratio(w_all), int(len(w_all))],
            "contested_within_auroc_prob": [*boot_ratio(w_con), int(len(w_con))],
            "global_auroc_direct": float(auroc(sd, lab)), "within_auroc_direct": [*boot_ratio(d_all), int(len(d_all))],
            "contested_within_auroc_direct": [*boot_ratio(d_con), int(len(d_con))],
            "within_auroc_length": list(boot_ratio(length)), "global_auroc_length": float(auroc(sl, lab)),
            "n_attempts_judged": len(lab)}


def config_table(qs, n=4, reps=50, seed=3) -> dict:
    rng = np.random.default_rng(seed)
    tab = Counter()
    for q in qs:
        for _ in range(reps):
            o = rng.permutation(q["n"])[:n]
            g, a = q["group"][o], q["answered"][o]
            cnt = Counter(g[a].tolist())
            k = sum(c for gg, c in cnt.items() if q["group_right"].get(gg))
            wrong = sorted((c for gg, c in cnt.items() if not q["group_right"].get(gg)), reverse=True)
            top = wrong[0] if wrong else 0
            kind = ("unwinnable" if k == 0 else "majority right" if k > top
                    else "tie" if k == top else "overturn")
            tab[kind] += 1 / reps
    total = sum(tab.values())
    return {k: v / total for k, v in tab.items()}


def matched_majority(acc, cost, target):
    """Majority mixed between the two N whose mean cost brackets ``target`` (unit or token cost), per question."""
    ns = sorted(int(k.split("@")[1]) for k in acc if k.startswith("majority@"))
    c = {n: float(cost[f"majority@{n}"].mean()) for n in ns}
    lo = max([n for n in ns if c[n] <= target], default=ns[0])
    hi = min([n for n in ns if c[n] >= target], default=ns[-1])
    if lo == hi or c[hi] == c[lo]:
        return acc[f"majority@{lo}"]
    w = (target - c[lo]) / (c[hi] - c[lo])
    return (1 - w) * acc[f"majority@{lo}"] + w * acc[f"majority@{hi}"]


def markdown(rep: dict) -> str:
    f3 = lambda x: f"{x[0]:.3f} [{x[1][0]:.3f}, {x[1][1]:.3f}]"
    f4 = lambda d: f"{d[0]:+.4f} [{d[1][0]:+.4f}, {d[1][1]:+.4f}]"
    L = ["# Phase-3 results (generated by phase3/analyze.py)", "", "## Pools", "",
         "| Set | Questions | Single attempt | Answered | Attempt tokens | Chain tokens | Score | Global AUROC | "
         "Within AUROC [CI] | Contested within AUROC [CI] |", "|---|---|---|---|---|---|---|---|---|---|"]
    for s in ("dev", "test", "extra"):
        if s not in rep:
            continue
        r, au = rep[s], rep[s]["auroc"]
        L.append(f"| {s} | {r['questions']} | {r['single_attempt']:.3f} | {r['answered']:.3f} | {r['mean_attempt_tokens']:.0f} | "
                 f"{r['mean_chain_tokens']:.0f} | chain | {au['global_auroc_prob']:.3f} | {f3(au['within_auroc_prob'])} | "
                 f"{f3(au['contested_within_auroc_prob'])} |")
        L.append(f"| | | | | | | direct | {au['global_auroc_direct']:.3f} | {f3(au['within_auroc_direct'])} | "
                 f"{f3(au['contested_within_auroc_direct'])} |")
        L.append(f"| | | | | | | length | {au['global_auroc_length']:.3f} | {f3(au['within_auroc_length'])} | |")
    if "judge_first4" in rep.get("test", {}):
        L += ["", "## Stage 0: judge on test attempts 0-3 (4 chains each)", "", "| Measure | Value |", "|---|---|"]
        for k, v in rep["test"]["judge_first4"].items():
            L.append(f"| {k} | {v if isinstance(v, list) else round(v, 4)} |")
    L += ["", "## N = 4 configurations (share of questions)", ""]
    for s in ("dev", "test", "extra"):
        if s in rep:
            L.append(f"- {s}: " + ", ".join(f"{k} {v:.3f}" for k, v in sorted(rep[s]["configs_n4"].items())))
    if "eval" in rep:
        L += ["", f"## Selection on test + extra ({rep['eval']['questions']} questions; dev-tuned)", "",
              "| Rule | Accuracy | Average cost (units) | Decoded tokens |", "|---|---|---|---|"]
        for k, v in sorted(rep["eval"]["rules"].items(), key=lambda kv: (kv[0].split("@")[0], kv[1]["cost"])):
            L.append(f"| {k} | {v['acc']:.4f} | {v['cost']:.2f} | {v['tokens']:.0f} |")
        p = rep["primary"]
        L += ["", "## Primary comparison (pre-registered)", "",
              f"- {p['rule']}: accuracy {p['acc']:.4f} at cost {p['cost']:.2f} ({p['tokens']:.0f} decoded tokens)",
              f"- majority at the same cost: {p['majority_matched']:.4f}; difference {f4(p['diff_vs_majority'])}",
              f"- majority at the same decoded tokens: {p['majority_matched_tokens']:.4f}; difference "
              f"{f4(p['diff_vs_majority_tokens'])}",
              f"- adaptive-consistency t={p['ac_threshold']} (cost {p['ac_cost']:.2f}): {p['ac_acc']:.4f}; difference "
              f"{f4(p['diff_vs_ac'])}",
              "", "## Secondary CAV settings (dev-tuned beta)", "",
              "| Setting | Accuracy | Cost | Tokens | vs majority (cost) | vs majority (tokens) | vs adaptive-consistency |",
              "|---|---|---|---|---|---|---|"]
        for k, c in rep["secondary"].items():
            L.append(f"| {k} | {c['acc']:.4f} | {c['cost']:.2f} | {c['tokens']:.0f} | {f4(c['diff_vs_majority'])} | "
                     f"{f4(c['diff_vs_majority_tokens'])} | {f4(c['diff_vs_ac'])} |")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graded", default="phase3/runs/graded")
    ap.add_argument("--judge", default="phase3/runs/judge")
    ap.add_argument("--out", default="phase3/runs/analysis")
    ap.add_argument("--sets", default="dev,test,extra")
    ap.add_argument("--attempts", default="", help="attempt texts, for the exploratory learned combiner")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = {s: load(Path(a.graded), Path(a.judge), s) for s in a.sets.split(",")}
    report = {}
    if a.attempts:  # exploratory learned combiner: fit on dev pairs only, applied everywhere
        for s, qs in data.items():
            add_features(qs, Path(a.attempts), s)
        full, cheap = [0, 1, 2, 3, 4, 5], [1, 2, 3, 4, 5]
        w_full, w_cheap = fit_combiner(data["dev"], full), fit_combiner(data["dev"], cheap)
        for qs in data.values():
            apply_combiner(qs, full, w_full, "pcombo")
            apply_combiner(qs, cheap, w_cheap, "pcheap")
        report["combiner"] = {"features": ["chain", "direct", "log_len", "log_retract", "log_guess", "tags"],
                              "w_full": w_full.tolist(), "w_cheap": w_cheap.tolist()}
        for s, qs in data.items():
            if s != "dev":
                report.setdefault("combo_auroc", {})[s] = {
                    k: {"within": boot_ratio(within_pairs(qs, lambda q, k=k: q[k])),
                        "contested": boot_ratio(within_pairs(qs, lambda q, k=k: q[k], contested_only=True))}
                    for k in ("pcombo", "pcheap")}
    Ns = [1, 2, 4, 6, 8, 10, 12, 14, 16]
    for s, qs in data.items():
        corr = np.concatenate([q["correct"] for q in qs])
        report[s] = {"questions": len(qs), "single_attempt": float(corr.mean()),
                     "answered": float(np.concatenate([q["answered"] for q in qs]).mean()),
                     "mean_attempt_tokens": float(np.concatenate([q["tokens"] for q in qs]).mean()),
                     "mean_chain_tokens": float(np.concatenate([q["jtok"][:, 0][q["answered"]] for q in qs]).mean()),
                     "auroc": auroc_block(qs), "configs_n4": config_table(qs)}
    for s, qs in data.items():  # vote-only scaling curves per split (Rao-Blackwellised over random orders)
        acc_s, _ = evaluate(qs, 0.0, [], [], Ns, seed=5)
        report[s]["curves"] = {"N": Ns, "majority": [float(acc_s[f"majority@{n}"].mean()) for n in Ns],
                               "pass": [float(acc_s[f"oracle@{n}"].mean()) for n in Ns]}
    if "test" in data:
        report["test"]["judge_first4"] = judge_block(data["test"])

    # tuning on dev (pre-registered): beta for non-adaptive Bayes, beta for each CAV (N1, m, score source)
    betas = [float(b) for b in np.arange(-4.0, 3.01, 0.5)]
    srcs = ("chain", "direct") + (("combo", "combo-cheap") if a.attempts else ())
    cav_grid = [(n1, m, b, src) for n1 in (8, 12, 16) for m in (4, 8) for b in betas for src in srcs]
    ac_t = [0.6, 0.7, 0.8, 0.9, 0.95, 0.99]
    dev_acc, dev_cost = {}, {}
    for b in betas:
        acc, cost = evaluate(data["dev"], b, cav_grid if b == betas[0] else [], ac_t if b == betas[0] else [], [4, 8, 16])
        dev_acc[b], dev_cost[b] = acc, cost
    best_bayes = max(betas, key=lambda b: dev_acc[b]["bayes@16"].mean())
    base_acc = dev_acc[betas[0]]
    cav_best = {(n1, m, src): max(betas, key=lambda b: base_acc[f"cav-{src}@{n1},{m},{b}"].mean())
                for n1 in (8, 12, 16) for m in (4, 8) for src in srcs}
    report["tuning_dev"] = {"bayes_beta": best_bayes,
                            "cav_beta": {f"{k[2]}:{k[0]},{k[1]}": v for k, v in cav_best.items()},
                            "cav_dev": {f"{src}:{n1},{m}": [float(base_acc[f'cav-{src}@{n1},{m},{b}'].mean()),
                                                           float(dev_cost[betas[0]][f'cav-{src}@{n1},{m},{b}'].mean())]
                                        for (n1, m, src), b in cav_best.items()},
                            "ac_dev_cost": {t: float(dev_cost[betas[0]][f"ac@{t}"].mean()) for t in ac_t}}

    # evaluation on test + extra with the dev-chosen settings
    ev = [q for s in ("test", "extra") if s in data for q in data[s]]
    cfgs = [(n1, m, b, src) for (n1, m, src), b in cav_best.items()]
    acc, cost = evaluate(ev, best_bayes, cfgs, ac_t, Ns, seed=11)
    tok = evaluate.tokens
    report["eval"] = {"questions": len(ev), "rules": {k: {"acc": float(acc[k].mean()), "cost": float(cost[k].mean()),
                                                         "tokens": float(tok[k].mean())} for k in acc}}

    def compare(rule):
        c_star, t_star_tok = float(cost[rule].mean()), float(tok[rule].mean())
        maj = matched_majority(acc, cost, c_star)
        maj_tok = matched_majority(acc, {k: tok[k] for k in tok}, t_star_tok)
        t_star = min(ac_t, key=lambda t: abs(cost[f"ac@{t}"].mean() - c_star))
        return {"rule": rule, "cost": c_star, "tokens": t_star_tok, "acc": float(acc[rule].mean()),
                "majority_matched": float(maj.mean()), "diff_vs_majority": boot_mean(acc[rule] - maj),
                "majority_matched_tokens": float(maj_tok.mean()), "diff_vs_majority_tokens": boot_mean(acc[rule] - maj_tok),
                "ac_threshold": t_star, "ac_cost": float(cost[f"ac@{t_star}"].mean()),
                "ac_acc": float(acc[f"ac@{t_star}"].mean()), "diff_vs_ac": boot_mean(acc[rule] - acc[f"ac@{t_star}"])}

    report["primary"] = compare(f"cav-chain@16,8,{cav_best[(16, 8, 'chain')]}")
    report["secondary"] = {f"{src}:{n1},{m}": compare(f"cav-{src}@{n1},{m},{b}") for (n1, m, src), b in cav_best.items()}
    (out / "report.json").write_text(json.dumps(report, indent=1, default=float) + "\n")
    (out / "report.md").write_text(markdown(report))
    print(json.dumps(report["primary"], indent=1, default=float))


if __name__ == "__main__":
    main()
