"""Part 3: where the 8.8-point headroom lives; tie-breaking vs overturning; scaling in N; compute matching."""
import numpy as np
from collections import Counter
from scipy import special
from m1_calibrate import simulate, group_select
from m2_selection import judge, run, within_auroc, bayes_select

fits = np.load(__file__.replace("m3_structure.py", "fits.npy"), allow_pickle=True).item()
a, b, rho = fits["test"]


def configs(N=4, Q=400_000):
    r = np.random.default_rng(11)
    p, Z, attr = simulate(a, b, rho, N, Q, r)
    k, m = Z.sum(1), attr.sum(1)
    u = N - k - m
    maj = group_select(Z, attr, np.ones(Z.shape), r)
    tab = Counter()
    hit = Counter()
    for kk, mm, uu, ok in zip(k, m, u, maj):
        tab[(kk, mm, uu)] += 1
        hit[(kk, mm, uu)] += ok
    print("config (right, attractor-wrong, unique-wrong) | share | majority right | headroom pts | type")
    tie = over = 0.0
    for c in sorted(tab, key=lambda c: -tab[c]):
        sh = tab[c] / Q
        acc = hit[c] / tab[c]
        head = sh * (1 - acc) * 100 if c[0] > 0 else 0.0
        kk, mm, uu = c
        top_wrong = max(mm, 1 if uu else 0)
        kind = ("unwinnable" if kk == 0 else "majority already right" if kk > top_wrong
                else "TIE (break it)" if kk == top_wrong else "OVERTURN plurality")
        if kind.startswith("TIE"): tie += head
        if kind.startswith("OVER"): over += head
        if sh > 0.002:
            print(f"  {c} | {100*sh:5.1f}% | {acc:5.2f} | {head:4.2f} | {kind}")
    print(f"headroom from ties {tie:.2f} pts, from overturning {over:.2f} pts (total {tie+over:.2f})")


def lexicographic(Z, attr, q, rng):
    """Majority vote; verifier only breaks ties (sum of q inside tied groups)."""
    return group_select(Z, attr, 1.0 + 1e-3 * q, rng)


def scaling(d, c0, rho_s, gamma=0.5, Ns=(1, 2, 4, 8, 16, 32, 64), Q=60_000):
    print(f"\n-- within d={d}, c0={c0}, within-group error correlation rho_s={rho_s}")
    print("   N | oracle | majority | best-of-N (argmax) | q-sum | Bayes (tuned) | lexicographic")
    for N in Ns:
        r = np.random.default_rng(N)
        p, Z, attr = simulate(a, b, rho, N, Q, r)
        u, q = judge(p, Z, attr, gamma, d, c0, r, V=4, rho_s=rho_s)
        maj = group_select(Z, attr, np.ones(Z.shape), r).mean()
        qs = group_select(Z, attr, q, r).mean()
        top = np.argmax(q + r.random(q.shape) * 1e-9, 1)
        bon = Z[np.arange(Q), top].mean()
        best = max(bayes_select(Z, attr, q, bt, np.random.default_rng(1)).mean() for bt in np.linspace(0, 6, 13))
        lex = lexicographic(Z, attr, q, r).mean()
        print(f"  {N:2d} | {100*Z.any(1).mean():5.1f} | {100*maj:5.1f} | {100*bon:5.1f} | {100*qs:5.1f} | "
              f"{100*best:5.1f} | {100*lex:5.1f}")


if __name__ == "__main__":
    configs()
    print("\n### lenient judges (real judges flag 2-7% of own attempts): c0 sweep at gamma=0.5")
    print("  c0    d | share 'correct' verdicts | within AUROC | q-sum vs maj | lexicographic vs maj")
    for c0 in [0.6, 1.2, 1.8]:
        for d in [0.0, 0.5, 1.0]:
            r = np.random.default_rng(4)
            p, Z, attr = simulate(a, b, rho, 4, 100_000, r)
            u, q = judge(p, Z, attr, 0.5, d, c0, r)
            maj = group_select(Z, attr, np.ones(Z.shape), r).mean()
            qs = group_select(Z, attr, q, r).mean()
            lex = lexicographic(Z, attr, q, r).mean()
            print(f"  {c0:.1f} {d:4.1f} | {q.mean():.2f} | {within_auroc(1-q, Z):.3f} | {100*(qs-maj):+.1f} | {100*(lex-maj):+.1f}")
    for d, rho_s in [(0.5, 0.0), (1.0, 0.0), (1.0, 0.5), (2.0, 0.5)]:
        scaling(d, 0.6, rho_s)
