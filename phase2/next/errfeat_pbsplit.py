#!/usr/bin/env python3
"""Where does the error feature work on ProcessBench? Solution-level AUROC (mean step score) split by the model that
wrote the solution, and by whether the final answer is right (process error with a right vs wrong final answer)."""
import json, sys, collections
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from feature_check import auroc
D, PB = Path(sys.argv[1]), Path(sys.argv[2])
info = {}
for sub in ("gsm8k", "math", "olympiadbench", "omnimath"):
    for x in json.load(open(PB / f"{sub}.json")):
        info[f"pb-{x['id']}"] = (x["generator"], x["final_answer_correct"])
res = {}
for L, k in (("L18", 6596),):
    score, lab, gen, fac = [], [], [], []
    for src in ("pb-easy", "pb-hard"):
        z = np.load(D / f"{src}.npz"); its = json.load(open(D / f"{src}-items.json"))
        f = z[L][:, k].astype(np.float32); per = collections.defaultdict(list)
        for row, (i, j) in enumerate(z["meta"]):
            per[int(i)].append(float(f[row]))
        for i, v in per.items():
            u = its[i]["uid"]
            score.append(np.mean(v)); lab.append(1 if its[i]["label"] >= 0 else 0)
            gen.append(info[u][0]); fac.append(info[u][1])
    score, lab, gen, fac = map(np.array, (score, lab, gen, fac))
    by = {}
    for g in sorted(set(gen)):
        m = gen == g
        if lab[m].min() != lab[m].max():
            by[g] = {"n": int(m.sum()), "auroc": round(auroc(score[m], lab[m]), 3)}
    res["by_generator"] = by
    neg = lab == 0
    res["process_error_wrong_final_vs_correct"] = round(auroc(np.r_[score[(lab == 1) & ~fac], score[neg]],
                                                              np.r_[np.ones(((lab == 1) & ~fac).sum()), np.zeros(neg.sum())]), 3)
    res["process_error_right_final_vs_correct"] = round(auroc(np.r_[score[(lab == 1) & fac], score[neg]],
                                                              np.r_[np.ones(((lab == 1) & fac).sum()), np.zeros(neg.sum())]), 3)
    res["n_process_error_right_final"] = int(((lab == 1) & fac).sum())
print(json.dumps(res, indent=1))

# Same solution-level and step-level scores on the synthetic JUDGE test set, if scored.
if (D / "synthetic.npz").exists():
    z = np.load(D / "synthetic.npz"); its = json.load(open(D / "synthetic-items.json"))
    f = z["L18"][:, 6596].astype(np.float32); per = collections.defaultdict(list)
    for row, (i, j) in enumerate(z["meta"]):
        per[int(i)].append((int(j), float(f[row])))
    y = [1 if its[i]["label"] >= 0 else 0 for i in per]; sm = [np.mean([x for _, x in v]) for v in per.values()]
    lab = []; sc = []
    for i, v in per.items():
        L_ = its[i]["label"]
        for j, x in v:
            if L_ < 0 or j <= L_:
                lab.append(1 if j == L_ else 0); sc.append(x)
    print(json.dumps({"synthetic_solution_auroc_mean": round(auroc(sm, y), 3),
                      "synthetic_step_auroc": round(auroc(sc, lab), 3)}, indent=1))
