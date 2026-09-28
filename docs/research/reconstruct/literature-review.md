# RECONSTRUCT: literature and novelty assessment

Reviewed 19 September 2026. Scope: the proposed SOLVE / JUDGE / RECONSTRUCT study, especially inferring a mathematical question from its final answer and sparse, unordered solution evidence. This is a targeted narrative review of 23 relevant papers, not an exhaustive systematic review. Bibliographic metadata is maintained in [references.bib](references.bib); access depth and search limitations are in [source-log.md](source-log.md).

## Project framing and scope of this review

**The main project contribution is a controlled training-transfer study across SOLVE, JUDGE, and RECONSTRUCT.** The settings respectively require constructing a solution from a problem, evaluating supplied reasoning, and reconstructing a grounded problem from sparse evidence. We train on each setting and evaluate on all three to measure specialization, transfer, interference, and complementarity. See the [study framing](../../design/reasoning-transfer-study.md).

The clue-count/disclosure experiment supports a valid RECONSTRUCT condition within that larger study. It is not the main contribution. The original 23-paper search below primarily establishes the lineage of RECONSTRUCT; it cannot by itself settle novelty of the full training-transfer experiment. Two additional transfer-focused references are recorded below and in the bibliography.

## Novelty of the RECONSTRUCT component

**The broad RECONSTRUCT idea is not new.** Published work already reconstructs questions from worked answers, reconstructs queries from reasoning traces, and generates questions conditioned on answers and clues. Backward mathematical reasoning and problem generation are established research areas. In particular, Ranaldi and Pucci (2025), Gourabathina et al. (2026), and Balepur et al. (2025) must be treated as direct precedents.

**A supporting empirical contribution remains plausible:** mathematical question reconstruction under controlled partial solution evidence, measuring clue count, disclosure, and representation while separately evaluating evidence compatibility and original-question recovery. I did not identify that complete experimental combination in the inspected work. This is a provisional gap, not evidence of a first-ever task. Individual ingredients already have precedents. Established component tasks do not negate the contribution of a controlled study of transfer among them.

Calling the RECONSTRUCT skill **abductive mathematical inference under incomplete evidence** is appropriate: infer a plausible problem that explains the observations. Training and cross-task evaluation are central to the project. The three settings are operationally distinct; whether they rely on shared or different learned capabilities is a question for the experiment, rather than an assumption established by their names.

## Closest precedents

### 1. Exploring Backward Reasoning in Large Language Models

