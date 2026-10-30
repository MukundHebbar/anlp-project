"""Part 9: which training data teaches within-question discrimination?

Part 1 (closed form). Two cues seen in ONE attempt:
  difficulty-like cue  x_b = s_b * z_x + e_b      (z_x = standardised difficulty; e_b varies across attempts)
  within cue           x_w = d * Z + e_w
For a score th_b x_b + th_w x_w, within-question d' = d * th_w / sqrt(th_b^2 + th_w^2): ANY weight on x_b adds
within-question noise. Pointwise training under data where P(Z|x) varies puts th_b > 0; per-question balance gives th_b = 0.

Part 2 (finite sample). D-dimensional features with question-identity noise; 1,024 training examples from 900
questions; logistic regression; evaluated on fresh questions.
"""
import numpy as np
from scipy import optimize, special, stats
from m1_calibrate import simulate, auroc
from m2_selection import within_auroc

fits = np.load(__file__.replace("m9_training.py", "fits.npy"), allow_pickle=True).item()
a, b, rho = fits["test"]


def zscore_logit(p):
    z = special.logit(np.clip(p, 1e-4, 1 - 1e-4))
    return (z - (-0.3)) / 3.0     # fixed standardisation (population values of this Beta, approximately)


def fit_logistic(X, y, lam=1e-2):
    def f(w):
        s = X @ w
        return np.mean(np.logaddexp(0, s) - y * s) + lam * w @ w / 2, X.T @ (special.expit(s) - y) / len(y) + lam * w
    return optimize.minimize(f, np.zeros(X.shape[1]), jac=True, method="L-BFGS-B").x


# ---------------- Part 1: population optimum, two cues ----------------
print("Part 1: population logistic optimum with a difficulty-like cue (s_b) and a within cue (d = 1)")
print("  s_b | training data | weight on difficulty cue | weight on within cue | within AUROC")
r = np.random.default_rng(0)
p, Z, _ = simulate(a, b, rho, 4, 100_000, r)
zx = zscore_logit(p)
for s_b in [0.5, 1.0, 2.0]:
    xb = s_b * zx[:, None] + r.standard_normal(Z.shape)
    xw = 1.0 * Z + r.standard_normal(Z.shape)
    X = np.stack([xb.ravel(), xw.ravel(), np.ones(Z.size)], 1)
    y = Z.ravel().astype(float)
    k = Z.sum(1)
    regimes = {"natural": np.ones(Z.shape, bool)}
    wrong = ~Z
    keep_right = Z & (r.random(Z.shape) < wrong.sum() / Z.sum())
    regimes["globally balanced (Phase 2)"] = wrong | keep_right
    mixed = ((k > 0) & (k < 4))[:, None]
    # per-question balance: within mixed questions keep min(k, 4-k) of each class
    mk = np.minimum(k, 4 - k)[:, None]
    rank_r = np.cumsum(Z, 1); rank_w = np.cumsum(~Z, 1)
    regimes["per-question balanced"] = mixed & ((Z & (rank_r <= mk)) | (~Z & (rank_w <= mk)))
    for name, m in regimes.items():
        w = fit_logistic(X[m.ravel()], y[m.ravel()], lam=1e-4)
        dprime = 1.0 * w[1] / np.hypot(w[0], w[1])
        print(f"  {s_b:.1f} | {name:28s} | {w[0]:+.2f} | {w[1]:+.2f} | {stats.norm.cdf(dprime/np.sqrt(2)):.3f}")
print("  (within-only optimum: within AUROC = Phi(1/sqrt 2) = 0.760)")

# ---------------- Part 2: finite sample, high-dimensional ----------------
D, TAU, SB, DW, NTRAIN = 64, 1.0, 1.0, 1.0, 1024
rng = np.random.default_rng(1)
ub, uw, ul = np.eye(D)[0], np.eye(D)[1], np.eye(D)[2]


