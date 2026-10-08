# RECONSTRUCT with Jev in stages: few-shot shortcut check, then P/T/E/M

506 answers to 82 test questions (artifacts/jev-recon-v2/sample.json). DeepSeek flags 32 shortcuts. P/T/E/M are the v1 answers in every row; only the shortcut decision differs.

| Shortcut decision | Caught | False flags | Pearson | Rating exact | MAE | Pairs same / opposite | Close pairs same / opposite |
|---|---:|---:|---:|---:|---:|---|---|
| v1 (one question inside the validity request) | 15 / 32 | 1 | 0.80 | 58% | 9.0 | 81% / 18% | 70% / 30% |
| stage 1 Choice (type) | 21 / 32 | 8 | 0.80 | 57% | 9.0 | 82% / 17% | 70% / 30% |
| stage 1 yes/no | 16 / 32 | 5 | 0.80 | 57% | 9.1 | 82% / 18% | 70% / 30% |
| stage 1, Choice and yes/no agree | 16 / 32 | 5 | 0.80 | 57% | 9.1 | 82% / 18% | 70% / 30% |
| **final: stage 1 Choice or a precise check** | 23 / 32 | 10 | 0.80 | 58% | 9.0 | 83% / 17% | 69% / 31% |

Stage 1 Choice, most probable label (DeepSeek shortcut / not):
- answer-copy tautology: 19 / 4
- no usable question: 1 / 4
- not a shortcut: 12 / 466

Pairs: answers to the same question that DeepSeek scored differently (1167; close = within 12.5 points, 549), ordered by the probability-weighted score.
