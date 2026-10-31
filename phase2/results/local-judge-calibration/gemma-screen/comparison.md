# Gemma 4 12B: light calibration screen

Frozen sample: 12 responses per task per historical checkpoint; 96 JUDGE and 96 RECONSTRUCT responses. Four checkpoints fit thresholds, four evaluate them (48 planned held-out responses per task). No new reference API calls. Gemma had 13 failed requests: only 40 held-out RECONSTRUCT responses remained, versus 48 for Qwen. These RECONSTRUCT columns therefore do not compare identical retained samples. This is a small screen, not proof of equivalence.

| Held-out correlation with saved reference labels | Gemma 12B | Qwen27B, planned subset |
|---|---:|---:|
| judge, total calibrated score with gates | 0.909 | 0.931 |
| reconstruct, total calibrated score with gates | 0.847 | 0.814 |
| RECONSTRUCT continuous rubric-only, reference non-shortcuts | 0.832 | 0.860 |

Shortcut classification and rubric-only grading are audited separately in `reconstruct-audit.json`. The production scoring function and the calibration aggregation must match exactly. Qwen27B remains the final evaluator; no training job is started by this screen.

Extraction caveat: 380 of 929 rubric questions had allowed-label probability mass below 0.5, and 13 had zero allowed labels in the returned top 20 tokens. The threshold-only eligibility flag in the original summary does not establish operational reliability. The follow-up `gemma-full-explicit` run requests all single-token allowed-label spellings explicitly, retains the original prompts/rubrics/checkpoint split, and compares Qwen on matching complete response groups.
