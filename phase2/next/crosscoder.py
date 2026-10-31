#!/usr/bin/env python3
"""Direction 4 pilot: model diffing with a crosscoder (untrained Qwen3.5-2B vs the mixed GRPO model).

1. acts: both models read ProcessBench solutions (GSM8K + MATH, 1,400) inside the JUDGE prompt; residual-stream
   activations of every solution-step token are saved for layers LAYERS. One model is loaded; "base" activations are
   taken with the LoRA adapter disabled, so both models see identical inputs.
2. train: one crosscoder per layer: a shared TopK sparse code over both models' activations, with a separate decoder
   per model. A latent whose decoder norm is mostly in the mixed model's decoder is a feature the training created
   or strengthened ("mixed-only"); mostly in the base decoder, one it removed ("base-only").
3. analyze: step-level latent activation (mean over the step's tokens). Positives: first wrong steps; negatives: steps
   of correct solutions and steps before the first error. Latents are ranked by AUROC on one half of the solutions
   and reported on the other half, per class (mixed-only / shared / base-only), against raw residual dimensions.

    python phase2/next/crosscoder.py all --out DIR --acts DIR_ON_SCRATCH --base <2B path> --pb-dir <ProcessBench dir>
"""

import argparse, hashlib, json, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "phase2" / "scripts"))

LAYERS = (12, 18)
SUBSETS = ("gsm8k", "math")
LATENTS, TOPK, EPOCHS, BATCH, LR = 8192, 32, 15, 4096, 2e-4


def items(pb_dir):
    out = []
    for sub in SUBSETS:
        for x in json.load(open(Path(pb_dir) / f"{sub}.json")):
            out.append({"uid": f"pb-{x['id']}", "subset": sub, "problem": x["problem"], "steps": x["steps"],
                        "label": x["label"]})
    return out


def acts(a):
    import torch
    from peft import PeftModel
    from transformers import AutoTokenizer, Qwen3_5ForConditionalGeneration
    import functional as F

    its = items(a.pb_dir)
    tok = AutoTokenizer.from_pretrained(a.base)
    model = Qwen3_5ForConditionalGeneration.from_pretrained(a.base, dtype=torch.bfloat16).to("cuda").eval()
    model = PeftModel.from_pretrained(model, str(Path(a.adapters) / "mixed-step75")).eval()
    store = {(m, L): [] for m in ("base", "mixed") for L in LAYERS}
    meta = []  # per saved token: item index, step index
    for i, it in enumerate(its):
        user = F.judge_prompt(it["problem"], it["steps"])
        text = tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
        enc = tok(text, return_offsets_mapping=True, return_tensors="pt")
        offs = enc.pop("offset_mapping")[0].tolist()
        spans, pos = [], 0
        for j, s in enumerate(it["steps"], 1):
            k = text.find(f"S{j}: {s}", pos)
            if k < 0:
                spans = None
                break
            spans.append((k, k + len(f"S{j}: {s}")))
            pos = k + 1
        if not spans:
            continue
        tok_step = [next((j for j, (s0, s1) in enumerate(spans) if s0 <= o0 < s1), -1) for o0, _ in offs]
        idx = [t for t, j in enumerate(tok_step) if j >= 0]
        if not idx:
            continue
        ids = enc["input_ids"].to("cuda")
        with torch.no_grad():
            hm = model(input_ids=ids, output_hidden_states=True).hidden_states
            with model.disable_adapter():
                hb = model(input_ids=ids, output_hidden_states=True).hidden_states
        for L in LAYERS:
            store[("mixed", L)].append(hm[L][0, idx].float().cpu().numpy().astype(np.float16))
            store[("base", L)].append(hb[L][0, idx].float().cpu().numpy().astype(np.float16))
        meta += [(i, tok_step[t]) for t in idx]
        if i % 200 == 0:
            print("acts", i, len(meta), flush=True)
    d = Path(a.acts); d.mkdir(parents=True, exist_ok=True)
    for (m, L), parts in store.items():
        np.save(d / f"{m}-L{L}.npy", np.concatenate(parts))
    np.save(d / "meta.npy", np.array(meta, dtype=np.int32))
    json.dump(its, open(d / "items.json", "w"))