def features(p, Z, rng):
    Q, N = Z.shape
    zx = zscore_logit(p)
    qid = rng.standard_normal((Q, 1, D)) * TAU                           # question identity
    X = qid + SB * zx[:, None, None] * ub + DW * Z[..., None] * uw
    X += (1.0 * zx[:, None, None] + 0.3 * Z[..., None]) * ul              # length-like: mostly difficulty
    return X + rng.standard_normal((Q, N, D))


def make_pool(Q, N, rng):
    p, Z, attr = simulate(a, b, rho, N, Q, rng)
    return p, Z, features(p, Z, rng)


def sample_regime(name, rng):
    if name.endswith("N=16"):
        p, Z, X = make_pool(900, 16, rng)
    else:
        p, Z, X = make_pool(900, 4, rng)
    Q, N = Z.shape
    flatX, flatZ = X.reshape(-1, D), Z.ravel()
    if name == "natural":
        i = rng.choice(Q * N, NTRAIN, replace=False)
        return flatX[i], flatZ[i].astype(float), "point"
    if name == "globally balanced (Phase 2)":
        w, rt = np.flatnonzero(~flatZ), np.flatnonzero(flatZ)
        nw = min(len(w), NTRAIN // 2)
        i = np.r_[rng.choice(w, nw, replace=False), rng.choice(rt, NTRAIN - nw, replace=False)]
        return flatX[i], flatZ[i].astype(float), "point"
    # same-question (right, wrong) pairs
    pairs = []
    for q in range(Q):
        rr, ww = np.flatnonzero(Z[q]), np.flatnonzero(~Z[q])
        if len(rr) and len(ww):
            m = min(len(rr), len(ww))
            pairs += [(q, i, j) for i, j in zip(rng.permutation(rr)[:m], rng.permutation(ww)[:m])]
    pairs = np.array(pairs)
    if name.startswith("pairwise"):
        pairs = pairs[rng.permutation(len(pairs))[:NTRAIN // 2]]
        diff = X[pairs[:, 0], pairs[:, 1]] - X[pairs[:, 0], pairs[:, 2]]
        Xd = np.r_[diff, -diff]
        return Xd, np.r_[np.ones(len(diff)), np.zeros(len(diff))], f"pair ({len(diff)} pairs)"
    pairs = pairs[rng.permutation(len(pairs))[:NTRAIN // 2]]
    Xp = np.r_[X[pairs[:, 0], pairs[:, 1]], X[pairs[:, 0], pairs[:, 2]]]
    return Xp, np.r_[np.ones(len(pairs)), np.zeros(len(pairs))], f"point ({2*len(pairs)} examples)"


p_te, Z_te, X_te = make_pool(20_000, 4, np.random.default_rng(999))
regimes = ["natural", "globally balanced (Phase 2)", "per-question balanced N=4", "per-question balanced N=16",
           "pairwise N=16"]
print(f"\nPart 2: D={D}, question-identity sd {TAU}, {NTRAIN} training examples from 900 questions; "
      f"evaluated on 20,000 fresh questions x 4 (mean over 10 seeds)")
print("  regime                          | data used            | global AUROC | within AUROC")
for name in regimes:
    g, wv, used = [], [], ""
    for seed in range(10):
        Xtr, ytr, used = sample_regime(name, np.random.default_rng(seed))
        w = fit_logistic(np.c_[Xtr, np.ones(len(Xtr))], ytr, lam=1e-2)
        s = X_te @ w[:D]
        g.append(auroc(-s.ravel(), ~Z_te.ravel()))
        wv.append(within_auroc(-s, Z_te))
    print(f"  {name:31s} | {used:20s} | {np.mean(g):.3f} | {np.mean(wv):.3f} ± {np.std(wv)/np.sqrt(10):.3f}")
print(f"  within-only oracle (weights on the within direction only): within AUROC {stats.norm.cdf(DW/np.sqrt(2)):.3f}")
