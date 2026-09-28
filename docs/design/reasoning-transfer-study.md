# Controlled transfer across SOLVE, JUDGE, and RECONSTRUCT

## Main contribution

Study how training under different reasoning demands and information conditions transfers across tasks. The central evidence is a train-task by evaluation-task matrix. A new individual task is not required for this empirical contribution.

| Task | Information supplied | Required reasoning |
|---|---|---|
| SOLVE | Complete problem statement | Construct a valid solution and derive the answer. |
| JUDGE | Problem plus complete candidate solution information | Distinguish valid from invalid reasoning, localize the issue where applicable, and ground the judgment. |
| RECONSTRUCT | Final answer plus sparse, partial solution evidence; source question hidden | Infer a plausible question and justify its consistency with the observations. |

The intended contrast is constructive reasoning, evaluative reasoning with supplied information, and abductive reasoning under incomplete evidence. “Complete information” in JUDGE means complete material to assess, not guaranteed truthful reasoning or a supplied correctness label. The tasks change reasoning direction, output demand, and information structure together. Consequently, an overall difference cannot be attributed solely to information quantity without an additional within-task intervention.

The settings are operationally distinct. Whether their learned capabilities are shared, complementary, or separable is an empirical question.

## Primary experiment

Start from one identical base checkpoint and train three independent models, one per task. Evaluate every checkpoint on every task, without additional target-task training in the primary matrix.

| Training | Test SOLVE | Test JUDGE | Test RECONSTRUCT |
|---|---|---|---|
| None | Baseline | Baseline | Baseline |
| SOLVE only | Within-task learning | S → J transfer | S → R transfer |
| JUDGE only | J → S transfer | Within-task learning | J → R transfer |
| RECONSTRUCT only | R → S transfer | R → J transfer | Within-task learning |

Let M_i be a checkpoint trained on task i, M_0 the initial checkpoint, and score_j a fixed target-task metric. Report:

    delta(i → j) = score_j(M_i) - score_j(M_0)

Compare training interventions within each target column, where the metric and evaluation set are identical. Do not interpret identical numerical changes across unlike task rubrics as equal capability gains. Report baseline, absolute gain, uncertainty, and each task's own-training reference. Positive, absent, or negative transfer are all valid findings.

Separate direct transfer from a later source-pretraining/target-fine-tuning experiment; the latter answers a different question about adaptation or sample efficiency.

## Questions the results should answer

1. Does learning to generate correct solutions improve the ability to assess supplied reasoning and infer missing problem structure?
2. Does learning to discriminate correct and incorrect reasoning improve construction or reconstruction?
3. Does learning from sparse evidence improve forward solving and judgment?
4. Are these relationships asymmetric? For example, does J → S improve while S → J remains unchanged under the stated controls?
5. Does combined training provide useful complementarity or cause interference?

After the single-task matrix, evaluate S+J, S+R, J+R, and S+J+R with a fixed total training budget. Compare each target score with the corresponding pure-task budget control. If only the all-task mixture is feasible, limit conclusions to joint versus single-task training rather than attributing benefits to a specific pair.

## Essential controls

- **Match mathematical content.** Draw the three training forms from the same underlying source pool. Avoid a confound where one task simply contains easier or different topics.
- **Split before conversion.** Group identical and near-duplicate source problems, then split into train/development/test. All task forms and all clue variants of a source stay in its split. Sharing a source across tasks within a split is intended; sharing it across train/test is leakage.
- **Control training exposure.** Keep initialization, training method, tuning allowance, and decoding policy fixed. Predeclare the primary budget, such as processed tokens/compute; also report unique sources, examples, updates, input tokens, and supervised output tokens. Equal example counts alone do not equate training exposure because task lengths differ. Where feasible, add a source-count-matched sensitivity run.
- **Make zero-target-training evaluation meaningful.** Give every checkpoint the same explicit task instructions and fixed development-only demonstrations if needed. Report formatting failures separately. Distinguish gains in mathematical reasoning from learning a response schema.
- **Keep JUDGE candidates fixed across checkpoints.** Use a controlled correct/incorrect mix, meaningful errors, and audited labels. Changing candidate quality with the evaluated solver would change the test distribution and confound transfer.
- **Require grounded outputs.** SOLVE needs answer correctness; JUDGE needs a correct verdict and supported diagnosis; RECONSTRUCT needs a well-posed question, correct supplied answer, and substantive clue compatibility. Evaluate source recovery separately from compatible alternative reconstruction. Human-audit automated scoring.
- **Use training seeds and source-level uncertainty.** Repeated generations from one problem do not substitute for independent source problems or training runs. Analyze all checkpoints on the same held-out sources.

An unchanged off-diagonal score does not prove fully distinct reasoning mechanisms; it may reflect training strength, task difficulty, output adaptation, or statistical uncertainty. Likewise, higher correlation alone does not establish that training one task benefits another. The intervention matrix addresses the latter question directly.

## Role of the clue study

The executable-as-a-procedure task definition, prompt pack, and pilot plan are specified in [RECONSTRUCT/SKILL.md](reconstruct/SKILL.md). These are draft specifications, not completed model runs.

The clue-count, disclosure, and presentation experiments validate the RECONSTRUCT condition. They establish that it has useful but incomplete evidence, permits grounded alternatives, avoids direct question restatement, and supports reliable scoring. A simple few-shot converter is compatible with this study.

Calibrate on development data and freeze a primary reconstruction condition for the transfer matrix. A small held-out clue sweep can then test whether transfer changes with evidence availability. Do not make the entire clue-format factorial the main project or select test examples to force a desired Qwen score.

## Positioning against prior work

The [literature review](../research/reconstruct/literature-review.md) documents component-task precedents. The closest training comparisons include [RevThink](https://aclanthology.org/2025.naacl-long.434/), [ALIVE](https://arxiv.org/abs/2602.05472), and [Learning to Self-Verify Makes Language Models Better Reasoners](https://arxiv.org/abs/2602.07594). The last explicitly reports asymmetric generation/verification training effects, so asymmetric transfer alone cannot be claimed as new.

The proposed contribution is the controlled, matched-content study spanning all three specified settings, with full directional evaluation and budget-matched mixture comparisons. Its precise novelty remains subject to method-level comparison with these papers. No transfer outcomes have yet been measured here.
