"""Part 2: verifier = between-question (difficulty) signal + within-question signal.

latent u_i = c0 + gamma * z_x + d * Z_i + eta_i,  eta ~ N(0,1), shared with weight rho_s inside an answer group
judge says "correct" in each of V verdicts w.p. Phi(u_i);  q_i = share of "correct" verdicts
"""
import numpy as np
from scipy import special, stats
from m1_calibrate import simulate, group_select, auroc

fits = np.load(__file__.replace("m2_selection.py", "fits.npy"), allow_pickle=True).item()


def judge(p, Z, attr, gamma, d, c0, rng, V=4, rho_s=0.0):
    Q, N = Z.shape
    zx = special.logit(np.clip(p, 1e-4, 1 - 1e-4))
    zx = (zx - zx.mean()) / zx.std()
    eps = rng.standard_normal((Q, N))
    if rho_s > 0:  # error shared by attempts with the same answer (correct group / attractor group)
        sh_c, sh_a = rng.standard_normal(Q), rng.standard_normal(Q)
        shared = np.where(Z, sh_c[:, None], np.where(attr, sh_a[:, None], rng.standard_normal((Q, N))))
        eps = np.sqrt(rho_s) * shared + np.sqrt(1 - rho_s) * eps
    u = c0 + gamma * zx[:, None] + d * Z + eps
    prob = stats.norm.cdf(u)
    q = rng.binomial(V, prob) / V if V else prob
    return u, q


def within_auroc(score_wrong, Z):
    """Pair-weighted P(wrong attempt scored more suspicious than right attempt of the SAME question)."""
    Q, N = Z.shape
    num = den = 0.0
    for i in range(N):
        for j in range(N):
            m = (~Z[:, i]) & Z[:, j]
            num += ((score_wrong[m, i] > score_wrong[m, j]) + 0.5 * (score_wrong[m, i] == score_wrong[m, j])).sum()
            den += m.sum()
    return num / den


def bayes_select(Z, attr, q, beta, rng, V=4):
    lo = special.logit((q * V + 1) / (V + 2)) if V else special.logit(np.clip(q, 1e-6, 1 - 1e-6))
    return group_select(Z, attr, beta + lo, rng)


def tune_beta(a, b, rho, gamma, d, c0, V=4, N=4, rho_s=0.0):
    r = np.random.default_rng(99)
    p, Z, attr = simulate(a, b, rho, N, 100_000, r)
    u, q = judge(p, Z, attr, gamma, d, c0, r, V, rho_s)
    grid = np.linspace(0, 6, 25)
    accs = [bayes_select(Z, attr, q, bt, np.random.default_rng(5), V).mean() for bt in grid]
    return grid[int(np.argmax(accs))]


def run(a, b, rho, gamma, d, c0, N=4, V=4, Q=200_000, seed=3, rho_s=0.0, tune=True):
    r = np.random.default_rng(seed)
    p, Z, attr = simulate(a, b, rho, N, Q, r)
    u, q = judge(p, Z, attr, gamma, d, c0, r, V, rho_s)
    maj = group_select(Z, attr, np.ones(Z.shape), r).mean()
    qsum = group_select(Z, attr, q, r).mean()
    out = dict(maj=maj, qsum=qsum, oracle=Z.any(1).mean(),
               g_auc=auroc(1 - q.ravel(), ~Z.ravel()), w_auc=within_auroc(1 - q, Z))
    if tune:
        bt = tune_beta(a, b, rho, gamma, d, c0, V, N, rho_s)
        out["bayes"] = bayes_select(Z, attr, q, bt, r, V).mean()
        out["beta"] = bt
    return out


if __name__ == "__main__":
    a, b, rho = fits["test"]
    for c0 in [0.0, 0.6]:
        print(f"\n### c0 = {c0}  (test calibration; majority ~74.0, oracle ~82.8)")
        print(" gamma    d | global AUROC | within AUROC | q-sum pick (vs maj) | Bayes pick (vs maj)")
        for gamma in [0.0, 0.3, 0.6, 1.0]:
            for d in [0.0, 0.25, 0.5, 1.0, 2.0]:
                o = run(a, b, rho, gamma, d, c0, Q=100_000)
                print(f"  {gamma:.1f}  {d:4.2f} |    {o['g_auc']:.3f}     |    {o['w_auc']:.3f}     |"
                      f"  {100*o['qsum']:.1f} ({100*(o['qsum']-o['maj']):+.1f})     |"
                      f"  {100*o['bayes']:.1f} ({100*(o['bayes']-o['maj']):+.1f})  beta={o['beta']:.2f}")
