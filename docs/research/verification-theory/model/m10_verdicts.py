"""Part 10: why 1-2 verdicts per attempt beat 4, and a winner's-curse check on dev-based checkpoint choice.

Verdicts on the SAME attempt share the judge's latent error eta; only the Bernoulli sampling noise averages out.
So the within-question AUROC of q_V saturates at the latent's AUROC, while a new attempt adds a fresh vote and a
fresh eta.
"""
import numpy as np
from scipy import stats
from m1_calibrate import auroc

rng = np.random.default_rng(0)
n = 400_000
print("within-question AUROC of the verdict share q_V (latent u = c0 + d Z + eta, verdict ~ Bernoulli(Phi(u)))")
print("   d   c0 |  V=1  |  V=2  |  V=4  |  V=8  | latent (V=inf) | share of latent's gain captured by V=1 / 2 / 4")
for d in [0.5, 1.0]:
    for c0 in [0.0, 0.6, 1.5]:
        Z = rng.random(n) < 0.5
        u = c0 + d * Z + rng.standard_normal(n)
        pr = stats.norm.cdf(u)
        res = [auroc(rng.binomial(V, pr) / V, Z) for V in [1, 2, 4, 8]]
        lat = auroc(u, Z)
        share = [(x - 0.5) / (lat - 0.5) for x in res[:3]]
        print(f"  {d:.1f} {c0:4.1f} | " + " | ".join(f"{x:.3f}" for x in res) + f" | {lat:.3f} | "
              + " / ".join(f"{100*s:.0f}%" for s in share))

print("\nwinner's curse: pick the better of two checkpoints on a 200-question dev set (SE of a picking difference"
      " about 1.5 pts), true difference 0")
d = rng.normal(0, 1.5, (100_000, 2))
best = d.max(1)
print(f"  expected dev advantage of the chosen checkpoint: +{best.mean() - 0:.2f} pts over its true value"
      f" (Phase 2: +2.0 on dev, +1.2 on test)")

print("\nleniency check: one latent judge fitted to section 4 (single verdict flags 7.4% of wrong, 2.2% of right)")
z_h, z_f = stats.norm.ppf(0.074), stats.norm.ppf(0.022)
print(f"  SDT d' = z(H) - z(F) = {z_h - z_f:.2f}; binary-verdict AUROC = (1 + H - F)/2 = {(1 + 0.074 - 0.022)/2:.3f} "
      f"(Phase 2 reported 0.53)")
c0 = -z_h * np.sqrt(2)                 # flag prob for wrong = 1 - Phi(c0 / sqrt 2)
d = -z_f * np.sqrt(2) - c0             # flag prob for right = 1 - Phi((c0 + d) / sqrt 2)
Z = rng.random(n) < 0.674
u = c0 + d * Z + rng.standard_normal(n)
pr = stats.norm.cdf(u)
print(f"  implied latent judge: c0 = {c0:.2f}, d = {d:.2f}")
for V in [1, 4, 16]:
    print(f"    AUROC with {V:2d} sampled verdicts: {auroc(rng.binomial(V, pr) / V, Z):.3f}")
print(f"    AUROC of the latent score (verdict-token probability): {auroc(u, Z):.3f}")
print("  Phase 2 (section 13, same mixed judge, 4 verdicts, own test attempts): 0.568")

print("\ncriterion-shift hypothesis: keep the latent d = 0.80, move only the criterion c0 (4 verdicts)")
for c in [2.05, 1.5, 1.0, 0.5, 0.0, -0.5]:
    Z = rng.random(n) < 0.674
    u = c + d * Z + rng.standard_normal(n)
    q4 = rng.binomial(4, stats.norm.cdf(u)) / 4
    print(f"  c0 = {c:+.2f}: share of 'incorrect' verdicts {1 - q4.mean():.2f}, AUROC (4 verdicts) {auroc(q4, Z):.3f}")
print("  Phase 2 self-judge (4 verdicts, own test attempts): 0.665")

print("\nP-0c: distribution of the number of 'incorrect' verdicts among 4, implied latent judge (c0 = 2.05, d = 0.80)")
Z = rng.random(n) < 0.674
u = c0 + d * Z + rng.standard_normal(n)
k_inc = 4 - rng.binomial(4, stats.norm.cdf(u))
for lab, m in [("wrong attempts", ~Z), ("right attempts", Z)]:
    dist = np.bincount(k_inc[m], minlength=5) / m.sum()
    print(f"  {lab}: " + "  ".join(f"{k}:{100*v:.1f}%" for k, v in enumerate(dist)))
ind = 1 - np.mean(stats.norm.cdf(c0 / np.sqrt(2)))
print(f"  (if the 4 verdicts were independent at the same flag rate, P(4 of 4 'incorrect' | wrong) = {ind**4:.5f})")
