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

## Fixed design decisions

These decisions are final. They replace any earlier text, including the course proposal, that assumes matched source questions, other split sizes, or supervised fine-tuning.

- **Data:** [FINAL-v3](../../data/manifests/final-v3/README.md) is the only dataset. It has 4,000 DeepMath-103K questions per task, split 3,600 train / 400 test. The datasets will not be regenerated.
- **Different questions per task.** SOLVE, JUDGE and RECONSTRUCT use disjoint DeepMath questions. No question appears in two tasks. The tasks are matched by distribution instead of by item. Every task draws from the same four broad topics (Algebra, Calculus, Discrete Mathematics, Number Theory), the same difficulty range (5.0–8.0), and the same filters. Each task's share of questions at every difficulty level is within about one percentage point of the other tasks' (upper band 7.0–8.0: 30.4% / 30.3% / 30.4%). Topic shares are close but not identical; JUDGE is the least even.
- **Splits:** 3,600 train / 400 test per task, chosen for compute constraints. There is no separate development split. Any prompt, checkpoint or mixture decision must use training questions only. The test sets are used only for final evaluation.
- **Models and method details:** student Qwen3.5-2B and teacher Qwen3.8-27B (16k-token training rollouts, 32k-token evaluation); baseline results and the OPD configuration are in [baselines-and-opd-method.md](../research/transfer-study/baselines-and-opd-method.md).
- **Training method:** on-policy distillation (OPD) only; no supervised fine-tuning. The student generates responses to training prompts, and the teacher supplies next-token probabilities along those responses. The loss is reverse KL, D_KL(p_student ‖ p_teacher), averaged over the student's generated tokens. The teacher must share the student's tokenizer. The `training.chain_of_thought` and `training.final_answer` fields in FINAL-v3 are not imitation targets under OPD. Only `training.input` (the prompt) is used for training. The answer keys are used for evaluation.

## Primary experiment

Start from one identical base checkpoint and train three independent models with OPD, one per task. Evaluate every checkpoint on every task, without additional target-task training in the primary matrix.

| Training | Test SOLVE | Test JUDGE | Test RECONSTRUCT |
|---|---|---|---|
| None | Baseline | Baseline | Baseline |
| SOLVE only | Within-task learning | S → J transfer | S → R transfer |
| JUDGE only | J → S transfer | Within-task learning | J → R transfer |
| RECONSTRUCT only | R → S transfer | R → J transfer | Within-task learning |

Let M_i be a checkpoint trained on task i, M_0 the initial checkpoint, and score_j a fixed target-task metric. Report:

    delta(i → j) = score_j(M_i) - score_j(M_0)

Compare training interventions within each target column, where the metric and evaluation set are identical. Do not interpret identical numerical changes across unlike task rubrics as equal capability gains. Report baseline, absolute gain, uncertainty, and each task's own-training reference. Positive, absent, or negative transfer are all valid findings.

Separate direct transfer from a later source-training/target-training experiment; the latter answers a different question about adaptation or sample efficiency.

## Questions the results should answer

1. Does learning to generate correct solutions improve the ability to assess supplied reasoning and infer missing problem structure?
2. Does learning to discriminate correct and incorrect reasoning improve construction or reconstruction?
3. Does learning from sparse evidence improve forward solving and judgment?
4. Are these relationships asymmetric? For example, does J → S improve while S → J remains unchanged under the stated controls?
5. Does combined training provide useful complementarity or cause interference?

After the single-task matrix, evaluate S+J, S+R, J+R, and S+J+R with a fixed total training budget. Compare each target score with the corresponding pure-task budget control. If only the all-task mixture is feasible, limit conclusions to joint versus single-task training rather than attributing benefits to a specific pair.

## Essential controls

- **Match the question distribution, not individual questions.** The tasks use different questions drawn with the same topic buckets, difficulty range and filters, and near-identical difficulty shares (see *Fixed design decisions*). This prevents one task from simply having easier or different topics. It does not make the questions identical. A difference between rows can therefore reflect item-level differences as well as the task form. Report per-topic and per-difficulty results so such differences stay visible. Item-level cross-task analyses, such as whether a model solves the same question it judges, are not possible.
- **No leakage across tasks or splits.** No question appears in two tasks, counting every DeepMath copy (checked by `scripts/audit_final_dataset.py`). Train and test never share a question. RECONSTRUCT test questions come only from sources that no prompt development touched.
- **Control training exposure.** Keep initialization, OPD settings, teacher, tuning allowance, maximum generation length and decoding policy fixed across task arms. Predeclare the primary budget, such as optimizer steps or prompts processed. Also report unique questions, student-generated tokens and teacher-scored tokens. Under OPD the student's response lengths differ by task and change during training, so equal prompt counts do not equate exposure.
- **Make zero-target-training evaluation meaningful.** Give every checkpoint the same explicit task instructions and fixed demonstrations taken from training questions if needed, never from test. Report formatting failures separately. Distinguish gains in mathematical reasoning from learning a response schema.
- **Keep JUDGE candidates fixed across checkpoints.** Use a controlled correct/incorrect mix, meaningful errors, and audited labels. Changing candidate quality with the evaluated solver would change the test distribution and confound transfer.
- **Require grounded outputs.** SOLVE needs answer correctness; JUDGE needs a correct verdict and supported diagnosis; RECONSTRUCT needs a well-posed question, correct supplied answer, and substantive clue compatibility. Evaluate source recovery separately from compatible alternative reconstruction. Human-audit automated scoring.
- **Use training seeds and question-level uncertainty.** Repeated generations from one problem do not substitute for independent problems or training runs. Evaluate all checkpoints on the same 400 held-out test questions for each task, and bootstrap over those questions.

An unchanged off-diagonal score does not prove fully distinct reasoning mechanisms; it may reflect training strength, task difficulty, output adaptation, or statistical uncertainty. Likewise, higher correlation alone does not establish that training one task benefits another. The intervention matrix addresses the latter question directly.

## Role of the clue study

The executable-as-a-procedure task definition, prompt pack, and pilot plan are specified in [RECONSTRUCT/SKILL.md](reconstruct/SKILL.md). These are draft specifications, not completed model runs.

The clue-count, disclosure, and presentation experiments validate the RECONSTRUCT condition. They establish that it has useful but incomplete evidence, permits grounded alternatives, avoids direct question restatement, and supports reliable scoring. A simple few-shot converter is compatible with this study.

The FINAL-v3 RECONSTRUCT condition (the final answer plus four clues) is now frozen for the transfer matrix. A small held-out clue sweep can then test whether transfer changes with evidence availability. Do not make the entire clue-format factorial the main project or select test examples to force a desired Qwen score.

## Positioning against prior work

The [literature review](../research/reconstruct/literature-review.md) documents component-task precedents. The closest training comparisons include [RevThink](https://aclanthology.org/2025.naacl-long.434/), [ALIVE](https://arxiv.org/abs/2602.05472), and [Learning to Self-Verify Makes Language Models Better Reasoners](https://arxiv.org/abs/2602.07594). The last explicitly reports asymmetric generation/verification training effects, so asymmetric transfer alone cannot be claimed as new.

The proposed contribution is a controlled on-policy-distillation study spanning all three settings. The task datasets are matched in distribution, not item by item. The study has full directional evaluation and budget-matched mixture comparisons. Its precise novelty remains subject to method-level comparison with these papers. No transfer outcomes have yet been measured here.
