# RECONSTRUCT-PC v1: partial-credit specification

Status: specified for prospective calibration, not empirically validated. This is a new scoring version; do not relabel historical0–4 results as results under this rubric. The existing one-gap/formula condition remains a constrained baseline.

Judge implementation update: use [PC-v4 and the verified certificate validator](JUDGE_VERIFICATION.md) for new partial-credit scoring. Score weights/bands remain unchanged. The19-case development calibration fixes the observed boundaries but does not validate the new converter/student distribution or guarantee unseen judge accuracy.

## Task

Given a final answer and partial supported observations, reconstruct one plausible original mathematical question and briefly verify how its premises, requested quantity and solution explain that evidence.

The intended skill is abductive reconstruction under incomplete information: infer missing structure, choose a target, and check the resulting question. Sparse observations need not uniquely identify the source. A mathematically sound alternative earns consistency/validity credit without automatically receiving source-recovery credit.

The question must stand alone. Inferred premises must appear in it; a value mentioned only in assumptions or justification does not silently repair it. Equivalent formulations, redundant valid premises and reparameterizations are accepted when they preserve the mathematical problem. A changed requested unknown is not equivalent merely because its answer coincides.

## Student interface

Public input contains only the final answer and numbered ordinary-sentence observations; equations may appear inside sentences. No source question, full worked solution, source ID, subject label, difficulty label or private conversion certificate is shown.

Output:

```json
{
  "assumptions": ["Brief inferred premises and why they fit the evidence"],
  "question": "One complete mathematical question",
  "justification": "A concise verification connecting the question, observations and supplied answer"
}
```

This requests a brief mathematical explanation, not private internal deliberation. Use one fixed few-shot student prompt and one primary draw per example. The established original Qwen3-4B Q4_K_M/nonthinking configuration and8192-token cap remain the baseline for comparability; they are not claimed optimal.

## Fixed conversion and exposure

One frozen few-shot converter produces an ordered bank of six supported observations, with a coherent four-observation core and two optional additions. Do not impose a separate hand-written transformation for each topic. Clues may convey setup, a relationship, a partial intermediate result or a broad target cue. The converter preserves enough distinguishing structure to make reconstruction plausible while withholding an essential question element, which may be a premise, parameter, relation or exact target.

Unlike the constrained baseline, always preserving the exact target and hiding only one number is not required. Do not routinely expose a complete parameter-to-answer formula: retain that as the separately labeled high-information baseline.

Prespecified exposures are sparse=first3, intermediate=first4, rich=all6. Intermediate is the initial default, chosen for a manageable starting point, not because four clues have been proved optimal. Every exposure is audited independently; passing a six-clue audit does not certify a three-clue input. Sentence count is a manipulation of exposure, not an information-theoretic measurement. Do not pad a bank just to reach six: return NOT_SUITABLE when the source cannot support the format.

Source support and an inverse/reconstruction certificate are private. The certificate identifies what is withheld, demonstrates that the original is compatible with the public answer and clues, and describes plausible alternatives. It does not claim uniqueness without proof. Never include that certificate in the student prompt.

Choose one exposure policy globally on development data, then freeze it for fresh evaluation. Do not add clues to individual test examples until the student succeeds or select a different policy per source after seeing its score. If later using a mixture of exposure levels, predeclare its allocation independently of student outcomes and report each level separately.

## Four dimensions, each0–4

The source-aware fidelity judge scores P and T from the original and candidate questions. It cannot import missing candidate premises from the student's explanation. The source-blind validity judge scores E and M using only public input and the response. Separate calls prevent the reference solution from silently supplying mathematical work to the validity judge.

| Dimension |0|1|2|3|4|
|---|---|---|---|---|---|
| P: premise fidelity |No meaningful correspondence|Objects/topic overlap, essential setup largely different|Important original structure retained, essential premise(s) missing or changed|Most setup retained; one localized, material error/omission|Essential objects, premises, parameters, domains and quantifiers equivalent|
| T: target fidelity |No identifiable or unrelated target|Related objects but fundamentally different requested result|Same target family, different quantity/event/direction|Same quantity but a limited material scope/qualification error|Same mathematical target, up to equivalence|
| E: evidence integration |Evidence ignored or predominantly contradicted|Mentions clues without a usable connection|Substantively uses some clues; important gaps or conflicts remain|All clues connected, with one limited unsupported link|Every clue substantively fits one coherent reconstruction, with links explained|
| M: mathematical validity |No meaningful verification or only circular assertions|Substantive attempt with demonstrably wrong answer, ill-posedness or false essential mathematics|Plausible route, but an essential mathematical gap leaves correctness unsupported|Correct answer and sound argument with a minor omitted step|Well-posed question, independently correct answer and sufficient sound verification|

These dimensions describe different aspects, not statistically independent capabilities. P/T measure fidelity to the source; E/M measure whether the candidate is grounded and mathematically viable. A valid alternative may score highly on E/M and lower on P/T. Do not erase that useful distinction.

An essential premise missing from the candidate cannot receive P4. An unresolved free parameter that changes the answer makes the question ill-posed, not merely an incomplete proof. A correct final number does not excuse false proof steps. Inferring a missing premise from the supplied answer is legitimate; putting the requested answer into the reconstructed question as a premise is a shortcut.

Judges must cite concrete correspondences, student/public spans and mathematical reasons. If a judge cannot resolve a dimension, return null/needs_review, not an invented middle score. Do not score style, length, confident wording or topic vocabulary.

