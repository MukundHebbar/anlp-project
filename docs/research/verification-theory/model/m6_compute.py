"""Part 6: compute-matched frontier. One attempt = 1 unit; one judge verdict ~ 0.3 units
(about 1.45k decoded tokens vs about 5k for an attempt; prefill ignored)."""
import numpy as np
from m1_calibrate import simulate, group_select
from m2_selection import judge, bayes_select

fits = np.load(__file__.replace("m6_compute.py", "fits.npy"), allow_pickle=True).item()
a, b, rho = fits["test"]
COST_V = 0.3


def best_bayes(Z, attr, q, V):
    return max(bayes_select(Z, attr, q, bt, np.random.default_rng(1), V).mean() for bt in np.linspace(-1, 6, 15))


print("budget | majority | best verified (N attempts, V verdicts each) for within d=0.5 (AUROC~0.6) | d=1.0 (~0.7) | d=1.5 (~0.78)")
for B in [4, 8, 16, 32, 64]:
    r = np.random.default_rng(B)
    p, Z, attr = simulate(a, b, rho, B, 40_000, r)
    maj = group_select(Z, attr, np.ones(Z.shape), r).mean()
    row = [f"{B:3d} | {100*maj:5.1f}"]
    for d in [0.5, 1.0, 1.5]:
        best = (maj, B, 0)
        for V in [1, 2, 4]:
            N = int(B // (1 + COST_V * V))
            if N < 2:
                continue
            r2 = np.random.default_rng(100 + B)
            p2, Z2, at2 = simulate(a, b, rho, N, 40_000, r2)
            _, q = judge(p2, Z2, at2, 0.5, d, 0.6, r2, V=V, rho_s=0.3)
            acc = best_bayes(Z2, at2, q, V)
            if acc > best[0]:
                best = (acc, N, V)
        row.append(f"{100*best[0]:5.1f} (N={best[1]}, V={best[2]})")
    print(" | ".join(row))
