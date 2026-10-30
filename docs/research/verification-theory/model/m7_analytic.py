"""Part 7: closed forms for the N = 4 gain, and where the headroom lives by difficulty.

Judge with continuous within-question scores: right ~ N(d, 1), wrong ~ N(0, 1), independent (rho_s = 0).
Lexicographic rule (majority; judge breaks ties by group mean):
  gain = P(1,1,2)+P(1,0,3) times (M4(d) - 1/4)  +  P(2,2,0) times (Phi(d) - 1/2)
  M4(d) = P(right singleton has the top score of 4) = int phi(x - d) Phi(x)^3 dx
Bayes rule, right group size k vs wrong group size m (vote weight beta, LLR = d s - d^2/2):
  P(pick right) = Phi( [(k - m) beta + (k + m) d^2 / 2] / (sqrt(k + m) d) )
"""
import numpy as np
from scipy import integrate, stats
from m1_calibrate import simulate, group_select, beta_moment

fits = np.load(__file__.replace("m7_analytic.py", "fits.npy"), allow_pickle=True).item()
a, b, rho = fits["test"]


def M(t, d):
    return integrate.quad(lambda x: stats.norm.pdf(x - d) * stats.norm.cdf(x) ** (t - 1), -10, 10)[0]


def config_probs(Q=400_000):
    r = np.random.default_rng(11)
    p, Z, attr = simulate(a, b, rho, 4, Q, r)
    k, m = Z.sum(1), attr.sum(1)
    u = 4 - k - m
    return {c: np.mean((k == c[0]) & (m == c[1]) & (u == c[2])) for c in [(1, 1, 2), (1, 0, 3), (2, 2, 0), (1, 2, 1), (1, 3, 0)]}


P = config_probs()
print("closed-form tie-breaking gain vs simulation (continuous scores, rho_s = 0)")
print("   d | A_within | M4(d) | closed form (pts) | simulated lexicographic (pts)")
for d in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
    m4 = M(4, d)
    cf = (P[(1, 1, 2)] + P[(1, 0, 3)]) * (m4 - 0.25) + P[(2, 2, 0)] * (stats.norm.cdf(d) - 0.5)
    r = np.random.default_rng(3)
    p, Z, attr = simulate(a, b, rho, 4, 300_000, r)
    s = d * Z + r.standard_normal(Z.shape)
    maj = group_select(Z, attr, np.ones(Z.shape), r).mean()
    # lexicographic with group MEAN as tie-break (sizes are equal inside a tie)
    lex = group_select(Z, attr, 1.0 + 1e-4 * stats.norm.cdf(s), r).mean()
    print(f"  {d:4.2f} | {stats.norm.cdf(d/np.sqrt(2)):.3f} | {m4:.3f} | {100*cf:5.2f} | {100*(lex-maj):5.2f}")

print("\nBayes overturn probability, right group k vs wrong plurality m (beta = vote weight)")
for k, m in [(1, 2), (1, 3)]:
    for beta in [0.5, 1.0, 2.0]:
        row = [f"{stats.norm.cdf(((k-m)*beta + (k+m)*d*d/2)/(np.sqrt(k+m)*d)):.2f}" for d in [0.5, 1.0, 1.5, 2.0]]
        print(f"  k={k} m={m} beta={beta}: P(overturn) at d=0.5/1/1.5/2 = {' / '.join(row)}")

print("\nwhere things live, by question solve rate p (test calibration, N = 4)")
r = np.random.default_rng(5)
p, Z, attr = simulate(a, b, rho, 4, 1_000_000, r)
maj = group_select(Z, attr, np.ones(Z.shape), r)
head = Z.any(1) & ~maj
k = Z.sum(1)
pairs = k * (4 - k)
edges = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0]
print("   p bin    | questions | share of within pairs | share of headroom")
for lo, hi in zip(edges[:-1], edges[1:]):
    m = (p >= lo) & (p < hi)
    print(f"  {lo:.1f}-{hi:.1f}  |  {100*m.mean():5.1f}%  |  {100*pairs[m].sum()/pairs.sum():5.1f}%  |  {100*head[m].sum()/head.sum():5.1f}%")
w_pairs = pairs / pairs.sum()
w_head = head / head.sum()
print(f"mean p: over within pairs {np.sum(w_pairs*p):.2f}, over headroom {np.sum(w_head*p):.2f}")

print("\nif the judge is weaker on harder questions, d(p) = d0 * (0.25 + 0.75 p):")
for d0 in [1.0, 2.0]:
    dp = d0 * (0.25 + 0.75 * p)
    a_pairs = np.sum(w_pairs * stats.norm.cdf(dp / np.sqrt(2)))
    a_head = np.sum(w_head * stats.norm.cdf(dp / np.sqrt(2)))
    print(f"  d0={d0}: within AUROC averaged over pairs {a_pairs:.3f}; over the headroom questions {a_head:.3f}")
