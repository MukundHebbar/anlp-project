# Jev judge fixes vs DeepSeek (500-answer samples)

## JUDGE

500 answers: 160 fail the strict gate (score 0, not judged); 339 compared with DeepSeek. V and L come from the parser in every row except v1.

| Version | κ V | κ L | κ E | κ M | Pearson | Rating exact | MAE | Means DeepSeek/Jev | Pairs same / opposite | Close pairs |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| v1 (Jev V/L/E/M) | 0.95 | 0.93 | 0.87 | 0.71 | 0.95 | 87% | 7.4 | V 2.67/2.61 L 2.12/2.10 E 1.84/2.00 M 1.94/2.55 | 86% / 12% | 82% / 16% |
| parser V/L + rubric M | 0.94 | 0.94 | 0.86 | 0.76 | 0.94 | 91% | 7.0 | V 2.67/2.63 L 2.12/1.98 E 1.84/1.99 M 1.94/2.45 | 86% / 14% | 84% / 16% |
| … + no-claim check | 0.94 | 0.94 | 0.86 | 0.76 | 0.94 | 91% | 7.0 | V 2.67/2.63 L 2.12/1.98 E 1.84/1.99 M 1.94/2.45 | 86% / 14% | 84% / 16% |
| **… + false-claim cap** | 0.94 | 0.94 | 0.86 | 0.75 | 0.94 | 90% | 7.0 | V 2.67/2.63 L 2.12/1.98 E 1.84/1.99 M 1.94/2.42 | 85% / 15% | 82% / 18% |

DeepSeek scored the 159 gated (hedged or contradictory) answers 35.8 on average and gave 73 of them full verdict credit; the gate scores them 0.

## RECONSTRUCT

506 answers; 45 fail the strict gate. DeepSeek flags 32 shortcuts. Zeroed answers keep their dimension scores for κ but score 0 in total.

| Version | κ P | κ T | κ E | κ M | Pearson | Rating exact | MAE | Means DeepSeek/Jev | Pairs same / opposite | Close pairs |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| v1 | 0.66 | 0.71 | 0.58 | 0.70 | 0.80 | 58% | 9.0 | P 2.03/1.72 T 2.33/2.04 E 1.94/2.10 M 1.02/1.25 | 81% / 18% | 70% / 30% | <!-- zeroed 16, of which DeepSeek shortcut 15 -->
| gate + stage 1, v1 E/M | 0.66 | 0.71 | 0.58 | 0.70 | 0.78 | 57% | 9.6 | P 2.03/1.72 T 2.33/2.04 E 1.94/2.10 M 1.02/1.25 | 82% / 17% | 70% / 30% | <!-- zeroed 56, of which DeepSeek shortcut 29 -->
| **gate + stage 1 + rubric E/M** | 0.66 | 0.71 | 0.57 | 0.66 | 0.77 | 57% | 9.8 | P 2.03/1.72 T 2.33/2.04 E 1.94/2.07 M 1.02/1.22 | 82% / 17% | 71% / 28% | <!-- zeroed 56, of which DeepSeek shortcut 29 -->

