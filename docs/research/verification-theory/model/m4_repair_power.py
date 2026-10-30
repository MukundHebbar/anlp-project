"""Part 4: repair calculus (checked against section 4), majority limit, power, training-data structure."""
import numpy as np
from itertools import combinations
from scipy import stats
from m1_calibrate import simulate, group_select, beta_moment
from m2_selection import judge, within_auroc

fits = np.load(__file__.replace("m4_repair_power.py", "fits.npy"), allow_pickle=True).item()

# ---------- repair: gain = E[f (p_x - Z)] for fresh resampling ----------
a, b, rho = fits["dev"]
acc = 0.6975
Epq = beta_moment(a, b, lambda p: p * (1 - p))
print(f"[repair] dev model: E[p(1-p)] = {Epq:.4f} -> perfect flags + fresh resample = +{100*Epq:.1f} pts "
      f"(observed with cut-and-regenerate: +7.0)")
r_fix = 0.07 / (1 - acc)                       # implied by the perfect-flag row of section 4
r_break = Epq / acc                            # fresh-resample estimate for correct attempts
for name, tpr, fpr, obs in [("JUDGE mixed", .074, .022, 70.13 - 69.75), ("JUDGE specialist", .041, .027, None)]:
    pred = (1 - acc) * tpr * r_fix - acc * fpr * r_break
    print(f"[repair] {name}: predicted {100*pred:+.2f} pts, observed {'' if obs is None else f'{obs:+.2f}'}")
lr_breakeven = acc * r_break / ((1 - acc) * r_fix)
print(f"[repair] flag rule helps iff TPR/FPR > {lr_breakeven:.2f}")
for d in [0.6, 1.0, 1.5]:  # binormal ROC, best global threshold
    t = np.linspace(-4, 4, 2001)
    tpr, fpr = stats.norm.sf(t - d), stats.norm.sf(t)
    gain = (1 - acc) * tpr * r_fix - acc * fpr * r_break
    i = gain.argmax()
    print(f"[repair] solution-level d'={d} (AUROC {stats.norm.cdf(d/np.sqrt(2)):.3f}): best +{100*gain[i]:.2f} pts "
          f"at TPR {tpr[i]:.2f} FPR {fpr[i]:.2f}")

# ---------- majority limit (N -> infinity) ----------
for k in ["test", "dev"]:
    a, b, rho = fits[k]
    lim = beta_moment(a, b, lambda p: (p > rho * (1 - p)).astype(float))
    print(f"[majority limit] {k}: P(right answer is the mode) = {100*lim:.1f}%")

# ---------- power ----------
a, b, rho = fits["test"]
disc = []
wa_sd = {}
for N in [4, 8, 16]:
    vals = []
    for s in range(150):
        r = np.random.default_rng(1000 + s)
        p, Z, attr = simulate(a, b, rho, N, 400, r)
        u, q = judge(p, Z, attr, 0.5, 0.75, 0.6, r)
        vals.append(within_auroc(1 - q, Z))
        if N == 4:
            maj = group_select(Z, attr, np.ones(Z.shape), r)
            qs = group_select(Z, attr, q, r)
            disc.append((maj != qs).mean())
    wa_sd[N] = (np.mean(vals), np.std(vals))
dd = np.mean(disc)
print(f"[power] discordant questions (judge pick vs majority): {100*dd:.1f}%  -> SE of the paired difference on "
      f"400 questions = {100*np.sqrt(dd/400):.2f} pts")
for eff in [1.0, 2.0, 3.0]:
    n = (1.96 + 0.84) ** 2 * dd / (eff / 100) ** 2
    print(f"[power] questions for 80% power to detect +{eff:.0f} pts over majority: {n:.0f}")
for N, (m, s) in wa_sd.items():
    print(f"[power] within-question AUROC on 400 questions x {N}: mean {m:.3f}, sd {s:.3f}")

# Rao-Blackwellised best-of-4: draw 16 per question, average over all 1820 4-subsets
idx = np.array(list(combinations(range(16), 4)))
one, rb = [], []
for s in range(60):
    r = np.random.default_rng(5000 + s)
    p, Z, attr = simulate(a, b, rho, 16, 400, r)
    _, q = judge(p, Z, attr, 0.5, 0.75, 0.6, r)
    one.append(group_select(Z[:, :4], attr[:, :4], q[:, :4], r).mean())
    sub = [group_select(Z[:, c], attr[:, c], q[:, c], r).mean() for c in idx[::20]]
    rb.append(np.mean(sub))
print(f"[power] sd of q-sum accuracy on 400 questions: one 4-draw {100*np.std(one):.2f} pts, "
      f"averaged over 4-subsets of 16 draws {100*np.std(rb):.2f} pts")

# ---------- training-data structure ----------
print("\n[data] per-question structure of own-attempt training data (test-like difficulty)")
print("   N | questions mixed | right-wrong pairs per question | wrong attempts from all-wrong questions")
for N in [4, 8, 16]:
    r = np.random.default_rng(2)
    p, Z, attr = simulate(a, b, rho, N, 200_000, r)
    k = Z.sum(1)
    print(f"  {N:2d} | {100*((k>0)&(k<N)).mean():5.1f}% | {(k*(N-k)).mean():6.2f} | "
          f"{100*((k==0)*N).sum()/(~Z).sum():4.0f}%")
