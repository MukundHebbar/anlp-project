"""Part 11: (a) decompose the benchmark-vs-own-attempt gap of the verbal judge from Phase-2 numbers;
(b) power of a Stage-1 CAV evaluation.

(a) AUROC is linear in a mixture of the positive class: if a share lam of wrong attempts carry a locatable step
error (judged with AUROC A_loc, as on ProcessBench) and the rest are judged at chance against right attempts, then
AUROC_own = lam * A_loc + (1 - lam) * 0.5.
"""
import numpy as np
from scipy import stats
from m1_calibrate import simulate, group_select
from m2_selection import judge
from m8_adaptive import cav

print("(a) verbal-judge gap, JUDGE model as judge (Phase-2 sections 8 and 10)")
A_pb = {"JUDGE model": stats.norm.cdf(2.50 / np.sqrt(2)), "mixed": stats.norm.cdf(2.63 / np.sqrt(2))}
own = {"JUDGE model": {"own, step format (6.3k tok)": 0.58, "condensed by 9B (0.5k tok)": 0.67},
       "mixed": {"own, step format (6.3k tok)": 0.54, "condensed by 9B (0.5k tok)": 0.59}}
for j in A_pb:
    print(f"  {j}: ProcessBench solution-level AUROC from d' = {A_pb[j]:.3f}")
    for k, v in own[j].items():
        lam = (v - 0.5) / (A_pb[j] - 0.5)
        print(f"     {k}: AUROC {v:.2f} -> implied share of wrong attempts with a ProcessBench-like error: {lam:.2f}")

print("\n(b) Stage-1 power: CAV (logprob, N1=16, m=8) vs majority at equal average cost (~11)")
fits = np.load(__file__.replace("m11_gap_power.py", "fits.npy"), allow_pickle=True).item()
a, b, rho = fits["test"]
for d, beta in [(0.5, 1.0), (1.0, 0.0)]:
    r = np.random.default_rng(3)
    Q = 100_000
    p, Z, attr = simulate(a, b, rho, 16, Q, r)
    _, q = judge(p, Z, attr, 0.5, d, 0.6, r, V=0, rho_s=0.3)
    # per-question outcomes: CAV vs majority over the first 11 attempts (same pool, paired)
    from m8_adaptive import groups
    from scipy import special
    rr = np.random.default_rng(7)
    first = groups(Z[:, :4], attr[:, :4])
    una = (first.sum(2) == 4).any(1)
    acc_c, cost, _ = cav(Z, attr, q, 4, 2, 8, beta, 0, rr)
    # recompute per-question CAV correctness (cav returns means), via a light re-implementation
    mem = groups(Z, attr)
    size = mem.sum(2).astype(float)
    order = np.argsort(-(size + rr.random(size.shape) * 1e-3), axis=1)[:, :2]
    top = np.take_along_axis(mem, order[:, :, None], 1)
    judged = top & (np.cumsum(top, 2) <= 8)
    lo = special.logit(np.clip(q, 1e-4, 1 - 1e-4))
    ev = (judged * lo[:, None, :]).sum(2) / np.maximum(judged.sum(2), 1)
    ts = np.take_along_axis(size, order, 1)
    pick = np.take_along_axis(order, np.where(ts > 0, ts * (beta + ev), -np.inf).argmax(1)[:, None], 1)[:, 0]
    maj4 = group_select(Z[:, :4], attr[:, :4], np.ones((Q, 4)), rr)
    cav_ok = np.where(una, maj4, pick == 0)
    maj11 = group_select(Z[:, :11], attr[:, :11], np.ones((Q, 11)), rr)
    diff = cav_ok.astype(float) - maj11
    disc = (diff != 0).mean()
    eff = diff.mean()
    n80 = (1.96 + 0.84) ** 2 * diff.var() / eff ** 2
    print(f"  within d={d}: CAV {100*cav_ok.mean():.1f} (avg cost {cost:.1f}) vs majority@11 {100*maj11.mean():.1f}: "
          f"gain {100*eff:+.1f}, discordant {100*disc:.1f}% -> questions for 80% power: {n80:.0f}")
