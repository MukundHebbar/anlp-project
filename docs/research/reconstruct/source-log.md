# Source and search log

Date: 2026-09-19. Review: [literature-review.md](literature-review.md). Canonical metadata: [references.bib](references.bib).

This is a targeted literature/novelty audit. Search used web discovery followed by primary proceedings pages, author-hosted PDFs, arXiv records, and paper sections. It did not use a preregistered protocol or exhaustively screen every search hit. No citation-count ranking or formal quality score was applied. Secondary summaries were discovery aids only. “No matching study found” is bounded by this search, not a universal absence claim.

Search concepts covered answer-to-question generation, backward math reasoning, inverse math problems, question reconstruction from reasoning traces, sparse/partial reasoning clues, mathematical problem posing, abductive generation, missing-information benchmarks, clue disclosure, prompt representation, and LLM judge validity. Exact-title follow-ups and references in the closest papers expanded the set. Published versions replace earlier versions where identified; preprints are retained but labeled. Broader education research on human mathematical problem posing and general question-generation surveys were outside the detailed review, so this is not a complete history of problem posing.

The following source log records reading depth, status, and intended use. “Sections” means targeted method/results inspection, not a claim of line-by-line full-paper review. URLs resolve from the corresponding citation keys in references.bib and linked titles in the review.

| Citation key | Status verified | Access / evidence | Takeaway used |
|---|---|---|---|
| ranaldi2025backward | Findings NAACL 2025 | Proceedings + PDF task definitions, Section 6, judge appendices | Direct Blanking precedent; evidence disclosure and multiple-answer evaluation already discussed. |
| gourabathina2026inversion | ACL 2026 | Proceedings + PDF method, results, Appendix B.4 | Direct trace-to-query precedent; downstream abstention. |
| balepur2025rqa | NAACL 2025 | Proceedings + PDF task/evaluation/results sections | Answer-only open-ended generation and QA/RQA comparison. |
| liu2020acs | WWW 2020 | Author PDF architecture and data-generation sections | Answer/clue/style-conditioned generation with source passage visible. |
| wang2021mwp | EMNLP 2021 | Proceedings + PDF method and results | Equation/context-conditioned mathematical problem generation. |
| deb2023blank | Author record says ACL 2024 workshop; exact workshop unverified | arXiv and IBM author publication record | Missing-condition recovery from answer, distinct from hidden whole-question recovery. |
| jiang2024fobar | Findings ACL 2024 | Proceedings, primary project description and method excerpts | Backward recovery for candidate-answer verification. |
| weng2023selfverify | Findings EMNLP 2023 | Proceedings abstract; PDF downloaded, no detailed result audit | Backward self-verification; only broad reported findings used. |
| yu2024metamath | ICLR 2024 | Proceedings + primary PDF excerpts | Reverse augmentation is one component of a larger mixture. |
| chen2025revthink | NAACL 2025 | Proceedings + PDF objectives and Table 1 | Training on forward/backward objectives; source question is available. |
| zhao2026reversemath | 2026 arXiv preprint | arXiv + PDF/HTML method and verification sections | Numerical condition/answer inversion and augmentation. |
| liu2022roda | TASLP 2022; online 2021 | arXiv abstract and author institutional publication record | Earlier reverse-operation augmentation lineage. |
| bhagavatula2020abduction | ICLR 2020 | arXiv abstract, author record and primary project | Abductive selection and generation background. |
| li2025questbench | NeurIPS 2025 Datasets and Benchmarks | Proceedings + PDF task definitions/results | Information acquisition differs from ordinary solving. |
| ouyang2025treecut | ACL 2025 | Proceedings abstract | Removing necessary premises creates hallucination risk. |
| boateng2026nsmq | AIED 2026 acceptance per author arXiv comments | arXiv abstract/metadata | Progressive clues are an existing benchmark design. |
| sclar2024format | ICLR 2024 | Proceedings abstract | Meaning-preserving formatting can affect measured performance. |
| hua2025format | EMNLP 2025 | Proceedings abstract | Evaluation rules can exaggerate format effects. |
| berglund2024reversal | ICLR 2024 | Proceedings abstract | Learned-fact reversal is distinct from in-context reconstruction. |
| duan2026alive | 2026 arXiv preprint | arXiv + HTML method/appendix sections | Prior unified posing/solving/judging training. |
| xu2026mathduels | 2026 arXiv preprint, v3 August | arXiv abstract/metadata | Authoring and solving partly decouple; use current subtitle. |
| zeng2023mrgsm8k | arXiv 2023, revised 2024; venue unverified | arXiv abstract and primary repository description | Direct solution-judging benchmark precedent. |
| lucy2024mathfish | Findings EMNLP 2024 | Proceedings abstract + author PDF Table 3 | Human/model discrepancy in judging curricular alignment. |

Publication details requiring care:

- Trace Inversion is now an ACL 2026 proceedings paper, not merely its April preprint.
- MathDuels v3 is titled “A Self-Play Benchmark That Grows”; earlier searches returned “Evaluating LLMs as Problem Posers and Solvers.” These are not separate papers.
- “From Answers to Questions: A Study on Backward Reasoning in Large Language Models” appears to be an earlier version of the Hiding/Blanking work; it was not counted independently.
- For Fill in the Blank, [IBM's author record](https://research.ibm.com/publications/fill-in-the-blank-exploring-and-enhancing-llm-capabilities-for-backward-reasoning-in-math-word-problems) identifies a workshop paper on 11 August 2024. The bibliography cites the verifiable arXiv version and records that qualification.
- RODA's journal DOI is 10.1109/TASLP.2021.3126932, although its volume year is 2022.
- Unverified venue assignments were not inferred from third-party tables.

No published result in this log is a measurement of this project's Qwen3-4B / DeepSeek configuration. Findings about other tasks motivate controls; they do not validate the proposed rubric or predict its accuracy.

## Transfer-focused extension after scope clarification

The project contribution is training and cross-evaluation across SOLVE, JUDGE, and RECONSTRUCT. The original component-focused review was insufficient to assess that contribution. On the same date, additional discovery queries included `language models training transfer solving verification backward reasoning cross task study`, `"reasoning" "solving" "verification" "transfer" training inverse problems`, and exact-title follow-ups for the following primary records:

| Citation key | URL / status | Reading depth and takeaway |
|---|---|---|
| chen2026selfverify | https://arxiv.org/abs/2602.07594 — February 2026 preprint | Abstract/metadata: reports asymmetric generation/self-verification transfer and joint RL gains; close central-study precedent. |
| vu2020transfer | https://aclanthology.org/2020.emnlp-main.635/ — EMNLP 2020 | Proceedings abstract and method excerpts: broad task-transfer study; intermediate-then-target fine-tuning differs from the proposed direct cross-evaluation matrix. |

The bibliography now contains 25 entries. The three-task framing and experimental controls are in [reasoning-transfer-study.md](../../design/reasoning-transfer-study.md). A full method-level novelty audit of the transfer study is still distinct from this component-focused literature review.
