# final_v2 pilot: validate today's untested pipeline edits before any scaled run

## Why

Three edits landed in `data/prompts/reconstruct/final_v2/` and the shared orchestration
(`scripts/run_reconstruct_final100.py`, `scripts/run_reconstruct_valid100.py`) on
2026-09-21, at explicit user direction, with zero examples run against them:

1. The `copy` leakage-challenge gate was removed; acceptance now depends on `audit`
   alone. In the last validated run (`valid-100-recovery-v1`, on the unmodified
   `final_v1` prompts), the copy gate alone caused 56/71 (79%) of all rejections, so
   acceptance rates under `final_v2` should be substantially higher — this pilot
   checks whether that comes with a real leakage-safety cost.
2. `student.md` dropped the "Equivalent mathematical formulations are welcome."
   sentence and both worked few-shot examples. Untested against the two-example
   version used in every prior student prompt variant (p1–p18).
3. `judge_fidelity`/`judge_validity` were briefly merged then explicitly reverted
   (`final_v2` uses the original separate two-judge prompts, unchanged from `final_v1`).

The prior validated baseline (`final_v1`, `valid-100-recovery-v1`) sits at
**2/100 semantic recoveries (2%)**, far under the project's 20–40% target
(`docs/design/reconstruct/CURRENT_PROTOCOL.md`). Generating a full dataset on top of
untested edits to an already-underperforming pipeline would confound any result: a
bad outcome could not be attributed to the task's inherent difficulty vs. today's edits.

## Scope

A small, cheap pilot — **not** confirmation data, **not** eligible for the paper's
final numbers. Purpose is solely: (a) sanity-check that audit-only gating doesn't let
obviously-leaking clue banks through, and (b) get a first noisy read on whether the
no-few-shot student prompt looks comparable, better, or worse than the 2% baseline.

- 20 fresh DeepMath-103K sources, excluded against every source already used by the
  146-item curated pilot pool (`final-100-v1`'s source pool) and the 608-source pool
  used by `valid-100-v1`/`valid-100-recovery-v1`, so this pilot's leakage/quality
  signal isn't contaminated by reused material.
- Prompts: `data/prompts/reconstruct/final_v2/*` (convert, audit, student, judge_fidelity,
  judge_validity — unchanged convert/audit/judges, edited student, no copy stage).
- Cost ceiling: $1.00 (a fraction of the $2.80/$4.75 ceilings used for the 100-row runs).
- Same models, sampling and rating thresholds as `final_v1` (Qwen/Qwen3-4B non-thinking
  student, DeepSeek V4.1 Flash teacher, RATING-v4 boundaries) — only the three edits
  above vary, so any change in outcome is attributable to them.

## What happens after

This pilot's numbers are read by eye, not treated as a release decision on their own —
20 sources is far below the 25-family confirmation threshold this project's protocol
already requires. If nothing looks structurally broken (no obvious leaked questions
slipping through audit-only gating, semantic-recovery rate not collapsing to zero),
the next step is a properly sized, source-family-allocated confirmation run before
`final_v2` could be considered for a scaled dataset generation. If something looks
broken, the specific edit responsible gets isolated and reverted, same as the
judge-merge revert on 2026-09-21.
