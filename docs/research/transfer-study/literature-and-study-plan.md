# SOLVE / JUDGE / RECONSTRUCT: literature review, gaps, and study plan

Written 2026-09-25. Extends the [RECONSTRUCT literature review](../reconstruct/literature-review.md)
(which covers RECONSTRUCT's lineage in depth) and the [study framing](../../design/reasoning-transfer-study.md).
This review focuses on the transfer question: which training transfers to what, and how it
interacts with distillation and cross-model transfer. It is a targeted narrative review of
roughly 25 additional papers found by web search on 2026-09-25, read at abstract/summary depth
unless stated; it is not a systematic review, and every "gap" below means "not found in this
search", not "proven absent".

**Design update (2026-09-28).** Three decisions are now final and override earlier text in this
review (details in the [study framing](../../design/reasoning-transfer-study.md#fixed-design-decisions)):
- Each task uses **different DeepMath questions**. The tasks are matched by topic buckets,
  difficulty range and difficulty shares, not by item. The datasets will not be regenerated.
- The splits are **3,600 train / 400 test per task** ([FINAL-v3](../../../data/manifests/final-v3/README.md)).
- **On-policy distillation (reverse KL) is the only training method.** There is no SFT arm.

The sections below have been revised to match these decisions.

## 1. What the three tasks are

All three tasks are built from the same kind of source: a math problem with a known answer and
a reference solution. Each task uses its own questions, drawn from the same topic and
difficulty distribution. The tasks differ in what the model is given and what it must produce.

| | SOLVE | JUDGE | RECONSTRUCT |
|---|---|---|---|
| Given | Full problem | Full problem + a full candidate solution | Final answer + 4 sparse clues; problem hidden |
| Produces | A solution and answer | Verdict, first wrong step, explanation | A plausible question + justification |
| Information | Complete statement, no solution | Most: statement *and* a worked attempt | Least: fragments only |
| Reasoning direction | Forward (premises → answer) | Checking (verify each step) | Backward (answer + fragments → premises) |
| Core demand | Construction | Discrimination and localization | Abduction: grounded hypothesis generation |
| Failure mode | Wrong derivation | Accepting a flaw / inventing one | Inventing an unsupported or answer-copying question |

**How to read the three together.** They are three *information regimes* over the same
distribution of mathematics. JUDGE has the most information but needs the finest discrimination;
SOLVE needs a path to be constructed; RECONSTRUCT needs structure to be inferred from too little.
The study holds the topic and difficulty distribution fixed and varies the regime. This removes
topic and difficulty mix as an explanation for differences in transfer. Item-level differences
between the question sets remain, so report per-topic and per-difficulty results.

**Why transfer is plausible in each direction** (hypotheses to test, not claims):

- **JUDGE → SOLVE.** Learning to spot the first wrong step should teach self-checking, which a
  solver can apply to its own steps. The closest precedents (critique fine-tuning;
  self-verification training) report exactly this direction working.
- **SOLVE → JUDGE.** A better solver knows more correct derivations, but the self-verification
  paper reports that generation training does *not* bring verification with it. A
  weak or absent effect here is itself a finding.
- **RECONSTRUCT → JUDGE.** Both require reading partial reasoning and asking "what must be true
  for this to hold?" Localizing an error is a structural inference over steps, which
  reconstruction trains directly.
- **RECONSTRUCT → SOLVE.** Backward reasoning improved forward reasoning in RevThink, and
  abduction tasks mattered for math in Absolute Zero's ablations, but neither isolated
  reconstruction from sparse evidence.
- **SOLVE / JUDGE → RECONSTRUCT.** Should mainly raise the *mathematical validity* part of the
  reconstruction score (checking a candidate question), not the *fidelity* part (recovering the
  original), because only reconstruction trains hypothesis generation from fragments.

These component-level predictions matter: they turn "does A help B" into "which part of B does
A help", which is where real insight comes from.

## 2. What is already known

### 2.1 Generation ↔ verification transfer (closest precedents for SOLVE ↔ JUDGE)

| Work | Finding | What it means for us |
|---|---|---|
| **Learning to Self-Verify** ([Chen et al., 2026](https://arxiv.org/abs/2602.07594)) | Generation training does not improve self-verification, even on the same task; verification training improves generation, with more efficient traces. RL, multi-objective. | The asymmetry question is already asked for SOLVE ↔ JUDGE. We must go beyond it: add a third regime, hold content fixed, and decompose *which* skill moves. |
| **Critique Fine-Tuning** ([Wang et al., 2025](https://arxiv.org/abs/2501.17703)) | Training to critique noisy solutions beats imitating correct ones by 4–10% on six math benchmarks; 50K examples rival 2M-sample SFT. | JUDGE-style data may be a better *distillation format* than SOLVE-style data. We can test whether this holds for a third format (RECONSTRUCT) and across student families. |
| **Generative Verifiers** ([Zhang et al., 2024](https://arxiv.org/abs/2408.15240)) | Jointly training generation and verification with next-token prediction transfers positively in both directions. | Supports running mixtures as well as single tasks; joint training is a baseline, not our contribution. |
| **Mind the Gap** ([Song et al., ICLR 2025](https://arxiv.org/abs/2412.02674)) | Formalizes the *generation–verification gap* and shows it scales with pretraining compute. | Gives a ready-made quantity to measure per checkpoint: does task training widen or close each model's gap? |
| **J1** ([2505.10320](https://arxiv.org/abs/2505.10320)), **JudgeLRM** ([2504.00050](https://arxiv.org/abs/2504.00050)), **V-STaR** ([2402.06457](https://arxiv.org/abs/2402.06457)) | RL-trained reasoning judges beat SFT judges; verifiers can be trained from a solver's own samples. | JUDGE training is feasible and well studied; these are baselines for how judges are trained, not transfer studies. |
| **MR-GSM8K** ([2312.17080](https://arxiv.org/abs/2312.17080)), **ProcessBench** ([2412.06559](https://arxiv.org/abs/2412.06559)) | Benchmarks for judging correctness and locating the first wrong step. | External JUDGE evaluation. ProcessBench's first-error-step format matches ours. |

### 2.2 Backward reasoning and abduction (precedents for RECONSTRUCT as a training signal)

| Work | Finding | What it means for us |
|---|---|---|
| **RevThink** ([Chen et al., NAACL 2025](https://aclanthology.org/2025.naacl-long.434/)) | Distilling forward reasoning + backward question generation + backward reasoning lifts Mistral-7B's 8-task average from 50.6 to 63.2. | Backward training helps forward reasoning, but the backward generator sees the original question, and backward is always mixed with forward. We isolate it. |
| **Absolute Zero** ([Zhao et al., 2025](https://arxiv.org/abs/2505.03335)) | RL self-play over three task types: deduction, abduction (infer an input from program + output), induction. Removing abduction/induction significantly drops math performance. | The strongest precedent that abduction matters for math transfer. But it is code, RL, self-proposed tasks, and ablation-only (no train-X-evaluate-Y matrix). Our natural-language, distribution-matched matrix is distinct. |
| **ALIVE** ([Duan et al., 2026](https://arxiv.org/abs/2602.05472)) | Unified posing, solving and judging with masked content in training. | The three-role combination is precedented; we cannot claim it. The distinction is the controlled matrix and matched information regimes. |
| **LogiDynamics** ([Zheng et al., EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1045/)) | Compares inductive vs abductive/deductive inference in a controlled environment. | Inference-time comparison, not training transfer. |
| Earlier RECONSTRUCT lineage | Blanking (Ranaldi & Pucci 2025), Trace Inversion (Gourabathina et al. 2026), Reverse QA (Balepur et al. 2025), FOBAR, Fill-in-the-Blank | See the [RECONSTRUCT review](../reconstruct/literature-review.md): the task itself is not new; the controlled sparse-evidence version and its use as a *training* signal are what we add. |

### 2.3 Cross-task and cross-domain transfer of reasoning training

| Work | Finding | What it means for us |
|---|---|---|
| **Does Math Reasoning Improve General Capabilities?** ([Huan et al., 2025](https://arxiv.org/abs/2507.00432)) | Across 20+ models, RL-trained math models transfer to other domains; SFT-trained ones mostly do not. SFT causes large drift in latent and output space; RL preserves feature geometry. | Two things. (1) We train only with on-policy distillation. Like RL, it learns from the student's own samples, so it may behave more like RL than SFT here. That is a hypothesis, not something these papers test, and there is no SFT or RL arm to compare against. (2) Their latent-drift and token-distribution analyses are tools we can reuse (section 5). |
| **Does Learning Math Problem-Solving Generalize?** ([2507.04391](https://arxiv.org/abs/2507.04391)) | Short-CoT instruction tuning gives limited or negative transfer; long CoT with self-reflection generalizes much better. | The *form* of the training traces matters as much as the task. Under OPD the traces are the student's own, so fix the maximum generation length across arms and report response lengths. |
| **GURU** ([2506.14965](https://arxiv.org/abs/2506.14965)) | 92K RL examples across six domains; training on each domain yields a different transfer profile over the others. | A published train-X-evaluate-Y matrix, but across *domains*. Ours varies the *reasoning regime* with the topic and difficulty distribution fixed. |
| **TAC curriculum** ([2606.25178](https://arxiv.org/abs/2606.25178)) | Uses gradient-cosine between domains as a transferability signal; reports math updates as idiosyncratic, weakly aligned with other domains. | Gradient alignment is a cheap predictor we can compute and test against our matrix. |
| **Exploring and Predicting Transferability** ([Vu et al., EMNLP 2020](https://aclanthology.org/2020.emnlp-main.635/)) | Transfer across 33 NLP tasks depends on data size and task similarity; task embeddings predict it. | Methodological ancestor of the transfer-matrix design. |
| **Learning Task Mixtures from Task Affinities** ([2507.12612](https://arxiv.org/abs/2507.12612)) | Models pairwise task affinities to choose SFT mixtures. | A way to predict mixture results from single-task results. |

### 2.4 Distillation and cross-model transfer

| Work | Finding | What it means for us |
|---|---|---|
| **Small Models Struggle to Learn from Strong Reasoners** ([Li et al., ACL Findings 2025](https://aclanthology.org/2025.findings-acl.1301/)) | Models of about 3B and below do not reliably benefit from long CoT distillation; mixing long and short chains helps. | Qwen3-4B sits near this boundary. Transfer may depend on student size, so size must be a factor, and teacher trace length matters. |
| **Not All Correct Answers Are Equal** ([Tian et al., 2025](https://arxiv.org/abs/2505.14464)) | With the same 1.89M queries, the teacher that generated the traces changes student results substantially. | Teacher identity is a variable. Holding the OPD teacher fixed is a control; varying it is an experiment. OPD needs a teacher that shares the student's tokenizer, so DeepSeek (used through the API) is the rater, not the teacher. |
| **Not All Synthetic Data Is Yours to Learn From** ([2605.31126](https://arxiv.org/abs/2605.31126)) | Synthetic data transfers best within the same model lineage; cross-family transfer is much worse; per-token likelihood and semantic similarity fail to predict which data helps. | Cross-model transfer of task data is not automatic. A second student family is needed to know whether our findings are about the tasks or about Qwen. |
| **Local naturalness for selecting teacher data** ([2510.03988](https://arxiv.org/abs/2510.03988)) | Selecting teacher traces that are locally natural to the student improves distillation. | Student-side perplexity is a candidate explanation for why a format distills well into one family and not another. |
| **Reasoning that Travels** ([2605.28913](https://arxiv.org/abs/2605.28913)) | Studies one model's chain-of-thought being used by another (provider → receiver); transfer mechanism is task-dependent. | Inference-time cross-model transfer; a template for our end-to-end chain analysis. |

### 2.5 Analysis methods used in these papers

| Method | Where used | What it tells you |
|---|---|---|
| Latent-space drift (PCA of hidden states before/after training) | Huan et al. 2025 | How much a task's training reshapes internal representations; SFT vs RL differ sharply. |
| Token-distribution shift (KL divergence, rank shift on held-out inputs) | Huan et al. 2025 | Whether training changes *what* the model says broadly or only on target inputs. |
| Gradient cosine between tasks | TAC 2026, GURU | Whether updates from task A point in the same direction as task B's; predicts transfer before training. |
| Task vectors (fine-tuned minus base weights) and their cosine | Task arithmetic literature | Weight-space similarity of what each task learned; overlap vs. orthogonality. |
| Update sparsity (fraction of parameters changed) | [RL finetunes small subnetworks, NeurIPS 2025](https://arxiv.org/abs/2505.11711) | RL changes 5–30% of parameters, SFT is dense; relates to forgetting and transfer. |
| Generation–verification gap | Song et al. 2025 | A single number per checkpoint linking SOLVE and JUDGE ability. |
| Rasch / item-response models | MathDuels 2026 | Separates item difficulty from model ability; good for comparing checkpoints on the same items. |
| Error taxonomies and behavior counts (verification phrases, backtracking, length) | CFT, self-verification, RevThink | Explains *how* behavior changed, not just whether accuracy did. |

## 3. Gaps and candidate novel contributions

Ranked by how defensible they are against the literature above.

1. **A distribution-matched on-policy-distillation transfer matrix across three information
   regimes, including abduction from sparse evidence.** Closest work either varies domains
   (GURU), pairs only two regimes (self-verification, CFT, GenRM), ablates task types without a
   full matrix (Absolute Zero), or mixes backward with forward training (RevThink). Holding the
   topic and difficulty distribution fixed, training with OPD, and crossing all three regimes
   with full train-X-evaluate-Y cells was not found. *Main contribution.* The task datasets use
   different questions, so claims are about regimes over matched distributions, not about the
   same problems presented three ways.
2. **Component-level transfer.** Existing papers report aggregate accuracy. Decomposing each
   target into its parts shows *which* skill moves. For JUDGE: verdict, localization,
   explanation. For RECONSTRUCT: fidelity vs validity. For SOLVE: error type. For example, "JUDGE
   training improves SOLVE only on self-checkable errors", or "RECONSTRUCT training improves
   JUDGE localization but not verdicts". *Strong insight value, low extra cost.*
3. **Task format as a distillation lever.** Same teacher, same problem distribution, three
   formats: which format transfers the teacher's knowledge best into a small student under OPD,
   and does the ranking change with student size? CFT shows critique beats imitation for one pair; the
   three-format comparison under a learnability-gap lens (2502.12143) was not found.
4. **Does the transfer structure survive a change of student?** Repeating the core matrix on a
   second model family tests whether transfer is a property of the *tasks* or of *Qwen*. Given
   the lineage-compatibility results (2605.31126), this is a genuine open question.
5. **Mechanistic prediction of the matrix.** Test whether gradient alignment, task-vector cosine
   or representation drift, all measured cheaply, predict the observed transfer matrix. Prior
   work uses these tools but not to explain regime-level transfer.
6. ~~**End-to-end chains.**~~ Dropped: E6 needs SFT on filtered samples, and the study uses OPD
   only.

**What not to claim:** the first answer-to-question task, the first solve/pose/judge
combination (ALIVE), the first generation–verification asymmetry result (self-verification),
or that critique beats imitation (CFT).

## 4. Research questions and experiments

Notation: M0 = the untrained student; M_S, M_J, M_R = students trained on one task; score_j =
the fixed metric for task j. Transfer Δ(i→j) = score_j(M_i) − score_j(M0), as in the study
framing. Always compare within a target column (same metric, same test set).

### E0 — Baselines (no training)
M0 on all three test sets; the OPD teacher on all three as an upper reference (DeepSeek
optionally as a second reference); an
answer-only RECONSTRUCT baseline and a full-solution RECONSTRUCT baseline (from the
RECONSTRUCT review). *Answers: where each model starts, how much headroom exists.*

### E1 — The core transfer matrix
Train M_S, M_J, M_R from the same checkpoint with reverse-KL on-policy distillation, using
the same teacher, the same hyperparameters, the same maximum generation length, and a
predeclared **budget** (optimizer steps or prompts processed). Each arm draws its prompts from
its own task's 3,600 training questions (`training.input`). Report student-generated and
teacher-scored tokens per arm, because response lengths differ by task. Evaluate each checkpoint
on all three 400-question test sets. At least 3 training seeds per cell.
*Answers RQ1: which directions transfer, and are they asymmetric?*

Include two controls, or the matrix cannot be interpreted:
- **Format-only placebo:** run OPD with the same budget on unrelated, non-mathematical
  instruction prompts. This separates "any distillation shifts outputs" from real transfer.
- **Format compliance:** report parse and format failures separately from reasoning scores,
  because a model trained on task A can fail task B's output format without being worse at the
  reasoning.

### E2 — Component decomposition (analysis on E1 outputs; no new training)
For every cell, break the target score into its parts:
- **JUDGE:** V, L, E, M, plus verdict accuracy split by correct vs incorrect solutions and by
  error position.
- **RECONSTRUCT:** premise and target fidelity vs evidence integration and mathematical validity.
- **SOLVE:** accuracy by topic and difficulty, plus an error taxonomy of wrong solutions.

Test the section 1 hypotheses directly. *Answers RQ2: which sub-skills move?*

### E3 — Mixtures (complementarity vs interference)
Train S+J, S+R, J+R and S+J+R at the same total budget as one single-task run. Compare each
target with its pure-task control at equal budget. *Answers RQ3: do tasks help each other when
combined, or crowd each other out?* If compute allows only one mixture, run S+J+R and restrict
the claim to "joint vs single".

### E4 — Distillation format (teacher knowledge in three formats)
The teacher's knowledge about the same problem distribution is delivered through its token-level
feedback on SOLVE, JUDGE or RECONSTRUCT rollouts. E1 already provides this comparison, because
all arms use one teacher. Optional factor:
- **Teacher identity:** a second teacher, which must also share the student's tokenizer, for one
  format.

*Answers RQ4: which format distills best, and why?* A candidate explanation is the initial
student–teacher reverse KL on each format's training prompts, which is the OPD analogue of the
local-naturalness line.

### E5 — Cross-model transfer (does the structure generalize across students?)
Repeat E0 + E1 (single tasks only, fewer seeds) on:
- **A smaller same-family model** (e.g. Qwen3-1.7B), to test size and learnability. It can
  reuse the same teacher.
- **A second family of similar size** (optional), e.g. a Llama-3.2-3B or Gemma-class model, to
  test task vs model. OPD then needs a teacher from that family with a shared tokenizer, so this
  also changes the teacher.

Report the matrix per student and a rank-correlation between matrices. *Answers RQ5: are
the transfer directions a property of the tasks?*

### E6, E7 — Dropped
The end-to-end filtering chain (E6) trained fresh students on filtered teacher samples, which is
SFT. The RL/GRPO arm (E7) is a second training method. The study uses OPD only, so both are out
of scope. Conclusions are therefore scoped to on-policy distillation.

## 5. Evaluation and analysis

### Metrics
| Task | Primary | Secondary | External check |
|---|---|---|---|
| SOLVE | Final-answer accuracy (deterministic check against the key) | Verified-reasoning rate (existing verifier), error type | MATH-500, GSM8K |
| JUDGE | Verdict accuracy; first-error-step accuracy (parsed, no model needed) | V/L/E/M rubric, 1–5 rating (as in the current JUDGE eval) | ProcessBench |
| RECONSTRUCT | Partial-credit score 0–100 (four dimensions) | Semantic recovery; grounded recovery; 1–5 rating | none exists; report answer-only and full-solution baselines |

Prefer metrics that need no model call (answer match, parsed verdict and step). They are
free, reproducible, and immune to judge drift. Use DeepSeek ratings where no deterministic
metric exists, and calibrate them once against a human-labeled sample.

The RECONSTRUCT recovery rate was about 2% for Qwen3-4B at baseline. At that level it cannot
show improvement, so the partial-credit score should be the headline RECONSTRUCT metric, with
recovery reported as secondary.

### Statistics
- **Test size:** with 400 test questions per task, a single rate near 50% is good to about ±5
  points (95% interval). A paired difference of about 6 points is detectable at 80% power,
  assuming two checkpoints disagree on about 20% of items. Transfer effects smaller than that
  need more seeds.
- **Uncertainty:** paired bootstrap over *test questions*, not over individual generations.
  McNemar's test for binary paired outcomes.
- **Main model:** a mixed-effects logistic regression with random effects for item and training
  seed and a fixed effect for the training condition, which pools seeds correctly.
- **Multiple comparisons:** the matrix has many cells, so correct across them (Holm) and
  preregister the section 1 hypotheses as the primary tests.
- **Ability vs difficulty (optional):** a Rasch model per task separates item difficulty from
  checkpoint ability.

### Mechanistic analysis (cheap, run on existing checkpoints)
1. **Gradient alignment:** at M0, average gradients on each task's training data and compute
   pairwise cosines. Does alignment predict the E1 matrix?
2. **Task-vector similarity:** cosine and principal-angle overlap between the weight updates
   (or adapters, if OPD uses LoRA) of M_S, M_J and M_R.
3. **Representation drift:** hidden-state PCA or CKA on each test set, before vs after
   training, as in Huan et al.
4. **Token-distribution shift:** KL divergence of next-token distributions on held-out inputs,
   to separate broad output change from targeted change.
5. **Latent verification probe:** a linear probe predicting "this solution is correct" from
   hidden states. Does SOLVE training create a latent verification signal that the model's
   JUDGE outputs fail to use? This is a concrete, testable version of the generation–verification
   gap.
6. **Behavior counts:** self-checking phrases, backtracking, and response length in SOLVE outputs
   per training condition.

## 6. What the current repository has, and what is missing

| Need | Status |
|---|---|
| SOLVE, JUDGE, RECONSTRUCT train/test | **Done:** [FINAL-v3](../../../data/manifests/final-v3/README.md), 3,600 / 400 per task. Different questions per task, matched on topic buckets and difficulty shares. Final; will not be regenerated. |
| Training targets | **Not needed for OPD.** Only `training.input` is used as a prompt. The stored chain-of-thought and target fields are unused for training. |
| Evaluation pipelines | SOLVE verifier exists; JUDGE evaluator exists (`scripts/evaluate_judge_qwen.py`); RECONSTRUCT judges exist. None is wired to the FINAL-v3 test files yet. |
| Fixed evaluation prompts | **Missing** for SOLVE and RECONSTRUCT: `training.input` has no instructions or output format. |
| Training code | **Missing:** an OPD runner (Turing cluster) with a teacher that shares the student's tokenizer, a fixed budget, and seeds |

The 78-item JUDGE set remains useful as an external JUDGE check alongside ProcessBench.

### Rough cost and scale

These are estimates to plan with, not measurements.
- **Data creation:** done (FINAL-v3).
- **Evaluation:** about $2–4 per checkpoint via DeepSeek, most of it RECONSTRUCT. E0–E3 on
  Qwen3-4B with 3 seeds is about 20–25 checkpoints, so about $50–100.
- **Training:** about 20–35 OPD runs on the Turing cluster, depending on how much of E3/E5 is
  run. Each OPD step needs student generation plus a teacher forward pass, so an OPD run costs
  more than an SFT run over the same number of prompts.

**Minimum viable paper:** E0 + E1 + E2 on Qwen3-4B with 3 seeds, plus the placebo control.
**Strong paper:** add E3 (all mixtures), E5 (a smaller Qwen3 student), and the mechanistic analyses.
**Extended:** E4 second teacher, E5 second family.

## 7. Threats to validity

- **Format learning masquerading as transfer.** Use the placebo control and report format
  failures separately.
- **Unequal training exposure.** Fix the OPD budget, and report prompts, unique questions,
  student-generated tokens and teacher-scored tokens per arm.
- **Different questions per task.** The tasks match on topic buckets and difficulty shares but
  not on items. Some row differences may come from the question sets rather than the task form.
  Report per-topic and per-difficulty results; JUDGE's topic mix is the least even.
- **Judge bias.** DeepSeek generated the RECONSTRUCT clues and also rates outputs. Calibrate
  against human labels, and prefer deterministic metrics.
- **Selection effects in data.** RECONSTRUCT gating changed the difficulty mix in v1. Stratified
  splits and per-stratum reporting keep this visible.
- **Small effects vs test size.** 400 items resolve roughly 6-point differences; do not
  interpret smaller ones without more seeds.
- **OPD-specific conclusions.** Transfer may differ under SFT or RL. Scope claims to on-policy
  distillation with the chosen teacher.
- **No development split.** Tune only on training questions; touching the test sets before the
  final evaluation invalidates them.

## 8. Suggested positioning

> We study how learning transfers across three mathematical reasoning regimes: constructing a
> solution from a problem, judging a supplied solution, and reconstructing a problem from sparse
> evidence. Each regime uses its own questions drawn from the same topic and difficulty
> distribution. Every model is trained with on-policy distillation under a matched budget. We
> measure the full train-by-evaluate matrix, decompose each effect into the sub-skill it
> changes, test whether the transfer structure holds across student sizes, and ask which task
> format best distills a teacher's knowledge into a small student.

## References (added in this review)

- Chen et al. 2026, Learning to Self-Verify Makes Language Models Better Reasoners — https://arxiv.org/abs/2602.07594
- Wang et al. 2025, Critique Fine-Tuning — https://arxiv.org/abs/2501.17703
- Zhang et al. 2024, Generative Verifiers — https://arxiv.org/abs/2408.15240
- Song et al. 2025, Mind the Gap (generation–verification gap), ICLR — https://arxiv.org/abs/2412.02674
- J1 2025 — https://arxiv.org/abs/2505.10320 ; JudgeLRM 2025 — https://arxiv.org/abs/2504.00050 ; V-STaR 2024 — https://arxiv.org/abs/2402.06457
- ProcessBench 2024 — https://arxiv.org/abs/2412.06559 ; MR-GSM8K — https://arxiv.org/abs/2312.17080
- Zhao et al. 2025, Absolute Zero — https://arxiv.org/abs/2505.03335
- Huan et al. 2025, Does Math Reasoning Improve General LLM Capabilities? — https://arxiv.org/abs/2507.00432
- Does Learning Mathematical Problem-Solving Generalize to Broader Reasoning? 2025 — https://arxiv.org/abs/2507.04391
- GURU 2025 — https://arxiv.org/abs/2506.14965 ; TAC 2026 — https://arxiv.org/abs/2606.25178
- Learning Task Mixtures from Task Affinities 2025 — https://arxiv.org/abs/2507.12612
- RL Finetunes Small Subnetworks in Large Language Models, NeurIPS 2025 — https://arxiv.org/abs/2505.11711
- Li et al. 2025, Small Models Struggle to Learn from Strong Reasoners, ACL Findings — https://aclanthology.org/2025.findings-acl.1301/
- Tian et al. 2025, Not All Correct Answers Are Equal — https://arxiv.org/abs/2505.14464
- Not All Synthetic Data Is Yours to Learn From 2026 — https://arxiv.org/abs/2605.31126
- Distilling Reasoning into Student LLMs: Local Naturalness 2025 — https://arxiv.org/abs/2510.03988
- Reasoning that Travels 2026 — https://arxiv.org/abs/2605.28913
- LogiDynamics, EMNLP 2025 — https://aclanthology.org/2025.emnlp-main.1045/
- Vu et al. 2020, Exploring and Predicting Transferability across NLP Tasks — https://aclanthology.org/2020.emnlp-main.635/
- Earlier RECONSTRUCT-lineage references: [literature-review.md](../reconstruct/literature-review.md), [references.bib](../reconstruct/references.bib)
