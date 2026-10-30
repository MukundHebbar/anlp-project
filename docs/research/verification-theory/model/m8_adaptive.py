"""Part 8: contest-adaptive verification (CAV).

1. sample n0 = 4 attempts; if all four give the same answer, stop
2. otherwise sample up to N1 attempts in total
3. judge only the attempts of the top-K answer groups by size (at most m per group, V verdicts each)
   (V = 0 means one judge pass scored by the verdict-token probability instead of sampled verdicts)
4. pick the group maximising  n_g * (beta + mean logit q~)   (Bayes with a vote prior, evidence extrapolated)
Cost: attempt = 1 unit, verdict = 0.3 units. Compared at equal AVERAGE cost per question.
"""
import numpy as np
from scipy import special
from m1_calibrate import simulate, group_select
from m2_selection import judge

fits = np.load(__file__.replace("m8_adaptive.py", "fits.npy"), allow_pickle=True).item()
a, b, rho = fits["test"]
COST_V = 0.3
Q = 60_000


def groups(Z, attr):
    """Group membership matrix: (Q, G, N) with G = N + 2 (right, attractor, one per unique wrong attempt)."""
    Qn, N = Z.shape
    uniq = (~Z) & (~attr)
    mem = np.zeros((Qn, N + 2, N), bool)
    mem[:, 0, :] = Z
    mem[:, 1, :] = attr
    idx = np.arange(N)
    mem[:, 2 + idx, idx] = uniq
    return mem


def cav(Z, attr, q, n0, K, mcap, beta, V, rng):
    Qn, N = Z.shape
    first = groups(Z[:, :n0], attr[:, :n0])
    unanimous = (first.sum(2) == n0).any(1)
    mem = groups(Z, attr)
    size = mem.sum(2).astype(float)
    order = np.argsort(-(size + rng.random(size.shape) * 1e-3), axis=1)[:, :K]       # top-K groups
    top = np.take_along_axis(mem, order[:, :, None], 1)                              # (Q, K, N)
    # judge at most mcap members per group (the first ones)
    judged = top & (np.cumsum(top, 2) <= mcap)
    lo = special.logit((q * V + 1) / (V + 2)) if V else special.logit(np.clip(q, 1e-4, 1 - 1e-4))
    ev = (judged * lo[:, None, :]).sum(2) / np.maximum(judged.sum(2), 1)
    tsize = np.take_along_axis(size, order, 1)
    score = np.where(tsize > 0, tsize * (beta + ev), -np.inf)
    pick = np.take_along_axis(order, score.argmax(1)[:, None], 1)[:, 0]
    maj_first = group_select(Z[:, :n0], attr[:, :n0], np.ones((Qn, n0)), rng)
    right = np.where(unanimous, maj_first, pick == 0)
    cost = np.where(unanimous, n0, N + COST_V * max(V, 1) * judged.sum((1, 2)))
    return right.mean(), cost.mean(), unanimous.mean()


def adaptive_majority(Z, attr, n0, rng):
    Qn, N = Z.shape
    first = groups(Z[:, :n0], attr[:, :n0])
    unanimous = (first.sum(2) == n0).any(1)
    maj = group_select(Z, attr, np.ones(Z.shape), rng)
    right = np.where(unanimous, group_select(Z[:, :n0], attr[:, :n0], np.ones((Qn, n0)), rng), maj)
    return right.mean(), np.where(unanimous, n0, N).mean()


if __name__ == "__main__":
    print("non-adaptive majority (cost = N):")
    maj_curve = {}
    for N in [4, 6, 8, 12, 16, 24, 32, 64]:
        r = np.random.default_rng(N)
        p, Z, attr = simulate(a, b, rho, N, Q, r)
        maj_curve[N] = group_select(Z, attr, np.ones(Z.shape), r).mean()
        print(f"  N={N:2d}: {100*maj_curve[N]:.1f}")

    print("\nadaptive majority (stop if the first 4 agree):")
    for N1 in [8, 16, 32, 64]:
        r = np.random.default_rng(10 + N1)
        p, Z, attr = simulate(a, b, rho, N1, Q, r)
        acc, cost = adaptive_majority(Z, attr, 4, r)
        print(f"  N1={N1:2d}: acc {100*acc:.1f} at average cost {cost:.1f}")

    for d in [0.5, 1.0]:
        print(f"\nCAV (c0 = 0.6; V = 0 rows read the verdict-token probability), within d={d} (A_within ~{0.638 if d==0.5 else 0.760:.2f} continuous), rho_s=0.3, K=2:")
        print("  N1  V  m | unanimous | average cost | accuracy | best beta")
        for N1 in [8, 16, 32]:
            for V, mcap in [(1, 2), (1, 4), (2, 4), (1, 8), (0, 4), (0, 8)]:
                r = np.random.default_rng(100 + N1)
                p, Z, attr = simulate(a, b, rho, N1, Q, r)
                _, qv = judge(p, Z, attr, 0.5, d, 0.6, r, V=V, rho_s=0.3)
                best = max(((cav(Z, attr, qv, 4, 2, mcap, bt, V, np.random.default_rng(7)), bt)
                            for bt in np.linspace(-0.5, 4, 10)), key=lambda t: t[0][0])
                (acc, cost, una), bt = best
                print(f"  {N1:2d}  {V}  {mcap} | {100*una:.0f}% | {cost:5.1f} | {100*acc:.1f} | {bt:.1f}")
