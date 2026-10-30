"""Part 1: calibrate a generative model of the solver to the Phase-2 numbers.

p_x ~ Beta(a, b)            per-question solve rate
k   ~ Binomial(N, p_x)      correct attempts (all share the true answer)
each wrong attempt gives the question's "attractor" wrong answer w.p. rho, else a unique wrong answer
"""
import numpy as np
from scipy import optimize, special, stats

rng = np.random.default_rng(0)


def beta_fit(mean, all_wrong4):
    def f(s):
        a, b = mean * s, (1 - mean) * s
        return np.prod([(b + j) / (a + b + j) for j in range(4)]) - all_wrong4
    s = optimize.brentq(f, 1e-3, 1e3)
    return mean * s, (1 - mean) * s


def beta_moment(a, b, fn, n=200_000):
    p = rng.beta(a, b, n)
    return fn(p).mean()


def simulate(a, b, rho, N, Q, rng):
    p = rng.beta(a, b, Q)
    Z = rng.random((Q, N)) < p[:, None]                       # correct?
    attr = (~Z) & (rng.random((Q, N)) < rho)                   # wrong + attractor
    return p, Z, attr


def group_select(Z, attr, w, rng):
    """Pick the answer group with the largest summed weight; random tie-break.
    Groups: 0 = correct answer, 1 = attractor wrong answer, 2+j = unique wrong answer of attempt j."""
    Q, N = Z.shape
    uniq = (~Z) & (~attr)
    g = np.full((Q, N + 2), -np.inf)
    g[:, 0] = np.where(Z.any(1), (w * Z).sum(1), -np.inf)
    g[:, 1] = np.where(attr.any(1), (w * attr).sum(1), -np.inf)
    g[:, 2:] = np.where(uniq, w, -np.inf)
    g = g + rng.random(g.shape) * 1e-9
    return g.argmax(1) == 0


def majority_acc(a, b, rho, N=4, Q=400_000, seed=1):
    r = np.random.default_rng(seed)
    p, Z, attr = simulate(a, b, rho, N, Q, r)
    return group_select(Z, attr, np.ones(Z.shape), r).mean()


def entropy2(p):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return -(p * np.log2(p) + (1 - p) * np.log2(1 - p))


def auroc(score, label):
    """P(score[label==1] > score[label==0]), ties half (Mann-Whitney)."""
    r = stats.rankdata(score)
    n1, n0 = label.sum(), (~label).sum()
    return (r[label].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def report(name, mean, pass4, maj):
    a, b = beta_fit(mean, 1 - pass4)
    rho = optimize.brentq(lambda r: majority_acc(a, b, r) - maj, 0.0, 1.0, xtol=1e-3)
    print(f"\n=== {name}: single {mean:.3f}, pass@4 {pass4:.3f}, majority {maj:.3f}")
    print(f"Beta(a={a:.3f}, b={b:.3f})  (a+b={a+b:.3f}; U-shaped if both < 1)   attractor rho={rho:.3f}")
    allright4 = beta_moment(a, b, lambda p: p**4)
    print(f"P(all 4 right)={allright4:.3f}  P(all 4 wrong)={1-pass4:.3f}  P(mixed)={pass4-allright4:.3f}")
    print(f"8 tries: always right {beta_moment(a,b,lambda p:p**8):.3f}, always wrong "
          f"{beta_moment(a,b,lambda p:(1-p)**8):.3f}  (training set, other questions: 0.39 / 0.11)")

    # information split: I(Z;X) vs E[H(p_x)] (upper bound on within-question information)
    HZ = entropy2(np.array(mean))
    EHp = beta_moment(a, b, entropy2)
    print(f"H(Z)={HZ:.3f} bits = I(Z;X) {HZ-EHp:.3f} (question difficulty) + E[H(p_x)] {EHp:.3f} "
          f"(max within-question info)  -> difficulty share {100*(HZ-EHp)/HZ:.0f}%")

    # simulate 400 x 4 like the test set many times: share of within-question pairs among AUROC pairs
    Q, N = 400, 4
    shares, wrong_from_allwrong, diff_auc = [], [], []
    for s in range(200):
        r = np.random.default_rng(100 + s)
        p, Z, attr = simulate(a, b, rho, N, Q, r)
        k = Z.sum(1)
        within = (k * (N - k)).sum()
        total = Z.sum() * (~Z).sum()
        shares.append(within / total)
        wrong_from_allwrong.append(((k == 0) * N).sum() / (~Z).sum())
        # AUROC of a pure difficulty oracle: score each attempt by its question's p_x
        diff_auc.append(auroc(np.repeat(p, N), Z.ravel()))
    print(f"Within-question share of the (right, wrong) pairs in global AUROC: {100*np.mean(shares):.3f}%"
          f"  (~{np.mean(shares)*mean*(1-mean)*1600**2:.0f} of ~{mean*(1-mean)*1600**2:.0f} pairs)")
    print(f"Wrong attempts that come from all-wrong questions: {100*np.mean(wrong_from_allwrong):.0f}%")
    print(f"Global AUROC of a difficulty-only score (s = p_x, zero within-question info): "
          f"{np.mean(diff_auc):.3f}")
    for noise in [0.5, 1.0, 2.0]:
        r = np.random.default_rng(7)
        p, Z, attr = simulate(a, b, rho, 4, 200_000, r)
        zx = special.logit(np.clip(p, 1e-4, 1 - 1e-4))
        zx = (zx - zx.mean()) / zx.std()
        sc = zx + noise * r.standard_normal(zx.shape)
        print(f"   noisy difficulty perception (noise sd {noise}): global AUROC {auroc(np.repeat(sc,4), Z.ravel()):.3f}")
    # resampling repair rates implied by the model
    r_fix = beta_moment(a, b, lambda p: p * (1 - p)) / (1 - mean)
    r_break = beta_moment(a, b, lambda p: p * (1 - p)) / mean
    print(f"Fresh resample of a wrong attempt is right: {r_fix:.3f}; of a right attempt is wrong: {r_break:.3f}")
    return a, b, rho


if __name__ == "__main__":
    fits = {}
    fits["test"] = report("TEST (400x4)", 0.674, 0.828, 0.740)
    fits["dev"] = report("DEV (200x4)", 0.698, 0.865, 0.775)
    np.save(__file__.replace("m1_calibrate.py", "fits.npy"), fits, allow_pickle=True)
