#!/usr/bin/env python3
"""Does the step-level error feature also tell wrong ProcessBench solutions from correct ones (solution level)?"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from feature_check import auroc
D = Path(sys.argv[1])
out = {}
for src in ("pb-easy", "pb-hard"):
    z = np.load(D / f"{src}.npz"); its = json.load(open(D / f"{src}-items.json")); meta = z["meta"]
    for L, k in (("L18", 6596), ("L12", 6926)):
        f = z[L][:, k].astype(np.float32)
        per = {}
        for row, (i, j) in enumerate(meta):
            per.setdefault(int(i), []).append((int(j), float(f[row])))
        y = []; smax = []; smean = []; sfirst_err = []; s_before = []
        for i, v in per.items():
            v = [x for _, x in sorted(v)]
            lab = its[i]["label"]
            y.append(1 if lab >= 0 else 0); smax.append(max(v)); smean.append(float(np.mean(v)))
        out[f"{src} {L}:{k}"] = {"solution_auroc_max": round(auroc(smax, y), 4), "solution_auroc_mean": round(auroc(smean, y), 4),
                                 "n_wrong": int(sum(y)), "n_correct": int(len(y) - sum(y))}
        # within wrong solutions: is the max-feature step the labelled first error?
        hit = []; rand = []
        for i, v in per.items():
            lab = its[i]["label"]
            if lab < 0 or lab >= len(v):
                continue
            vv = [x for _, x in sorted(v)]
            hit.append(int(np.argmax(vv)) == lab); rand.append(1 / len(vv))
        out[f"{src} {L}:{k}"]["argmax_step_is_first_error"] = round(float(np.mean(hit)), 4)
        out[f"{src} {L}:{k}"]["chance"] = round(float(np.mean(rand)), 4)
print(json.dumps(out, indent=1))
