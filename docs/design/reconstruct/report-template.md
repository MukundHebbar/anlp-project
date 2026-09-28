# RECONSTRUCT pilot and confirmation report

Status: NOT RUN. Replace placeholders with measured results; leave unavailable results marked unavailable.

## Frozen protocol

- Protocol / prompt versions or hashes:
- Source manifest, duplicate grouping, split seed and IDs:
- Exact converter, auditor, student and evaluator model versions:
- Reasoning mode, decoding configuration, context and output limits:
- Few-shot demonstrations and exclusion of near-duplicate sources:
- Development budget and deviations from the [specification](SKILL.md):

## Data and conversion coverage

| Stage | Sources | Reason for removal or review |
|---|---:|---|
| Source pool | — | — |
| Worked solution checked | — | — |
| Four-observation bank accepted | — | — |
| Disclosure variants accepted | — | — |
| Common factorial-development subset | — | — |
| Primary-policy confirmation subset | — | — |

Break this down by topic and difficulty. Report retained versus excluded source SOLVE performance where available, to expose selection effects. Preserve failures and retries in the manifest.

## Human and model scoring calibration

Report the 60-output stratified audit and 12 controls separately. Include adjudication procedure, binary confusion matrix, score agreement, per-clue disagreements, false accepts, unresolved cases, and uncertainty intervals. If prompts were revised, report the fresh 30-output validation separately; do not reuse fitting labels as independent validation.

## Full development grid

Attach all 36 rows with: clue count, disclosure, format, distinct source count, repeated-output count, grounded success, mean score/4, answer correctness, per-item all-clue grounding, shortcut rate, unresolved rate, source-recovery distribution, input/output tokens, and truncation rate.

Use source-level uncertainty. Do not average metrics with different denominators without stating how. Report success bounds if unresolved cases remain.

## Clue disclosure and contribution

- Direct restatement and joint-restatement audit rates before filtering:
- Counts of original-given / target / derived-relation / intermediate-value / structural-fact tags:
- Tied disclosure levels and common-subset eligibility:
- Nested count effects on primary success and source recovery:
- Leave-one-out effects, including redundant or negative-contribution clues:
- Format effects for matched facts and order, with token lengths:
- Exploratory interactions and their uncertainty:

These are observed disclosure characteristics and performance effects, not measured information in bits.

## Selected policy

- Chosen count / disclosure / format:
- Evidence that clues are useful, incomplete, and not direct source restatement:
- Development performance and judge reliability:
- Reason for choosing this policy using the predeclared selection rule:
- Prompt changes or departures from the proposed 35–70% operating range:
- Freeze timestamp / hashes before confirmation:

## Held-out confirmation

| Condition | Sources | Grounded success / bounds | Mean score/4 | Source recovery=2 | Unresolved | Tokens |
|---|---:|---:|---:|---:|---:|---:|
| Primary policy | — | — | — | — | — | — |
| Fewer clues | — | — | — | — | — | — |
| More clues | — | — | — | — | — | — |
| Answer only | — | — | — | — | — | — |
| Full worked solution | — | — | — | — | — | — |
| Random audited excerpts | — | — | — | — | — | — |

State actual count values, excerpt coverage/length differences, decoding seeds, and resolved denominators. Report paired differences against the primary policy. This confirmation does not estimate the entire disclosure×format interaction grid.

## Qualitative cases

Show one grounded source recovery, one valid alternative, one incorrect answer, one incompatible-clue response, one answer shortcut, and one evaluator disagreement. Include only the public evidence before revealing the source comparison. Explain each score briefly.

## Training handoff and limitations

Record frozen production policy, training-source split, teacher completion procedure using public evidence only, completion acceptance, and human checks. State what remains unimplemented. No cross-task learning claim can be made from this calibration alone; attach the later SOLVE/JUDGE/RECONSTRUCT transfer matrix when training runs exist.
