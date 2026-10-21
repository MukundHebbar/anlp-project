#!/usr/bin/env python3
"""Analysis of the error-feature scores (CPU).

Latents are fixed in advance: the top 5 per layer by AUROC on half 0 of ProcessBench GSM8K + MATH (pb-easy), the
same selection as feature_check.py. Nothing is re-selected on the other sources.

1. pb-easy half 1 (pipeline check) and pb-hard (OlympiadBench, Omni-MATH): step-level AUROC, first wrong step vs clean.
2. Attempts (own-free, own-step, base-step, 9b-step, condensed): solution-level AUROC (wrong vs right answer) of the
   attempt's highest step score, against the verbal JUDGE's share of "incorrect" votes on the same attempts.
3. Selection among the 4 attempts per question: majority vote vs votes weighted by the feature score (2-fold
   cross-validated over questions), and combined with the verbal JUDGE.

    python phase2/next/errfeat_analyze.py --feats DIR --out DIR
"""

import argparse, collections, hashlib, json, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "phase2" / "scripts")); sys.path.insert(0, str(HERE))
from feature_check import auroc  # noqa: E402
import hint_pilot as hp  # noqa: E402

RUNS = REPO / "phase2" / "runs"


def load(feats, src):
    p = Path(feats) / f"{src}.npz"
    if not p.exists():
        return None
    z = np.load(p)
    return {"meta": z["meta"], "L12": z["L12"].astype(np.float32), "L18": z["L18"].astype(np.float32),
            "items": json.load(open(Path(feats) / f"{src}-items.json"))}


def step_labels(d):
    lab = np.array([(1 if s == d["items"][i]["label"] else (0 if d["items"][i]["label"] < 0 or s < d["items"][i]["label"]
                     else -1)) for i, s in d["meta"]])
    half = np.array([int(hashlib.md5(d["items"][i]["uid"].encode()).hexdigest(), 16) % 2 for i, _ in d["meta"]])
    sub = np.array([d["items"][i]["subset"] for i, _ in d["meta"]])
    return lab, half, sub


def verbal_scores(src):
    """Share of 'incorrect' JUDGE votes per attempt uid for the specialist and the mixed judge, where available."""
    files = {"own-step": sorted((RUNS / "stepformat").glob("judged-shard*.jsonl")),
             "base-step": [RUNS / "crossjudge" / "judged-base.jsonl"], "9b-step": [RUNS / "crossjudge" / "judged-9b.jsonl"],
             "condensed": [RUNS / "crossjudge" / "judged-condensed.jsonl"],
             "own-free": sorted((REPO / "runs-out" / "functional" / "drift").glob("critics-shard*.jsonl"))}.get(src, [])
    files = [f for f in files if f.exists()]
    out = {}
    for x in (hp.read_jsonl(files) if files else []):
        u = f"{x['uid']}#{x['attempt']}"
        r = {}
        for j in ("spec", "mixed"):
            if f"{j}_p_incorrect" in x:
                r[j] = x[f"{j}_p_incorrect"]
            elif f"{j}_judge" in x and "votes" in x[f"{j}_judge"]:
                v = x[f"{j}_judge"]["votes"]
                r[j] = sum(d == "incorrect" for d, _ in v) / max(1, len(v))
        out[u] = r
    return out


def same(a, b):
    import functional as F
    return F.same_answer(a, b)


