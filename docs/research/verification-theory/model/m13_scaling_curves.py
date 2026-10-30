"""Part 13: model-predicted majority@N and pass@N (fits from Phase-2 N=4 aggregates only), for the paper's
predicted-vs-observed scaling figure. Writes model_curves.json."""
import json
import numpy as np
from m1_calibrate import simulate, group_select, beta_moment

fits = np.load(__file__.replace("m13_scaling_curves.py", "fits.npy"), allow_pickle=True).item()
out = {}
for split in ("dev", "test"):
    a, b, rho = fits[split]
    curves = {"N": [], "majority": [], "pass": []}
    for N in [1, 2, 4, 6, 8, 10, 12, 14, 16]:
        r = np.random.default_rng(N)
        p, Z, attr = simulate(a, b, rho, N, 200_000, r)
        curves["N"].append(N)
        curves["majority"].append(float(group_select(Z, attr, np.ones(Z.shape), r).mean()))
        curves["pass"].append(float(Z.any(1).mean()))
    curves["majority_limit"] = float(beta_moment(a, b, lambda p: (p > rho * (1 - p)).astype(float)))
    out[split] = curves
    print(split, {k: (np.round(v, 3).tolist() if isinstance(v, list) else round(v, 3)) for k, v in curves.items()})
open(__file__.replace("m13_scaling_curves.py", "model_curves.json"), "w").write(json.dumps(out, indent=1))