## Aggregation and exceptions

Current display policy: `RECONSTRUCT-RATING-v4` supersedes v3. Cutoffs are18.75,43.75,56.25,75; apply `balanced_rating_v4(score_100)` after aggregation. Only the2/3 cutoff increases from37.5 to43.75, moving six tied responses from3 to2. The47 scored responses now have counts3,12,18,12,2. This is a user-requested post-hoc development calibration; numerical scores, judgments, gates and success labels remain unchanged. Bands are no longer equally spaced. Historical versions remain available; the results below retain their original scale. Freeze before fresh evaluation and disclose the adaptation history rather than claiming Gaussian scores or improved performance. [Updated ratings and provenance](../../../artifacts/reconstruct/balanced-ratings-v4/report.md).

Use equal weights initially:

    partial_credit_100 = 6.25 * (P + T + E + M)

Equal weighting is a transparent design choice awaiting calibration, not an empirically optimized hyperparameter. Keep the complete dimension vector alongside the total. The LLM assigns dimension labels; deterministic code must calculate the total.

Display bands, if a1–5 histogram is needed:1=[0,20),2=[20,40),3=[40,60),4=[60,80),5=[80,100]. This display convention is NEW and not the old stored-score-plus-one mapping. Display5 means high aggregate partial credit, not automatically full recovery. Always retain the exact0–100 score.

Known shortcuts—asking for an already supplied answer, copying a complete public assertion without substantive reconstruction, or giving no usable question—receive final task score0. Preserve any dimension assessments as diagnostics and record the override reason; do not rewrite the raw judge outputs. A bad but substantive reconstruction keeps its earned partial credit.

If an input leaks the question, contains unsupported clues or exposes the complete solution, mark the item invalid. Do not score that as a student failure; retain it in conversion-coverage and allocated-source denominators. If a judge is unavailable or uncertain, keep scores missing and report bounds. A known absent/unusable student response is a failed student attempt; transport failure is separate and must not silently become a model-quality score.

## Strict success remains separate

Full grounded semantic recovery requires valid input, P4, T4, E4, M>=3, no shortcut, explicit source equivalence and checked mathematics. No threshold on the total alone defines success. For example, high partial credit on a valid alternative is not original recovery. Grade partial performance and report this binary flag side by side.

The converter, leakage reviewers and judges may all use DeepSeek in separate calls, but that is not independent human validation. Preserve disagreements and mathematical adjudications. The previous factorial-root false rejection must be included as a calibration control for legitimate answer-conditioned inverse inference.

## Leakage gates

1. Check each clue against the verified source and mathematical support.
2. Compare the exact combined public answer/clues against the original: reject full premise-target disclosure, disguised missing values, and complete worked solutions.
3. Run a public-only copying challenge restricted to copying/paraphrase, with no new premise or mathematical inference. Inspect proposed shortcuts, including ones producing a different trivial question with the same answer.
4. Review every apparent full success and all gate disagreements. Bind every decision to the actual rendered input and response hashes.

Known source features may be exposed. Recoverability through genuine inverse inference is the task, not itself a leak. These fallible checks reduce leakage risk; they do not certify its absolute absence. High exposure and complete disclosure must remain distinct recorded labels.

## Illustrative anchors, not measured results

For source “rectangle perimeter20, area24; find longer side,” answer6 and clues about side sum10, product relation and longer-side target:

- Correct equivalent question plus valid factorization: P4,T4,E4,M4 =>100; strict success if input gates pass.
- Same rectangle premises but asks for the shorter side, correctly derives4 and notices the supplied6 mismatch: P4,T2,E3,M1 =>62.5; meaningful partial recovery, not success.
- Omits area24 and asks for the longer side with perimeter20 alone: P2,T4,E2,M1 =>56.25; the original target is recovered, but the question is underdetermined.
- “A rectangle's longer side is6. What is its longer side?”: answer-copy shortcut, final0 regardless of superficial overlap.

These anchors explain intended distinctions. They must be independently checked and expanded before becoming validation gold. Do not treat an example's reference vector as universally applicable to every response of that broad type.

## Calibration and adoption

First apply the new rubric to saved responses, covering exact successes, wrong targets, omitted premises, valid alternatives, incorrect mathematics, answer-copy shortcuts and the known verifier errors. Use the same frozen response set for judge comparisons. Have independent reviewers check anchors, all disagreements and representative middle scores. Measure ordinal agreement and false full-success decisions, not just whether the histogram looks attractive.

Only after measurement is usable, compare3/4/6-clue exposures on the same source families with one fixed student prompt. Keep the former one-gap/symbolic-formula condition as a baseline. Report P/T/E/M, total, strict success, leakage/coverage and missingness by arm; report uncertainty at the source-family level.

Select intermediate exposure for meaningful partial reasoning and an interpretable strict-success rate, not to force more3s. Freeze prompts, weights, exposure policy and source-family allocation before untouched confirmation. Do not claim Gaussian ratings,20–40% general recovery, nearly perfect teacher accuracy or cross-task training transfer from this specification.

Prompts: [converter](../../../data/prompts/reconstruct/partial_credit_v1/convert.md), [student](../../../data/prompts/reconstruct/partial_credit_v1/student.md), [fidelity judge](../../../data/prompts/reconstruct/partial_credit_v1/judge_fidelity.md), [validity judge](../../../data/prompts/reconstruct/partial_credit_v1/judge_validity.md). They are specification templates; the old runtime runners do not yet implement this scoring schema.