Ranaldi and Pucci, Findings NAACL 2025. Key: `ranaldi2025backward`. [Paper](https://aclanthology.org/2025.findings-naacl.366/).

Their Hiding task removes a value or concept from a question; Blanking removes the question and asks for reconstruction from an answer, including a worked chain-of-thought answer. Worked answers substantially assist reconstruction. The authors explicitly discuss critical question information appearing in the evidence. They use BERTScore and also GPT-4 judging, and acknowledge multiple valid questions. See task definitions, Section 6, and evaluation appendices.

**Implication:** question recovery, leakage concerns, and an LLM evaluator are already present. The possible extension is systematically restricted evidence, rather than complete worked answers. BERTScore values must not be reported as reconstruction accuracy.

### 2. Answering the Wrong Question: Reasoning Trace Inversion for Abstention in LLMs

Gourabathina et al., ACL 2026. Key: `gourabathina2026inversion`. [Paper](https://aclanthology.org/2026.acl-long.608/).

Trace Inversion infers a query using only a generated reasoning trace, then compares it with the actual query to support abstention. It outperforms competitive baselines in 33 of 36 model/dataset settings. Appendix B.4 explicitly prompts reconstruction of the initial question from the trace. The inspected method does not establish a controlled sparse-clue study.

**Implication:** “reasoning trace → hidden question” is directly precedented. Our distinguishing variable would be partial evidence and reconstruction quality, whereas their downstream objective is abstention.

### 3. Reverse Question Answering: Can an LLM Write a Question so Hard (or Bad) that it Can't Answer?

Balepur et al., NAACL 2025. Key: `balepur2025rqa`. [Paper](https://aclanthology.org/2025.naacl-short.5/).

RQA asks for a question whose answer is a supplied value. Across 16 LLMs, numerical-answer RQA is considerably harder than ordinary QA; textual-answer RQA is slightly easier. Models sometimes answer their own invalid generated questions correctly, suggesting generation errors cannot be explained solely by knowledge gaps. Multi-hop generation is difficult. Evaluation includes a human-checked LLM oracle.

**Implication:** open-ended answer-to-question generation and comparing forward/backward competence are established. RQA supplies an answer-only baseline; it does not require recovery of a particular hidden mathematical source.

### 4. Asking Questions the Human Way: Scalable Question-Answer Generation from Text Corpus

Liu et al., WWW 2020; ACS-QG. Key: `liu2020acs`. [Author PDF](https://www-labs.iro.umontreal.ca/~liubang/files/bliu-www20.pdf).

Generation conditions on a passage, answer, clue, and question style. The system addresses one-to-many question generation and produces 2.8 million QA pairs from one million Wikipedia sentences. It reports improvements in question-generation quality. The passage remains available to the generator.

**Implication:** answer-plus-clue conditioning itself is not new. Our input hides the source problem and deliberately withholds much of the solution, creating a different information constraint.

### 5. Math Word Problem Generation with Mathematical Consistency and Problem Context Constraints

Wang, Lan, and Baraniuk, EMNLP 2021. Key: `wang2021mwp`. [Paper](https://aclanthology.org/2021.emnlp-main.484/).

The generator receives an equation and contextual keywords; mathematical-consistency constraints and keyword selection improve mathematical validity and language quality across three datasets. It generates a story consistent with supplied mathematics.

**Implication:** mathematical question generation with semantic constraints is established. RECONSTRUCT should require inference about missing problem structure; supplying a complete defining equation can reduce it to this earlier task.

## Backward mathematics, verification, and training

| Paper and status | Findings and relationship to RECONSTRUCT |
|---|---|
| **Fill in the Blank: Exploring and Enhancing LLM Capabilities for Backward Reasoning in Math Word Problems** — Deb et al.; 2023 arXiv, 2024 workshop per IBM author record. `deb2023blank`. [Paper](https://arxiv.org/abs/2310.01991) | Given an incomplete question and its answer, recover missing information. Backward performance drops on GSM8K, SVAMP, and MultiArith. Rephrasing, tool-based methods, checking, and a verifier-assisted ensemble improve it. Most question structure remains visible, unlike full-question reconstruction. |
| **Forward-Backward Reasoning in Large Language Models for Mathematical Verification (FOBAR)** — Jiang et al., Findings ACL 2024. `jiang2024fobar`. [Paper](https://aclanthology.org/2024.findings-acl.397/) | Hides an original numerical condition, supplies a candidate answer, and checks whether the missing condition can be recovered. Combining forward and backward evidence improves verification on six datasets and three models. Relevant to validating candidates, but it does not infer an entirely hidden question. |
| **Large Language Models are Better Reasoners with Self-Verification** — Weng et al., Findings EMNLP 2023. `weng2023selfverify`. [Paper](https://aclanthology.org/2023.findings-emnlp.167/) | Uses candidate answers as conditions for backward verification and answer selection; reports improvements on arithmetic, commonsense, and logical reasoning. Supports consistency checking rather than source-question reconstruction. |
| **MetaMath: Bootstrap Your Own Mathematical Questions for Large Language Models** — Yu et al., ICLR 2024. `yu2024metamath`. [Paper](https://proceedings.iclr.cc/paper_files/paper/2024/hash/c400474e8a36d0812fdee52739288b12-Abstract-Conference.html) | Bootstraps questions through several transformations including backward reasoning. Reports MetaMath-7B scores of 66.5 on GSM8K and 19.8 on MATH. These are outcomes of the overall augmentation mixture, not isolated proof that sparse reconstruction improves reasoning. |
| **Reverse Thinking Makes LLMs Stronger Reasoners (RevThink)** — Chen et al., NAACL 2025. `chen2025revthink`. [Paper](https://aclanthology.org/2025.naacl-long.434/) | Distills forward reasoning, backward-question generation, and backward reasoning. Table 1 increases Mistral-7B's average across eight tasks from 50.55 to 63.23. Its backward-question generator sees the original question; it is not reconstructing a hidden source from sparse fragments. |
| **ReverseMath: Answer Inversion for Scalable and Verifiable Mathematical Problem Generation** — Zhao et al., May 2026 preprint. `zhao2026reversemath`. [Paper](https://arxiv.org/abs/2605.27709) | Converts a source numerical condition into a new target and the original answer into a known condition. Reports failures on reversed counterparts and improvements from RL augmentation. The known original question guides construction; this differs from the reconstruction student's input. |
| **RODA: Reverse Operation Based Data Augmentation for Solving Math Word Problems** — Liu et al., IEEE/ACM TASLP 2022, early online 2021. `liu2022roda`. [Paper](https://arxiv.org/abs/2010.01556) | Reverses mathematical operations to generate augmented problems and improves two problem solvers. Establishes older mathematical inversion/data-augmentation lineage; not an LLM partial-evidence benchmark. |

## Incomplete evidence, ambiguity, and clue presentation

| Paper and status | Findings and relationship to RECONSTRUCT |
|---|---|
| **Abductive Commonsense Reasoning** — Bhagavatula et al., ICLR 2020. `bhagavatula2020abduction`. [Paper](https://arxiv.org/abs/1908.05739) | Introduces abductive explanation selection and generation from observations. Its reported historical best selection accuracy was 68.9 versus 91.4 for humans. Establishes the underlying inference skill, but does not reconstruct mathematical questions. |
| **QuestBench: Can LLMs ask the right question to acquire information in reasoning tasks?** — Li, Kim, and Wang, NeurIPS 2025 Datasets and Benchmarks. `li2025questbench`. [Paper](https://arxiv.org/abs/2503.22674) | Models identify which missing information to request in underspecified constraint problems. Strong math performance coexists with roughly 40–50% accuracy on logic/planning settings. Includes math word-problem and equation representations. The output is a clarification request, not a recovered source question. |
| **TreeCut: A Synthetic Unanswerable Math Word Problem Dataset for LLM Hallucination Evaluation** — Ouyang, ACL 2025. `ouyang2025treecut`. [Paper](https://aclanthology.org/2025.acl-short.84/) | Removes necessary conditions using expression trees. Reports worst-case zero-shot hallucination rates of 64% for GPT-4o and 44% for o3-mini. Missing-condition position and problem complexity matter. Distinguish insufficient evidence to identify the original from an invalid reconstructed candidate. |
| **NSMQ Riddles: A Benchmark of Scientific and Mathematical Riddles for Quizzing Large Language Models** — Boateng et al., AIED 2026 acceptance stated on author arXiv record. `boateng2026nsmq`. [Paper](https://arxiv.org/abs/2605.07051) | Contains about 1,800 riddles with at least three progressively informative clues; earlier answers earn more points. Tested models trail the best student contestants. Clue amount and revealing specificity are already studied in adjacent tasks, though the target is an answer/entity rather than a whole mathematical question. |
| **Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design or: How I learned to start worrying about prompt formatting** — Sclar et al., ICLR 2024. `sclar2024format`. [Paper](https://proceedings.iclr.cc/paper_files/paper/2024/hash/6c0e99d736da621403018ca7b32b1a4d-Abstract-Conference.html) | Meaning-preserving prompt formats can produce large measured differences, with an extreme reported spread of 76 accuracy points for Llama-2-13B. Supports controlling representation and sampling multiple formats; does not predict the size of a Qwen effect here. |
| **Flaw or Artifact? Rethinking Prompt Sensitivity in Evaluating LLMs** — Hua et al., EMNLP 2025. `hua2025format`. [Paper](https://aclanthology.org/2025.emnlp-main.1006/) | Across seven models, six benchmarks, and twelve templates, rigid evaluation rules inflate measured format sensitivity; semantic judging reduces it. Our format experiment must distinguish mathematical performance from output-parsing artifacts. |
| **The Reversal Curse: LLMs trained on “A is B” fail to learn “B is A”** — Berglund et al., ICLR 2024. `berglund2024reversal`. [Paper](https://proceedings.iclr.cc/paper_files/paper/2024/hash/5178b2f2d7c44aa390c0777dc77b3f0c-Abstract-Conference.html) | Shows directional generalization failures for learned facts. The paper explicitly distinguishes facts supplied in context, where reversal can succeed. Useful background, but not direct evidence that reconstruction from visible clues is difficult. |

## SOLVE / JUDGE / RECONSTRUCT and evaluation reliability

| Paper and status | Findings and relationship to the project |
|---|---|
| **ALIVE: Awakening LLM Reasoning via Adversarial Learning and Instructive Verbal Evaluation** — Duan, Ye, and Zhao, February 2026 preprint. `duan2026alive`. [Paper](https://arxiv.org/abs/2602.05472) | Uses unified problem posing, solving, and judging, with masked logical content and verbal feedback in training. Reports reasoning and self-correction gains. The three-role framing is already present, although its posing task is not our sparse mathematical source reconstruction. |
| **MathDuels: A Self-Play Benchmark That Grows** — Xu et al., April 2026 preprint, revised August. `xu2026mathduels`. [Paper](https://arxiv.org/abs/2604.21916) | Evaluates adversarial problem authors and solvers with independent validation and a Rasch model. Across 19 models, authoring and solving abilities are partly decoupled. Supports measuring distinct competencies; does not establish novelty of a multi-role evaluation. Earlier versions circulated under a different subtitle. |
| **MR-GSM8K: A Meta-Reasoning Benchmark for Large Language Model Evaluation** — Zeng et al., 2023 arXiv, revised 2024; publication venue not established in this review. `zeng2023mrgsm8k`. [Paper](https://arxiv.org/abs/2312.17080) | Evaluates judgments of solution correctness, error localization, and explanations. Reports model gaps over 20 points despite closer ordinary GSM8K performance. Direct JUDGE precedent and motivation for studying task-level disagreement. |
| **MathFish: Evaluating Language Model Math Reasoning via Grounding in Educational Curricula** — Lucy et al., Findings EMNLP 2024. `lucy2024mathfish`. [Paper](https://aclanthology.org/2024.findings-emnlp.323/) | Studies curriculum alignment. In Table 3, GPT-4 rates 96% of its generated problems fully aligned, while teachers rate 52%. This concerns conceptual alignment, not reconstruction correctness, but cautions against assuming a model reliably judges shared mathematical structure without human calibration. |

## Additional precedents for the central transfer study

- **Learning to Self-Verify Makes Language Models Better Reasoners** — Yuxin Chen et al., February 2026 preprint. `chen2026selfverify`. [Paper](https://arxiv.org/abs/2602.07594). Reports asymmetric transfer: generation improvement does not bring corresponding self-verification improvement, while self-verification training improves generation. It also studies joint reinforcement learning. This is a close precedent for the SOLVE/JUDGE portion and the question of transfer direction. Abstract-level inspection; detailed protocol comparison remains necessary before a priority claim.
- **Exploring and Predicting Transferability across NLP Tasks** — Vu et al., EMNLP 2020. `vu2020transfer`. [Paper](https://aclanthology.org/2020.emnlp-main.635/). Studies transfer across 33 NLP tasks and identifies roles for data size, task/domain similarity, and complexity. Its intermediate-then-target fine-tuning protocol differs from directly evaluating a source-trained model on all target tasks. This is methodological lineage, not an identical mathematical study. Proceedings abstract and method excerpts inspected.

RevThink and ALIVE above also become central related work under this framing: their multi-objective training motivates checking exactly which source-to-target comparisons and budget controls they already report. A complete novelty assessment must compare their training protocols, not merely their task labels.

## What can be claimed?

| Proposed claim | Assessment |
|---|---|
| First answer-to-question task | Contradicted by RQA and older question generation. |
| First reconstruction of a hidden question from reasoning | Contradicted by Blanking and Trace Inversion. |
| First question generation from answers plus clues | Contradicted by ACS-QG, with different source context. |
| First backward mathematical reasoning evaluation | Contradicted by Fill in the Blank and other inverse tasks. |
| First solve/pose/judge combination | Unsafe in light of ALIVE; our task semantics still differ. |
| First use of LLM judging or tolerance for multiple questions | Unsafe; both have direct precedents. |
| Controlled sparse-evidence mathematical reconstruction study | Plausibly distinct in the reviewed set; needs precise comparison and actual results. |
| Clue count × disclosure × representation interaction study | A possible empirical contribution, not a new general inference paradigm. |
| Controlled training and cross-evaluation across SOLVE, JUDGE, and RECONSTRUCT on matched sources | The main proposed contribution. Novelty rests on the information regimes, full transfer analysis, controls, and findings; compare directly with verification-training and reverse-training work. |

Suggested positioning:

> We conduct a controlled study of learning and transfer across three mathematical reasoning settings: constructing solutions from problem statements, judging supplied solution information, and reconstructing problems from sparse solution evidence. Using matched source problems and controlled training budgets, we train on each setting and evaluate across all three to measure specialization, transfer asymmetry, and complementarity. A supporting clue study calibrates the evidence available for reconstruction.

This states an investigation without asserting unverified priority or outcomes.

## Changes the literature motivates in the experiment

1. **Include the nearest-prior baselines.** Answer only; complete worked solution with question hidden; random solution excerpts; and our controlled clue sets. A full-solution baseline connects to Blanking/Trace Inversion. Random excerpts test whether the clue-conversion procedure adds value beyond deletion.
2. **Keep validity and recovery separate.** The primary evidence-only judge sees answer, clues, and candidate question. It checks well-posedness, answer correctness, and substantive compatibility of the clues with a coherent solution. A separate source-aware comparison assesses recovery of mathematical structure. Alternative valid questions should not fail merely because they differ from the hidden original.
3. **Prevent easy output shortcuts in the rubric.** A question that states the supplied answer, asks a tautology, or appends clues irrelevantly must not receive full credit. Check that the clues play a substantive role in the candidate's mathematical problem, while allowing reasonable unspecified details.
4. **Study disclosure rather than asserting zero leakage.** Useful evidence necessarily reveals something. Distinguish intended constraints from direct question restatements, copied target clauses, and full defining equations. Use a small human audit and held-out development calibration. Clue count is not an information measure; one equation can reveal more than four broad sentences. Do not label specificity tiers as measured bits of information.
5. **Make the format comparison semantically controlled.** Render the same selected observations as mathematical fragments, ordinary sentence bullets, and a short paragraph; audit that wording has not added facts. Report length as well as clue count. Separate shuffled versus original ordering as an explicit control rather than silently mixing it with format.
6. **Calibrate DeepSeek judging independently.** Have humans score a stratified sample including valid alternatives, subtly inconsistent questions, and direct-answer shortcuts. Report agreement and disagreement categories. A teacher that generated clues should not be accepted as its own untested ground truth. Mask source identity and experimental condition in the compatibility pass.
7. **Do not select test data for a desired Qwen percentage.** A medium development-set score may help choose a usable operating point. Freeze conversion and thresholds before held-out evaluation; keep and report the full difficulty curve. If performance is high only when clues restate the source, report that rather than silently adjusting the test set.
8. **Make the transfer matrix the central experiment.** Train separate models on SOLVE, JUDGE, and RECONSTRUCT from the same initial checkpoint; evaluate each on all three held-out task forms. Compare against the unmodified checkpoint and then budget-matched mixtures. Split source problems before generating task variants so that no source crosses train/test through another task. Use paired source-level analyses and multiple training seeds. Restrict claims to the sampled topics and teacher-verified subset; repeated clue/seed variants are not independent mathematical problems.

No new model runs were performed for this review. It does not establish a training benefit, a target Qwen success rate, or validated DeepSeek scoring reliability.