class Crosscoder:
    def __init__(self, d, torch):
        t = torch
        self.t = t
        g = t.Generator(device="cuda").manual_seed(0)
        self.W_enc = (t.randn(2 * d, LATENTS, device="cuda", generator=g) / (2 * d) ** 0.5).requires_grad_()
        self.b_enc = t.zeros(LATENTS, device="cuda", requires_grad=True)
        def dec():  # independent random decoders for the two models (an identical start keeps them identical)
            w = t.randn(LATENTS, d, device="cuda", generator=g)
            return (w / w.norm(dim=1, keepdim=True) * 0.1).requires_grad_()
        self.W_b, self.W_m = dec(), dec()
        self.c_b = t.zeros(d, device="cuda", requires_grad=True); self.c_m = t.zeros(d, device="cuda", requires_grad=True)

    def params(self):
        return [self.W_enc, self.b_enc, self.W_b, self.W_m, self.c_b, self.c_m]

    def encode(self, xb, xm):
        pre = self.t.relu(self.t.cat([xb, xm], 1) @ self.W_enc + self.b_enc)
        v, i = pre.topk(TOPK, dim=1)
        return self.t.zeros_like(pre).scatter_(1, i, v)

    def loss(self, xb, xm):
        z = self.encode(xb, xm)
        rb, rm = z @ self.W_b + self.c_b, z @ self.W_m + self.c_m
        return ((rb - xb) ** 2).sum(1).mean() / (xb ** 2).sum(1).mean() + ((rm - xm) ** 2).sum(1).mean() / (xm ** 2).sum(1).mean()


class DiffSAE:
    """TopK sparse autoencoder on the activation difference (mixed - base)."""

    def __init__(self, d, torch):
        t = torch
        self.t = t
        g = t.Generator(device="cuda").manual_seed(1)
        self.W_e = (t.randn(d, LATENTS, device="cuda", generator=g) / d ** 0.5).requires_grad_()
        self.b_e = t.zeros(LATENTS, device="cuda", requires_grad=True)
        w = t.randn(LATENTS, d, device="cuda", generator=g)
        self.W_d = (w / w.norm(dim=1, keepdim=True)).requires_grad_()
        self.c = t.zeros(d, device="cuda", requires_grad=True)

    def params(self):
        return [self.W_e, self.b_e, self.W_d, self.c]

    def encode(self, x):
        pre = self.t.relu((x - self.c) @ self.W_e + self.b_e)
        v, i = pre.topk(TOPK, dim=1)
        return self.t.zeros_like(pre).scatter_(1, i, v)

    def loss(self, x):
        r = self.encode(x) @ self.W_d + self.c
        return ((r - x) ** 2).sum(1).mean() / (x ** 2).sum(1).mean()


def auroc_cols(scores, y):
    """Column-wise AUROC (ties averaged) for a [n, k] score matrix and binary labels y."""
    r = np.empty(scores.shape, dtype=np.float64)
    for c in range(scores.shape[1]):  # average ranks with ties, per column (no scipy in the environment)
        col = scores[:, c]
        order = np.argsort(col, kind="mergesort")
        sc = col[order]
        bounds = np.flatnonzero(np.r_[True, sc[1:] != sc[:-1], True])
        ranks = np.empty(len(col))
        for b0, b1 in zip(bounds[:-1], bounds[1:]):
            ranks[b0:b1] = (b0 + b1 + 1) / 2
        r[order, c] = ranks
    npos, nneg = y.sum(), (1 - y).sum()
    return (r[y == 1].sum(0) - npos * (npos + 1) / 2) / (npos * nneg)


