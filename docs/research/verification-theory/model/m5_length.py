"""Part 5: why a good step-level error detector is at chance on long own traces.

(a) dilution: solution score = max over T step scores (Gumbel), one error step shifted by delta = log L.
    closed form AUROC_sol(T) = (T - 1 + L) / (2T - 1 + L);  error footprint m steps: (T - m + mL) / (2T - m + mL)
(b) liveness: errors get retracted ("wait, ...") in long traces; outcome = is an error still live at the end.
"""
import numpy as np
from m1_calibrate import auroc

rng = np.random.default_rng(0)
L = 4.0                                  # step-level AUROC 0.80  <=>  odds 4
delta = np.log(L)
n = 40_000

print("(a) dilution, step AUROC 0.80")
print("   T | closed form | simulated Gumbel-max | simulated Gaussian-max (same step AUROC)")
from scipy import stats
dg = np.sqrt(2) * stats.norm.ppf(0.8)
for T in [1, 3, 6, 12, 25, 50, 100, 200]:
    cf = (T - 1 + L) / (2 * T - 1 + L)
    g0 = rng.gumbel(size=(n, T)).max(1)
    g1 = rng.gumbel(size=(n, T)); g1[:, 0] += delta; g1 = g1.max(1)
    z0 = rng.standard_normal((n, T)).max(1)
    z1 = rng.standard_normal((n, T)); z1[:, 0] += dg; z1 = z1.max(1)
    lab = np.r_[np.ones(n, bool), np.zeros(n, bool)]
    print(f"  {T:3d} | {cf:.3f} | {auroc(np.r_[g1, g0], lab):.3f} | {auroc(np.r_[z1, z0], lab):.3f}")

print("\n(b) liveness chain: per step, error appears w.p. mu (if none live), is retracted w.p. r (if live)")
mu, r = 0.02, 0.05
Lr = 20.0                                # retraction cues ('wait', 'actually') are easy to spot
print("   T | P(wrong) | P(some error | right) | max-pool AUROC | max-pool AUROC, perfect detector | filter AUROC")
for T in [5, 10, 25, 50, 100, 200]:
    live = np.zeros(n, bool)
    intro = np.zeros((n, T), bool); retr = np.zeros((n, T), bool)
    for t in range(T):
        u = rng.random(n)
        intro[:, t] = (~live) & (u < mu)
        retr[:, t] = live & (u < r)
        live = (live | intro[:, t]) & ~retr[:, t]
    wrong = live
    e = rng.gumbel(size=(n, T)) + delta * intro          # error-step detector
    g = rng.gumbel(size=(n, T)) + np.log(Lr) * retr       # retraction detector
    # forward filter: P(live) with Gumbel location-shift likelihood ratios exp(x - shift) form
    le = np.exp(delta) * np.exp(-np.exp(-(e - delta))) / np.exp(-np.exp(-e))      # f1/f0 for error step
    lg = Lr * np.exp(-np.exp(-(g - np.log(Lr)))) / np.exp(-np.exp(-g))             # f1/f0 for retraction
    pl = np.zeros(n)
    for t in range(T):
        a_intro = (1 - pl) * mu * le[:, t]
        a_stay0 = (1 - pl) * (1 - mu)
        a_retr = pl * r * lg[:, t]
        a_stay1 = pl * (1 - r)
        pl = (a_intro + a_stay1) / (a_intro + a_stay0 + a_retr + a_stay1)
    ever = intro.any(1)
    print(f"  {T:3d} | {wrong.mean():.2f} | {ever[~wrong].mean():.2f} | {auroc(e.max(1), wrong):.3f} | "
          f"{auroc(ever.astype(float), wrong):.3f} | {auroc(pl, wrong):.3f}")

print("\n(c) the observed verbal-judge decay vs tokens (JUDGE model as judge): fit AUROC-0.5 = c * T^-alpha")
tok = np.array([482, 1902, 4662, 6317]); au = np.array([0.67, 0.63, 0.55, 0.58])
alpha, logc = np.polyfit(np.log(tok), np.log(au - 0.5), 1)
print(f"   alpha = {-alpha:.2f}  (max-pool dilution predicts alpha ~ 1; alpha < 1 means the error leaves a "
      f"footprint that grows with length, m ~ T^{1+alpha:.2f})")