def select(groups, w):
    """groups: question -> list of (attempt dict, weight); weighted vote over answer clusters."""
    acc = 0
    for xs in groups.values():
        cl = []
        for x, wt in xs:
            c = next((c for c in cl if same(c[0][0]["answer"], x["answer"])), None)
            c.append((x, wt)) if c else cl.append([(x, wt)])
        best = max(cl, key=lambda c: sum(wt for _, wt in c))
        acc += best[0][0]["correct"]
    return round(100 * acc / len(groups), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feats", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = {}
    easy = load(a.feats, "pb-easy")
    lab, half, _ = step_labels(easy)
    top = {}
    for L in ("L12", "L18"):
        tr = (lab >= 0) & (half == 0)
        aucs = np.array([auroc(easy[L][tr, k], lab[tr]) if easy[L][tr, k].any() else 0.5 for k in range(easy[L].shape[1])])
        aucs = np.nan_to_num(aucs, nan=0.5)
        order = np.argsort(-np.abs(aucs - 0.5))[:5]
        top[L] = [(int(k), 1 if aucs[k] >= 0.5 else -1) for k in order]
    res["latents"] = {L: [{"latent": k, "sign": s} for k, s in v] for L, v in top.items()}
    # 1. step level
    for src in ("pb-easy", "pb-hard"):
        d = easy if src == "pb-easy" else load(a.feats, src)
        if d is None:
            continue
        lab, half, sub = step_labels(d)
        m = (lab >= 0) & ((half == 1) if src == "pb-easy" else True)
        r = {}
        for L, lst in top.items():
            for k, s in lst:
                row = {"all": auroc(s * d[L][m, k], lab[m])}
                for sb in sorted(set(sub[m])):
                    mm = m & (sub == sb)
                    row[sb] = auroc(s * d[L][mm, k], lab[mm])
                r[f"{L}:{k}"] = {kk: (round(v, 4) if v is not None else None) for kk, v in row.items()}
        res[f"step_auroc_{src}"] = r
    # 2-3. attempts
    best = top["L18"][0]
    for src in ("own-free", "own-step", "base-step", "9b-step", "condensed"):
        d = load(a.feats, src)
        if d is None:
            continue
        L, (k, s) = "L18", best
        score = collections.defaultdict(list)
        for row, (i, j) in enumerate(d["meta"]):
            score[i].append(s * d[L][row, k])
        smax = {i: max(v) for i, v in score.items()}
        stop2 = {i: float(np.mean(sorted(v)[-2:])) for i, v in score.items()}
        its = d["items"]
        idx = sorted(smax)
        y = np.array([0 if its[i]["correct"] else 1 for i in idx])
        verbal = verbal_scores(src)
        r = {"attempts": len(idx), "accuracy": round(100 * (1 - y.mean()), 1),
             "feature_max_auroc": round(auroc([smax[i] for i in idx], y), 4),
             "feature_top2_auroc": round(auroc([stop2[i] for i in idx], y), 4)}
        for j in ("spec", "mixed"):
            v = [verbal.get(its[i]["uid"], {}).get(j) for i in idx]
            if all(x is not None for x in v):
                r[f"verbal_{j}_auroc"] = round(auroc(v, y), 4)
        # selection: questions with all 4 attempts
        q = collections.defaultdict(list)
        for i in idx:
            q[its[i]["question"]].append(i)
        q = {k_: v for k_, v in q.items() if len(v) >= 2}
        allv = np.array([smax[i] for i in idx]); lo, hi = np.percentile(allv, 5), np.percentile(allv, 95)
        norm = {i: float(np.clip((smax[i] - lo) / (hi - lo + 1e-9), 0, 1)) for i in idx}
        maj = select({k_: [(its[i], 1.0) for i in v] for k_, v in q.items()}, None)
        r["selection_majority"] = maj
        r["selection_oracle_pass@k"] = round(100 * np.mean([any(its[i]["correct"] for i in v) for v in q.values()]), 2)
        # weight = 1 - lam * norm; lam tuned on one half of the questions, scored on the other
        keys = sorted(q); halves = [keys[0::2], keys[1::2]]
        tot, chosen = 0.0, []
        for h in (0, 1):
            trq, teq = halves[h], halves[1 - h]
            best_lam = max([0.0, 0.25, 0.5, 0.75, 0.9, 1.0], key=lambda lam: select(
                {k_: [(its[i], 1 - lam * norm[i] + 1e-6) for i in q[k_]] for k_ in trq}, None))
            chosen.append(best_lam)
            tot += select({k_: [(its[i], 1 - best_lam * norm[i] + 1e-6) for i in q[k_]] for k_ in teq}, None) * len(teq)
        r["selection_feature_weighted_cv"] = round(tot / len(keys), 2)
        r["selection_lambdas"] = chosen
        r["selection_lowest_feature_attempt"] = round(100 * np.mean([its[min(v, key=lambda i: smax[i])]["correct"]
                                                                     for v in q.values()]), 2)
        res[f"attempts_{src}"] = r
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