def train_analyze(a):
    import torch
    d = Path(a.acts)
    its = json.load(open(d / "items.json"))
    meta = np.load(d / "meta.npy")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    # Step table: one row per (item, step) seen; label 1 = first wrong step, 0 = correct-solution step or before
    # the first error, -1 = after the first error (excluded).
    keys = sorted({(int(i), int(s)) for i, s in meta})
    row = {k: n for n, k in enumerate(keys)}
    lab = np.array([(1 if s == its[i]["label"] else (0 if its[i]["label"] < 0 or s < its[i]["label"] else -1))
                    for i, s in keys])
    half = np.array([int(hashlib.md5(its[i]["uid"].encode()).hexdigest(), 16) % 2 for i, _ in keys])
    tok_row = np.array([row[(int(i), int(s))] for i, s in meta])
    summary = {"tokens": int(len(meta)), "steps": len(keys), "first_error_steps": int((lab == 1).sum()),
               "negative_steps": int((lab == 0).sum()), "layers": {}}
    for L in LAYERS:
        xb_all = torch.from_numpy(np.load(d / f"base-L{L}.npy")).float()
        xm_all = torch.from_numpy(np.load(d / f"mixed-L{L}.npy")).float()
        sb, sm = xb_all.norm(dim=1).mean(), xm_all.norm(dim=1).mean()
        xb_all, xm_all = xb_all / sb * xb_all.shape[1] ** 0.5 / 10, xm_all / sm * xm_all.shape[1] ** 0.5 / 10
        cc = Crosscoder(xb_all.shape[1], torch)
        opt = torch.optim.Adam(cc.params(), lr=LR)
        n = len(xb_all)
        for ep in range(EPOCHS):
            perm = torch.randperm(n)
            tot = 0.0
            for s in range(0, n, BATCH):
                b = perm[s:s + BATCH]
                loss = cc.loss(xb_all[b].cuda(), xm_all[b].cuda())
                opt.zero_grad(); loss.backward(); opt.step()
                with torch.no_grad():  # unit-norm decoder rows (sum of both models' norms kept <= 2)
                    nrm = (cc.W_b.norm(dim=1) + cc.W_m.norm(dim=1)).clamp(min=1.0).unsqueeze(1) / 1.0
                    cc.W_b /= nrm; cc.W_m /= nrm
                tot += loss.item() * len(b)
            print(f"L{L} epoch {ep} loss {tot / n:.4f}", flush=True)
        # Step-level mean activations.
        steps_sum = torch.zeros(len(keys), LATENTS)
        cnt = torch.zeros(len(keys))
        raw_b = torch.zeros(len(keys), xb_all.shape[1]); raw_m = torch.zeros(len(keys), xm_all.shape[1])
        tr = torch.from_numpy(tok_row)
        with torch.no_grad():
            for s in range(0, n, BATCH):
                z = cc.encode(xb_all[s:s + BATCH].cuda(), xm_all[s:s + BATCH].cuda()).cpu()
                steps_sum.index_add_(0, tr[s:s + BATCH], z)
                raw_b.index_add_(0, tr[s:s + BATCH], xb_all[s:s + BATCH])
                raw_m.index_add_(0, tr[s:s + BATCH], xm_all[s:s + BATCH])
                cnt.index_add_(0, tr[s:s + BATCH], torch.ones(len(z)))
        feats = (steps_sum / cnt.unsqueeze(1)).numpy()
        rb_, rm_ = (raw_b / cnt.unsqueeze(1)).numpy(), (raw_m / cnt.unsqueeze(1)).numpy()
        nb, nm = cc.W_b.norm(dim=1).detach().cpu().numpy(), cc.W_m.norm(dim=1).detach().cpu().numpy()
        rel = nm / np.maximum(nb + nm, 1e-9)
        alive = (feats > 0).mean(0) > 0.001
        cls = np.where(rel > 0.9, "mixed-only", np.where(rel < 0.1, "base-only", np.where((rel > 0.3) & (rel < 0.7), "shared", "other")))
        res = {"mean_rel_norm": float(rel[alive].mean()), "alive": int(alive.sum()),
               "class_counts": {c: int(((cls == c) & alive).sum()) for c in ("mixed-only", "shared", "base-only", "other")}}

        def best(mat, mask):
            tr_, te_ = (lab >= 0) & (half == 0), (lab >= 0) & (half == 1)
            a_tr = auroc_cols(mat[tr_][:, mask], lab[tr_])
            a_tr = np.maximum(a_tr, 1 - a_tr)
            sign = np.where(auroc_cols(mat[tr_][:, mask], lab[tr_]) >= 0.5, 1, -1)
            top = np.argsort(-a_tr)[:5]
            a_te = auroc_cols(mat[te_][:, mask][:, top] * sign[top], lab[te_])
            ids = np.flatnonzero(mask)[top]
            return [{"index": int(i), "train_auroc": round(float(a_tr[t]), 3), "test_auroc": round(float(e), 3)}
                    for i, t, e in zip(ids, top, a_te)]
        for c in ("mixed-only", "shared", "base-only"):
            m = (cls == c) & alive
            if m.sum():
                res[f"top_{c}"] = best(feats, m)
        res["top_raw_base_dims"] = best(rb_, np.ones(rb_.shape[1], bool))
        res["top_raw_mixed_dims"] = best(rm_, np.ones(rm_.shape[1], bool))
        # Example steps for the best mixed-only latent.
        if "top_mixed-only" in res:
            li = res["top_mixed-only"][0]["index"]
            order = np.argsort(-feats[:, li])[:8]
            res["examples_best_mixed_only"] = [{"label": int(lab[o]), "act": round(float(feats[o, li]), 3),
                                                "step": its[keys[o][0]]["steps"][keys[o][1]][:300]} for o in order]
        # How different are the two models' activations at all, and what does a sparse code of the difference hold?
        diff = xm_all - xb_all
        res["relative_activation_difference"] = round(float((diff.norm(dim=1) / xb_all.norm(dim=1)).mean()), 4)
        sae = DiffSAE(diff.shape[1], torch)
        opt2 = torch.optim.Adam(sae.params(), lr=LR)
        dscale = diff.norm(dim=1).mean()
        for ep in range(EPOCHS):
            perm = torch.randperm(n); tot = 0.0
            for s in range(0, n, BATCH):
                b = perm[s:s + BATCH]
                loss = sae.loss(diff[b].cuda() / dscale)
                opt2.zero_grad(); loss.backward(); opt2.step()
                with torch.no_grad():
                    sae.W_d /= sae.W_d.norm(dim=1, keepdim=True).clamp(min=1.0)
                tot += loss.item() * len(b)
        res["diff_sae_fvu"] = round(tot / n, 4)
        dsum = torch.zeros(len(keys), LATENTS)
        with torch.no_grad():
            for s in range(0, n, BATCH):
                z = sae.encode(diff[s:s + BATCH].cuda() / dscale).cpu()
                dsum.index_add_(0, tr[s:s + BATCH], z)
        dfeats = (dsum / cnt.unsqueeze(1)).numpy()
        dalive = (dfeats > 0).mean(0) > 0.001
        res["diff_alive"] = int(dalive.sum())
        if dalive.sum():
            res["top_diff_latents"] = best(dfeats, dalive)
            li = res["top_diff_latents"][0]["index"]
            order = np.argsort(-dfeats[:, li])[:8]
            res["examples_best_diff_latent"] = [{"label": int(lab[o]), "act": round(float(dfeats[o, li]), 3),
                                                 "step": its[keys[o][0]]["steps"][keys[o][1]][:300]} for o in order]
        if "top_shared" in res:
            li = res["top_shared"][0]["index"]
            order = np.argsort(-feats[:, li])[:8]
            res["examples_best_shared"] = [{"label": int(lab[o]), "act": round(float(feats[o, li]), 3),
                                            "step": its[keys[o][0]]["steps"][keys[o][1]][:300]} for o in order]
        res["rel_norm_quantiles"] = [round(float(q), 3) for q in np.quantile(rel[alive], [0.01, 0.1, 0.5, 0.9, 0.99])]
        summary["layers"][f"L{L}"] = res
        torch.save({k: v.detach().cpu() for k, v in zip(("W_enc", "b_enc", "W_b", "W_m", "c_b", "c_m"), cc.params())},
                   d / f"crosscoder-L{L}.pt")
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["acts", "train", "all"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--acts", required=True)
    ap.add_argument("--base", default="")
    ap.add_argument("--pb-dir", default="")
    ap.add_argument("--adapters", default=str(Path.home() / "anlp-final-adapters"))
    a = ap.parse_args()
    if a.stage in ("acts", "all"):
        acts(a)
    if a.stage in ("train", "all"):
        train_analyze(a)
