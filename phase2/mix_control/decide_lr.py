#!/usr/bin/env python3
"""Decision rule for the lower-lr SOLVE-only controls, fixed on 2026-10-26 before any of their results existed (README).

Why: at the same lr, the SOLVE-only control spends each Adam step on SOLVE alone while the mixed run shares it with
JUDGE / RECONSTRUCT, so the control takes larger SOLVE steps. If a control with smaller steps reaches the mixed model,
the mixed run's SOLVE gain is explained by step size, not by the JUDGE / RECONSTRUCT content.
Arms: mixed (mixed75); SOLVE-only controls at lr 2e-5 (ctrl-s0/s1, done), 1e-5 (ctrl-lr1e-5-s0/s1) and 6.7e-6
(ctrl-lr6.7e-6-s0/s1, = 2e-5 / 3), everything else as decide.py (same prompts, steps, validation set, metrics).

  Transfer by content supported: for EVERY control lr, mixed - mean(its two seeds) > 0 with the 95% interval above
  0 on avg@4, and mixed above each of its seeds.
  Otherwise: the gain is explained by step size for the lr(s) that reach mixed (no evidence of transfer by content).
The SOLVE test set is evaluated once, after this decision.

    python phase2/mix_control/decide_lr.py
"""
import decide as d

LRS = {"2e-5": ("ctrl-s0", "ctrl-s1"), "1e-5": ("ctrl-lr1e-5-s0", "ctrl-lr1e-5-s1"),
       "6.7e-6": ("ctrl-lr6.7e-6-s0", "ctrl-lr6.7e-6-s1")}


def main() -> None:
    runs = ["mixed75"] + [r for pair in LRS.values() for r in pair]
    arms = {r: d.per_question(r) for r in runs}
    qs = sorted(set.intersection(*(set(v) for v in arms.values())))
    if any(len(arms[a][q]) != 4 for a in arms for q in qs):
        raise SystemExit("every question needs 4 samples in every arm")
    avg = lambda v: sum(v) / 4  # noqa: E731
    any_ = lambda v: float(any(v))  # noqa: E731
    score = {a: 100 * sum(avg(arms[a][q]) for q in qs) / len(qs) for a in arms}
    print(f"{len(qs)} validation questions, step 75")
    for a in runs:
        print(f"  {a:18s} avg@4 {score[a]:.1f}  pass@4 {100 * sum(any_(arms[a][q]) for q in qs) / len(qs):.1f}")
    beaten = {}
    for lr, (s0, s1) in LRS.items():
        mean, lo, hi = d.interval([avg(arms["mixed75"][q]) - (avg(arms[s0][q]) + avg(arms[s1][q])) / 2 for q in qs])
        spread = d.interval([avg(arms[s1][q]) - avg(arms[s0][q]) for q in qs])
        beaten[lr] = lo > 0 and score["mixed75"] > max(score[s0], score[s1])
        print(f"  lr {lr:6s}: mixed - mean(seeds) {100 * mean:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]; seed spread "
              f"{100 * spread[0]:+.1f} [{100 * spread[1]:+.1f}, {100 * spread[2]:+.1f}] -> mixed {'beats' if beaten[lr] else 'does not beat'} it")
    if all(beaten.values()):
        print("Transfer by content supported: mixed beats the SOLVE-only control at every lr")
    else:
        print("No evidence of transfer by content: step size explains the gain at lr " +
              ", ".join(lr for lr, b in beaten.items() if not b))


if __name__ == "__main__":
    main()
