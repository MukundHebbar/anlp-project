#!/usr/bin/env python3
"""Confound check for the crosscoder error features (CPU only).

For the best shared latents of each layer (phase2/runs/crosscoder2/summary.json), recompute step-level activations
from the saved activations and crosscoder, then test on the held-out half of the solutions whether the latent still
separates first wrong steps from clean steps once step position, step length and final-answer steps are controlled.

    python phase2/next/feature_check.py --acts DIR --summary phase2/runs/crosscoder2/summary.json --out DIR
"""

import argparse, hashlib, json, re
from pathlib import Path

import numpy as np

TOPK = 32


def auroc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, int)
    if y.min() == y.max():
        return None
    order = np.argsort(s, kind="mergesort"); sc = s[order]
    b = np.flatnonzero(np.r_[True, sc[1:] != sc[:-1], True])
    r = np.empty(len(s))
    for b0, b1 in zip(b[:-1], b[1:]):
        r[order[b0:b1]] = (b0 + b1 + 1) / 2
    p = y.sum(); n = len(y) - p
    return float((r[y == 1].sum() - p * (p + 1) / 2) / (p * n))


def logreg(X, y, steps=3000, lr=0.1):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = np.c_[(X - mu) / sd, np.ones(len(X))]
    w = np.zeros(Z.shape[1])
    for _ in range(steps):
        p = 1 / (1 + np.exp(-Z @ w))
        w -= lr * Z.T @ (p - y) / len(y)
    return lambda Xn: np.c_[(Xn - mu) / sd, np.ones(len(Xn))] @ w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acts", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = Path(a.acts)
    its = json.load(open(d / "items.json"))
    meta = np.load(d / "meta.npy")
    keys = sorted({(int(i), int(s)) for i, s in meta})
    row = {k: n for n, k in enumerate(keys)}
    tok_row = np.array([row[(int(i), int(s))] for i, s in meta])
    lab = np.array([(1 if s == its[i]["label"] else (0 if its[i]["label"] < 0 or s < its[i]["label"] else -1))
                    for i, s in keys])
    half = np.array([int(hashlib.md5(its[i]["uid"].encode()).hexdigest(), 16) % 2 for i, _ in keys])
    nsteps = np.array([len(its[i]["steps"]) for i, _ in keys])
    idx = np.array([s for _, s in keys])
    text = [its[i]["steps"][s] for i, s in keys]
    length = np.array([len(t) for t in text])
    is_last = idx == nsteps - 1
    is_final = np.array([bool(re.search(r"boxed|final answer|the answer is", t, re.I)) for t in text])
    erroneous_sol = np.array([its[i]["label"] >= 0 for i, _ in keys])
    summ = json.load(open(a.summary))
    out = {"steps": len(keys), "first_error": int((lab == 1).sum()), "clean": int((lab == 0).sum()), "layers": {}}
    for L, res in summ["layers"].items():
        lat = [x["index"] for x in res["top_shared"][:3]]
        w = {k: v.numpy() if hasattr(v, "numpy") else v for k, v in __import__("torch").load(d / f"crosscoder-{L}.pt").items()}
        xb = np.load(d / f"base-{L}.npy").astype(np.float32); xm = np.load(d / f"mixed-{L}.npy").astype(np.float32)
        xb = xb / np.linalg.norm(xb, axis=1).mean() * xb.shape[1] ** 0.5 / 10
        xm = xm / np.linalg.norm(xm, axis=1).mean() * xm.shape[1] ** 0.5 / 10
        acc = np.zeros((len(keys), len(lat))); cnt = np.zeros(len(keys))
        for s in range(0, len(xb), 4096):
            pre = np.maximum(np.c_[xb[s:s + 4096], xm[s:s + 4096]] @ w["W_enc"] + w["b_enc"], 0)
            kth = np.partition(pre, -TOPK, axis=1)[:, -TOPK][:, None]
            z = np.where(pre[:, lat] >= kth, pre[:, lat], 0)
            np.add.at(acc, tok_row[s:s + 4096], z); np.add.at(cnt, tok_row[s:s + 4096], 1)
        feats = acc / cnt[:, None]
        te, tr = (lab >= 0) & (half == 1), (lab >= 0) & (half == 0)
        base_X = np.c_[idx, idx / np.maximum(nsteps - 1, 1), np.log1p(length), is_last, is_final]
        lres = []
        for j, li in enumerate(lat):
            f = feats[:, j]
            sign = 1 if auroc(f[tr], lab[tr]) >= 0.5 else -1
            fs = sign * f
            r = {"latent": li, "direction": "higher on first errors" if sign > 0 else "lower on first errors",
                 "test_auroc": auroc(fs[te], lab[te])}
            m = te & ~is_last & ~is_final
            r["test_auroc_excl_last_and_final_answer_steps"] = auroc(fs[m], lab[m])
            m = te & erroneous_sol
            r["test_auroc_within_wrong_solutions_first_error_vs_earlier"] = auroc(fs[m], lab[m])
            per = []
            for k in range(0, 8):  # stratified by step index
                m = te & (idx == k)
                v = auroc(fs[m], lab[m])
                if v is not None:
                    per.append((v, int(m.sum())))
            r["test_auroc_stratified_by_step_index"] = round(sum(v * n for v, n in per) / sum(n for _, n in per), 4)
            ctrl = logreg(base_X[tr], lab[tr]); both = logreg(np.c_[base_X[tr], fs[tr]], lab[tr])
            r["controls_only_test_auroc"] = auroc(ctrl(base_X[te]), lab[te])
            r["controls_plus_feature_test_auroc"] = auroc(both(np.c_[base_X[te], fs[te]]), lab[te])
            lres.append({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
        out["layers"][L] = {"position_only_test_auroc": round(auroc(idx[te], lab[te]), 4),
                            "relative_position_only_test_auroc": round(auroc((idx / np.maximum(nsteps - 1, 1))[te], lab[te]), 4),
                            "length_only_test_auroc": round(auroc(length[te], lab[te]), 4), "latents": lres}
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "summary.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
