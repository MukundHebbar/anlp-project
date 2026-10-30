"""Part 12: robustness of the CAV gain (cost about 11, verdict probability, N1 = 16, m = 8) to model assumptions.

(a) attractor strength varies by question: rho_x ~ Beta(k mu, k (1 - mu)), mu refitted so majority@4 = 74.0
(b) the judge is weaker on hard questions: d(p) = d0 (0.25 + 0.75 p), d0 set so the pair-averaged within AUROC matches
(c) strongly shared judge errors inside an answer group (rho_s = 0.6)
"""
import numpy as np
from scipy import optimize, special, stats
from m1_calibrate import group_select
from m2_selection import judge
from m8_adaptive import cav

fits = np.load(__file__.replace("m12_robustness.py", "fits.npy"), allow_pickle=True).item()
a, b, rho0 = fits["test"]
Q = 60_000


def simulate_het(N, Q, rng, mu, kappa):
    p = rng.beta(a, b, Q)
    rx = rng.beta(kappa * mu, kappa * (1 - mu), Q) if kappa else np.full(Q, mu)
    Z = rng.random((Q, N)) < p[:, None]
    attr = (~Z) & (rng.random((Q, N)) < rx[:, None])
    return p, Z, attr


def maj(N, mu, kappa, seed=1):
    r = np.random.default_rng(seed)
    p, Z, attr = simulate_het(N, 200_000, r, mu, kappa)
    return group_select(Z, attr, np.ones(Z.shape), r).mean()


def pair_within_auroc(dvec, p):
    w = p * (1 - p)
    return np.sum(w * stats.norm.cdf(dvec / np.sqrt(2))) / w.sum()


def cav_gain(mu, kappa, d_of_p, rho_s):
    r = np.random.default_rng(5)
    p, Z, attr = simulate_het(16, Q, r, mu, kappa)
    dvec = d_of_p(p)[:, None]
    _, q = judge(p, Z, attr, 0.5, dvec, 0.6, r, V=0, rho_s=rho_s)
    best = max(cav(Z, attr, q, 4, 2, 8, bt, 0, np.random.default_rng(7))[:2] for bt in np.linspace(-0.5, 4, 10))
    r2 = np.random.default_rng(6)
    p2, Z2, at2 = simulate_het(11, Q, r2, mu, kappa)
    m11 = group_select(Z2, at2, np.ones(Z2.shape), r2).mean()
    return best[0], best[1], m11


p_ref = np.random.default_rng(0).beta(a, b, 200_000)
print("scenario                                   | CAV acc | avg cost | majority@11 | gain | majority limit")
for kappa in [0, 2.0]:
    mu = rho0 if kappa == 0 else optimize.brentq(lambda m: maj(4, m, kappa) - 0.740, 0.05, 0.95, xtol=1e-3)
    lim = maj(64, mu, kappa)
    for d_target in [0.5, 1.0]:
        A = stats.norm.cdf(d_target / np.sqrt(2))
        d0 = optimize.brentq(lambda x: pair_within_auroc(x * (0.25 + 0.75 * p_ref), p_ref) - A, 0.1, 5)
        for label, fn, rs in [(f"flat d={d_target}", lambda p, d=d_target: np.full_like(p, d), 0.3),
                              (f"d weaker on hard q (same pair AUROC {A:.2f})", lambda p, d0=d0: d0 * (0.25 + 0.75 * p), 0.3),
                              (f"flat d={d_target}, rho_s=0.6", lambda p, d=d_target: np.full_like(p, d), 0.6)]:
            acc, cost, m11 = cav_gain(mu, kappa, fn, rs)
            het = "constant rho" if kappa == 0 else f"rho_x ~ Beta, mean {mu:.2f}"
            print(f"  [{het}] {label:44s} | {100*acc:.1f} | {cost:4.1f} | {100*m11:.1f} | {100*(acc-m11):+.1f} | {100*lim:.1f}")
