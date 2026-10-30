"""CPU bounds for sampling-side interventions, from the cached 16 attempts per question (test ∪ extra).

Each question's 16 attempts stand in for the solver's answer distribution π (unanswered attempts are a separate
"no answer" mass that never wins a vote).

A. Answer-level sharpening, π_α(g) ∝ π(g)^α: the best case for power sampling / low-temperature annealing if the
   sequence likelihood were the same within an answer. Majority@N under π_α, for several α and N.
B. Decorrelation: move a fraction δ of the attractor (most common wrong answer) mass to diffuse one-off wrong answers.
   Single-attempt accuracy is unchanged; only the correlation of wrong answers drops.
C. Headroom: the share of questions where the right answer is present but not the plurality, and where it is absent.
"""
import json
from collections import Counter, defaultdict

import numpy as np

RNG = np.random.default_rng(20261029)
SIMS = 4000


def load():
    qs = defaultdict(list)
    for split in ("test", "extra"):
        for line in open(f"runs/graded/{split}.jsonl"):
            r = json.loads(line)
            qs[r["uid"]].append((r["group"], r["correct"]))
    out = []
    for atts in qs.values():
        assert len(atts) == 16
        # equivalent right answers can land in separate groups; merge them into one right group
        right = {g for g, c in atts if c and g >= 0}
        counts = Counter("R" if g in right else g for g, _ in atts if g >= 0)
        out.append((counts, "R" if right else None))
    return out


def dist(counts, right, alpha=1.0, delta=0.0):
    """Answer masses: [right, attractor, other named wrong..., diffuse wrong (never ties), none]. Sums to 1."""
    wrong = sorted(((c, g) for g, c in counts.items() if g != right), reverse=True)
    r = counts.get(right, 0) if right is not None else 0
    named = [c for c, _ in wrong]
    if named and delta:
        moved = delta * named[0]
        named[0] -= moved
        diffuse = moved
    else:
        diffuse = 0.0
    none = 16 - r - sum(c for c, _ in wrong)
    masses = np.array([r] + named, float) ** alpha
    # sharpening applies to answered mass only; keep the answered/unanswered split and diffuse mass as is
    answered = r + sum(named)
    masses = masses / masses.sum() * answered if masses.sum() else masses
    return masses, diffuse, none


def majority_acc(masses, diffuse, none, n):
    """P(right answer wins a plurality vote of n draws), random tie-break; diffuse draws are all distinct answers."""
    probs = np.concatenate([masses, [diffuse, none]]) / 16
    probs = probs / probs.sum()
    draws = RNG.multinomial(n, probs, size=SIMS)
    named = draws[:, : len(masses)].astype(float)
    # each diffuse draw is its own answer with count 1
    top = np.maximum(named.max(1), (draws[:, -2] > 0).astype(float))
    right_c = named[:, 0]
    n_top_named = (named == top[:, None]).sum(1)
    n_top = n_top_named + np.where(top == 1, draws[:, -2], 0)
    win = (right_c == top) & (right_c > 0)
    return float(np.mean(np.where(win, 1.0 / n_top, 0.0)))


def ceiling(masses, diffuse):
    """N → ∞: right wins iff its mass is strictly the largest named mass (diffuse never wins)."""
    if masses[0] == 0:
        return 0.0
    rest = masses[1:]
    if len(rest) == 0 or masses[0] > rest.max():
        return 1.0
    return 1.0 / (1 + (rest == masses[0]).sum()) if masses[0] == rest.max() else 0.0


def main():
    qs = load()
    single = np.mean([c.get(r, 0) / 16 if r is not None else 0 for c, r in qs])
    print(f"questions {len(qs)}, single-attempt accuracy {100 * single:.1f}%\n")

    print("## C. Headroom")
    absent = np.mean([r is None for _, r in qs])
    plural = np.mean([ceiling(*dist(c, r)[:2]) for c, r in qs])
    print(f"right answer absent from 16: {100 * absent:.1f}%; right is plurality (ceiling of voting on π): "
          f"{100 * plural:.1f}%; present but not plurality: {100 * (1 - absent - plural):.1f}%\n")

    print("## A. Answer-level sharpening π^α (best case for power sampling / annealing)")
    print("| α | maj@1 | maj@4 | maj@8 | maj@16 | N→∞ |\n|---|---|---|---|---|---|")
    for alpha in (1, 2, 4, 8):
        row = []
        for n in (1, 4, 8, 16):
            row.append(np.mean([majority_acc(*dist(c, r, alpha), n) for c, r in qs]))
        lim = np.mean([ceiling(*dist(c, r, alpha)[:2]) for c, r in qs])
        print(f"| {alpha} | " + " | ".join(f"{100 * x:.1f}" for x in row) + f" | {100 * lim:.1f} |")

    print("\n## B. Decorrelation: δ of attractor mass moved to diffuse wrong answers (single-attempt acc unchanged)")
    print("| δ | maj@4 | maj@8 | maj@16 | N→∞ |\n|---|---|---|---|---|")
    for delta in (0, 0.25, 0.5, 0.75, 1.0):
        row = [np.mean([majority_acc(*dist(c, r, 1, delta), n) for c, r in qs]) for n in (4, 8, 16)]
        lim = np.mean([ceiling(*dist(c, r, 1, delta)[:2]) for c, r in qs])
        print(f"| {delta} | " + " | ".join(f"{100 * x:.1f}" for x in row) + f" | {100 * lim:.1f} |")


if __name__ == "__main__":
    main()
