# SOLVE / JUDGE / RECONSTRUCT: literature review, gaps, and study plan

Written 2026-09-25. Extends the [RECONSTRUCT literature review](../reconstruct/literature-review.md)
(which covers RECONSTRUCT's lineage in depth) and the [study framing](../../design/reasoning-transfer-study.md).
This review focuses on the transfer question: which training transfers to what, and how it
interacts with distillation and cross-model transfer. It is a targeted narrative review of
roughly 25 additional papers found by web search on 2026-09-25, read at abstract/summary depth
unless stated; it is not a systematic review, and every "gap" below means "not found in this
search", not "proven absent".

## 1. What the three tasks are

All three tasks are built from the same kind of source: a math problem with a known answer and
a reference solution. They differ in what the model is given and what it must produce.

| | SOLVE | JUDGE | RECONSTRUCT |
|---|---|---|---|
| Given | Full problem | Full problem + a full candidate solution | Final answer + 4 sparse clues; problem hidden |
| Produces | A solution and answer | Verdict, first wrong step, explanation | A plausible question + justification |
| Information | Complete statement, no solution | Most: statement *and* a worked attempt | Least: fragments only |
| Reasoning direction | Forward (premises → answer) | Checking (verify each step) | Backward (answer + fragments → premises) |
| Core demand | Construction | Discrimination and localization | Abduction: grounded hypothesis generation |
| Failure mode | Wrong derivation | Accepting a flaw / inventing one | Inventing an unsupported or answer-copying question |

**How to read the three together.** They are three *information regimes* over the same
mathematics. JUDGE has the most information but needs the finest discrimination; SOLVE needs a
path to be constructed; RECONSTRUCT needs structure to be inferred from too little. A clean
study holds the mathematics fixed and varies only the regime, so any difference in transfer is
about the reasoning demand, not the topic.

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
| **Absolute Zero** ([Zhao et al., 2025](https://arxiv.org/abs/2505.03335)) | RL self-play over three task types: deduction, abduction (infer an input from program + output), induction. Removing abduction/induction significantly drops math performance. | The strongest precedent that abduction matters for math transfer. But it is code, RL, self-proposed tasks, and ablation-only (no train-X-evaluate-Y matrix). Our natural-language, content-matched matrix is distinct. |
| **ALIVE** ([Duan et al., 2026](https://arxiv.org/abs/2602.05472)) | Unified posing, solving and judging with masked content in training. | The three-role combination is precedented; we cannot claim it. The distinction is the controlled matrix and matched information regimes. |
| **LogiDynamics** ([Zheng et al., EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1045/)) | Compares inductive vs abductive/deductive inference in a controlled environment. | Inference-time comparison, not training transfer. |
| Earlier RECONSTRUCT lineage | Blanking (Ranaldi & Pucci 2025), Trace Inversion (Gourabathina et al. 2026), Reverse QA (Balepur et al. 2025), FOBAR, Fill-in-the-Blank | See the [RECONSTRUCT review](../reconstruct/literature-review.md): the task itself is not new; the controlled sparse-evidence version and its use as a *training* signal are what we add. |

### 2.3 Cross-task and cross-domain transfer of reasoning training

| Work | Finding | What it means for us |
|---|---|---|
| **Does Math Reasoning Improve General Capabilities?** ([Huan et al., 2025](https://arxiv.org/abs/2507.00432)) | Across 20+ models, RL-trained math models transfer to other domains; SFT-trained ones mostly do not. SFT causes large drift in latent and output space; RL preserves feature geometry. | Two things. (1) Our main arm is SFT, so modest transfer is the expected default; we should say so and ideally add a small RL arm. (2) Their latent-drift and token-distribution analyses are tools we can reuse (section 5). |
| **Does Learning Math Problem-Solving Generalize?** ([2507.04391](https://arxiv.org/abs/2507.04391)) | Short-CoT instruction tuning gives limited or negative transfer; long CoT with self-reflection generalizes much better. | The *form* of the training traces matters as much as the task. Trace length must be controlled or varied deliberately. |
| **GURU** ([2506.14965](https://arxiv.org/abs/2506.14965)) | 92K RL examples across six domains; training on each domain yields a different transfer profile over the others. | A published train-X-evaluate-Y matrix, but across *domains*. Ours varies the *reasoning regime* with content fixed. |
| **TAC curriculum** ([2606.25178](https://arxiv.org/abs/2606.25178)) | Uses gradient-cosine between domains as a transferability signal; reports math updates as idiosyncratic, weakly aligned with other domains. | Gradient alignment is a cheap predictor we can compute and test against our matrix. |
| **Exploring and Predicting Transferability** ([Vu et al., EMNLP 2020](https://aclanthology.org/2020.emnlp-main.635/)) | Transfer across 33 NLP tasks depends on data size and task similarity; task embeddings predict it. | Methodological ancestor of the transfer-matrix design. |
| **Learning Task Mixtures from Task Affinities** ([2507.12612](https://arxiv.org/abs/2507.12612)) | Models pairwise task affinities to choose SFT mixtures. | A way to predict mixture results from single-task results. |

### 2.4 Distillation and cross-model transfer

| Work | Finding | What it means for us |
|---|---|---|
| **Small Models Struggle to Learn from Strong Reasoners** ([Li et al., ACL Findings 2025](https://aclanthology.org/2025.findings-acl.1301/)) | Models of about 3B and below do not reliably benefit from long CoT distillation; mixing long and short chains helps. | Qwen3-4B sits near this boundary. Transfer may depend on student size, so size must be a factor, and teacher trace length matters. |
| **Not All Correct Answers Are Equal** ([Tian et al., 2025](https://arxiv.org/abs/2505.14464)) | With the same 1.89M queries, the teacher that generated the traces changes student results substantially. | Teacher identity is a variable. Holding the teacher fixed (DeepSeek) is a control; varying it is an experiment. |
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

1. **A content-matched transfer matrix across three information regimes, including abduction
   from sparse evidence.** Closest work either varies domains (GURU), pairs only two regimes
   (self-verification, CFT, GenRM), ablates task types without a full matrix (Absolute Zero), or
   mixes backward with forward training (RevThink). Holding the source problems fixed and
   crossing all three regimes with full train-X-evaluate-Y cells was not found. *Main
   contribution; defensible if content matching is real (see section 6).*
2. **Component-level transfer.** Existing papers report aggregate accuracy. Decomposing each
   target into its parts shows *which* skill moves. For JUDGE: verdict, localization,
   explanation. For RECONSTRUCT: fidelity vs validity. For SOLVE: error type. For example, "JUDGE
   training improves SOLVE only on self-checkable errors", or "RECONSTRUCT training improves
   JUDGE localization but not verdicts". *Strong insight value, low extra cost.*
3. **Task format as a distillation lever.** Same teacher, same problems, three formats: which
   format transfers the teacher's knowledge best into a small student, and does the ranking
   change with student family and size? CFT shows critique beats imitation for one pair; the
   three-format comparison under a learnability-gap lens (2502.12143) was not found.
4. **Does the transfer structure survive a change of student?** Repeating the core matrix on a
   second model family tests whether transfer is a property of the *tasks* or of *Qwen*. Given
   the lineage-compatibility results (2605.31126), this is a genuine open question.
5. **Mechanistic prediction of the matrix.** Test whether gradient alignment, task-vector cosine
   or representation drift, all measured cheaply, predict the observed transfer matrix. Prior
   work uses these tools but not to explain regime-level transfer.
6. **End-to-end chains.** Does a student trained on JUDGE become a better filter or teacher for
   another model's SOLVE data? This links transfer to a practical pipeline (section 4, E6).

**What not to claim:** the first answer-to-question task, the first solve/pose/judge
combination (ALIVE), the first generation–verification asymmetry result (self-verification),
or that critique beats imitation (CFT).

## 4. Research questions and experiments

Notation: M0 = the untrained student; M_S, M_J, M_R = students trained on one task; score_j =
the fixed metric for task j. Transfer Δ(i→j) = score_j(M_i) − score_j(M0), as in the study
framing. Always compare within a target column (same metric, same test set).

### E0 — Baselines (no training)
M0 on all three test sets; the teacher (DeepSeek) on all three as an upper reference; an
answer-only RECONSTRUCT baseline and a full-solution RECONSTRUCT baseline (from the
RECONSTRUCT review). *Answers: where each model starts, how much headroom exists.*

### E1 — The core transfer matrix
Train M_S, M_J, M_R from the same checkpoint with the same method (LoRA SFT), the same
hyperparameters, and a matched **training-token budget** (not example count; task lengths
differ). Evaluate each on all three tests. At least 3 training seeds per cell.
*Answers RQ1: which directions transfer, and are they asymmetric?*

Include two controls, or the matrix cannot be interpreted:
- **Format-only placebo:** train on the same token count of unrelated, non-mathematical
  instruction data. This separates "any fine-tuning shifts outputs" from real transfer.
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
The teacher's knowledge about the same problems is delivered as SOLVE traces, JUDGE critiques,
or RECONSTRUCT completions. E1 already provides this comparison if all training data comes
from one teacher. Add two factors:
- **Trace length:** short vs long teacher traces for the SOLVE format, testing the learnability
  gap on a 4B model.
- **Teacher identity (optional):** a second teacher for one format.

*Answers RQ4: which format distills best, and why?* Use student perplexity on each format's
training data as a candidate explanation (local-naturalness line).

### E5 — Cross-model transfer (does the structure generalize across students?)
Repeat E0 + E1 (single tasks only, fewer seeds) on:
- **A second family of similar size,** e.g. a Llama-3.2-3B or Gemma-class model, to test task
  vs model.
- **A smaller same-family model** (e.g. Qwen3-1.7B), to test size and learnability.

Report the matrix per student and a rank-correlation between matrices. *Answers RQ5: are
the transfer directions a property of the tasks?*

### E6 — End-to-end distillation chain
A practical pipeline test:
1. DeepSeek generates SOLVE samples for training problems.
2. Candidate filters decide which samples to keep: none, the answer key, M0 as a judge, M_J as a
   judge, and M_R-as-judge.
3. A fresh student is trained on each filtered set.
4. Everything is evaluated on SOLVE.

*Answers: does a model trained on JUDGE (or RECONSTRUCT) become a useful component in
another model's training?* This is where "cross-model transfer, end to end" becomes concrete:
the transfer is measured through a second model's learning, not just the first model's scores.

### E7 — Optional: RL arm
Huan et al. report that RL transfers where SFT does not. A small GRPO run on SOLVE (answer
reward) and JUDGE (verdict/step reward) for M0 would show whether the E1 conclusions depend on
the training method. RECONSTRUCT has no cheap verifiable reward, which is itself worth noting.
Run only if compute remains after E1–E5.

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
- **Test size:** with 500 test sources per task, a single rate is good to about ±4 points; a
  paired difference of about 5–6 points is detectable at 80% power (assuming two checkpoints
  disagree on about 20% of items). Transfer effects smaller than that need more test items or
  more seeds.
- **Uncertainty:** paired bootstrap over *source problems*, not over individual generations.
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
2. **Task-vector similarity:** cosine and principal-angle overlap between the LoRA updates of
   M_S, M_J and M_R.
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
| RECONSTRUCT train/test inputs | **Done:** v1.2, 3,500 / 500, stratified |
| RECONSTRUCT training targets | **Missing:** validated completions from public inputs only (SKILL.md §8) |
| SOLVE train/test on the **same** 5,000 sources | **Missing.** Existing SOLVE runs used the separate 113/146-problem pilot pool, which the RECONSTRUCT pool excludes. DeepMath provides `r1_solution_1` for every source, a candidate SOLVE target, but it is long CoT and needs a length decision (E4). |
| JUDGE train/test on the same sources | **Missing.** The 78-item JUDGE set is test-only, and **0 of its 78 problems are in the RECONSTRUCT pool**. JUDGE items (correct and flawed solutions with labeled first errors) must be built for the same 3,500 train / 500 test sources. |
| Evaluation pipelines | SOLVE verifier exists; JUDGE evaluator exists (`scripts/evaluate_judge_qwen.py`); RECONSTRUCT judges exist |
| Training code | **Missing:** a LoRA SFT runner (Turing cluster) with token-budget matching and seeds |

**Content matching is the most important item.** Without SOLVE and JUDGE items built from the
same sources as RECONSTRUCT, the study cannot separate "which regime" from "which problems", and
the core contribution in section 3 does not hold. The 78-item JUDGE set remains useful as an
external JUDGE check alongside ProcessBench.

### Rough cost and scale

These are estimates to plan with, not measurements.
- **Data creation:** SOLVE targets from DeepMath (free) or regenerated shorter (about $7);
  JUDGE train items (generate plus audit, about $15–25); RECONSTRUCT targets (about $15–30).
- **Evaluation:** about $2–4 per checkpoint via DeepSeek, most of it RECONSTRUCT. E0–E3 on
  Qwen3-4B with 3 seeds is about 20–25 checkpoints, so about $50–100.
- **Training:** about 20–35 LoRA runs of a few thousand examples each on the Turing cluster,
  depending on how much of E3/E5 is run.

**Minimum viable paper:** E0 + E1 + E2 on Qwen3-4B with 3 seeds, plus the placebo control.
**Strong paper:** add E3 (all mixtures), E5 (one second family), and the mechanistic analyses.
**Extended:** E4 trace-length, E6, E7.

## 7. Threats to validity

- **Format learning masquerading as transfer.** Use the placebo control and report format
  failures separately.
- **Unequal training exposure.** Match training tokens, and also report example counts and
  unique sources.
- **Judge bias.** DeepSeek generated the RECONSTRUCT clues and also rates outputs. Calibrate
  against human labels, and prefer deterministic metrics.
- **Selection effects in data.** RECONSTRUCT gating changed the difficulty mix in v1. Stratified
  splits and per-stratum reporting keep this visible.
- **Small effects vs test size.** 500 items resolve roughly 5–6-point differences; do not
  interpret smaller ones without more seeds or items.
- **SFT-specific conclusions.** Transfer may differ under RL (Huan et al.); scope claims to SFT
  unless E7 is run.

## 8. Suggested positioning

> We study how learning transfers across three mathematical reasoning regimes: constructing a
> solution from a problem, judging a supplied solution, and reconstructing a problem from sparse
> evidence. The source problems are held fixed across regimes and training budgets are
> matched. We measure the full train-by-evaluate matrix, decompose each effect into the sub-skill
> it changes, test whether the transfer structure holds across student models, and ask which
> task format best distills a teacher's knowledge into a small student.

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
