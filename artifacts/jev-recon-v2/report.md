# RECONSTRUCT Jev v2 vs v1, against DeepSeek

Fixed sample: 506 checkpoint answers to 82 test questions (artifacts/jev-recon-v2/sample.json). P and T are identical in v1 and v2.

## Dimensions (weighted κ against DeepSeek; mean DeepSeek vs Jev)

| Dim | v1 κ | v2 κ | DeepSeek mean | v1 mean | v2 mean |
|---|---:|---:|---:|---:|---:|
| E | 0.58 | 0.38 | 1.94 | 2.10 | 2.88 |
| M | 0.70 | 0.71 | 1.02 | 1.25 | 1.12 |

## Shortcuts (DeepSeek flags 32 of 506)

| Detector | Caught | False flags |
|---|---:|---:|
| v1 Jev | 15 / 32 | 1 |
| v2 code check | 14 / 32 | 16 |
| v2 Jev questions | 27 / 32 | 50 |
| v2 combined | 30 / 32 | 63 |

- Code check, answer stated in the question field: 12 agree with DeepSeek, 13 not flagged by DeepSeek.
- Code check, meta commentary in the question field: 2 agree with DeepSeek, 3 not flagged by DeepSeek.

## Total score

| Version | Pearson | 1–5 rating exact | MAE | Mean (DeepSeek 43.2) | Pairs same / opposite / tie | Close pairs same / opposite / tie |
|---|---:|---:|---:|---:|---|---|
| v1 | 0.80 | 58% | 9.0 | 43.0 | 81% / 18% / 0% | 70% / 30% / 0% |
| v2 (code shortcut) | 0.69 | 55% | 10.7 | 45.6 | 80% / 20% / 0% | 71% / 29% / 0% |
| v2 (jev shortcut) | 0.74 | 55% | 10.9 | 42.7 | 79% / 19% / 2% | 68% / 31% / 2% |
| v2 (combined shortcut) | 0.71 | 55% | 11.5 | 40.9 | 78% / 19% / 3% | 66% / 31% / 3% |

Pairs: answers to the same question that DeepSeek scored differently (1167; close = within 12.5 points, 549), ordered with Jev's probability-weighted score, as a GRPO reward would use it.

## Follow-up (offline, same Jev answers; no new calls)

- The per-observation E questions are too lenient (mean 2.88 vs DeepSeek 1.94, κ 0.38), so v1's E Score stays.
  The decomposed M matches v1 (κ 0.71 vs 0.70), so v1's M stays as well.
- Shortcut sub-questions:
  - "states the value it asks for": 19 catches, 1 false flag.
  - "only repeats the answer": 2 catches, 0 false flags.
  - "coherent request": 12 catches, **53 false flags**. Not used.
- The code check's 16 disagreements are drafting monologue leaked into the question field, and DeepSeek
  scored the final question as substantive. They are a format problem, not shortcuts under the rubric.

| Configuration | Shortcuts caught | False flags | Pearson | Rating exact | Pairs same / opposite | Close pairs same / opposite |
|---|---:|---:|---:|---:|---|---|
| v1 | 15 / 32 | 1 | 0.80 | 58% | 81% / 18% | 70% / 30% |
| **v1 P/T/E/M + shortcut = "states value" or "repeats answer"** | **19 / 32** | **1** | **0.81** | 58% | 82% / 18% | 70% / 30% |

Chosen: the bold row. The 13 shortcuts still missed are mostly DeepSeek's "no usable question" type
(monologue instead of a request); no Jev question tested here separates them without many false flags.
