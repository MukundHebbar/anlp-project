#!/usr/bin/env python3
"""Report saved development calibration and role outcomes; makes no model calls."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/reconstruct/followup-v2'


def main():
    gold = json.loads((OUT / 'gold-development.json').read_text())
    rows = list(gold['judge_fixtures'].values())
    categories = sorted({r['category'] for r in rows})
    lines = ['# Judge development calibration', '',
             f'{sum(r["passed"] for r in rows)}/{len(rows)} saved fixtures satisfy their predefined expected labels/ranges.', '',
             '| Category | Agreement |', '|---|---:|']
    for category in categories:
        rr = [r for r in rows if r['category'] == category]
        lines.append(f'| {category} | {sum(r["passed"] for r in rr)}/{len(rr)} |')
    lines += ['',
        'This is development calibration, not held-out accuracy. Thirty cases are three edits of each of ten mathematical families; the other eleven are authored fixtures. Exact answer checks support the constructed arithmetic cases, but do not mechanically certify every judgment about clue grounding or proof sufficiency. Labels are assistant-authored with stated mathematical checks, not independent human review.', '',
        'Do not use 41 as an independent sample size for a near-perfect-accuracy confidence claim. Repeated related edits, simple controls, and evaluator development limit generalization. Production-output adjudication and fresh independent family validation remain required.', '',
        'Evidence: [raw judgments](gold-development.json), [fixture manifest](../../../data/manifests/reconstruct-judge-development-v2.json), and `scripts/build_reconstruct_gold.py`. Regenerate this report with `scripts/report_reconstruct_calibration.py`.']
    (OUT / 'gold-development-report.md').write_text('\n'.join(lines) + '\n')

    result = json.loads((OUT / 'role-comparison.json').read_text())
    role = 'student_p1@role_augmented'
    rows = result['cases']
    ids = sorted({r['source_index'] for r in rows if r['arm'] == role})
    baseline = [r for r in rows if r['arm'] == 'student_p1' and r['source_index'] in ids]
    candidate = result['arms'][role]
    effect = result['comparisons'][role]['normalized_score_source_averaged']
    lines = ['# Added answer-role cue: development decision', '',
        f'Only {len(ids)}/12 source banks passed the combined public-disclosure audit (58.3% coverage). Accepted source IDs: {ids}.', '',
        '| Outcome | Baseline on same accepted sources | Added role |', '|---|---:|---:|',
        f'| Mean /100 | {sum(r["score"]*25 for r in baseline)/len(baseline):.2f} | {candidate["mean_normalized_score_resolved"]:.2f} |',
        f'| Grounded successes | {sum(r["success"] for r in baseline)}/{len(baseline)} | {candidate["successes"]}/{candidate["resolved"]} |', '',
        f'Paired source-average difference: +{effect["mean_difference"]:.2f}/100; descriptive source-bootstrap 95% interval {effect["source_bootstrap_95_interval"]}. Seven sources, two seeds each; no fresh confirmation.', '',
        'Do not promote this complete-bank-plus-role policy: coverage is below the predeclared 80% goal. The two successes occur on one source family, so the intervention has not demonstrated broad usefulness. The score improvement is conditional on passing the audit; comparing it with the full twelve-source baseline would confound source selection. This experiment also adds information and tokens, so it cannot isolate the effect of role semantics.', '',
        'Rejected sources: 40 violates the no-number role rule; 105, 131, 134, and 144 expose the premise/target bundle or essentially complete solution under the public-only audit. These are teacher disclosure decisions with assistant review, not a measured independently validated auditor accuracy.', '',
        'Next hypothesis: orient the task while reducing redundant or overly revealing observations. First audit the baseline itself using the corrected public-only visibility boundary. Then compare globally specified sparse inputs on all preselected sources, preserving exclusion counts. Do not hand-edit clues to rescue individual Qwen failures.', '',
        'Evidence: [analysis](role-comparison.json), [raw records](role-study.json), [cases](role-cases.md), [audit review](audit-review.json).']
    (OUT / 'role-decision.md').write_text('\n'.join(lines) + '\n')

    if (OUT / 'revision-comparison.json').exists():
        result = json.loads((OUT / 'revision-comparison.json').read_text())
        revised = result['arms']['student_p8_revision']
        effect = result['comparisons']['student_p8_revision']['normalized_score_source_averaged']
        lines = ['# Two-call self-revision: development decision', '',
            'Twenty-four baseline drafts were submitted to local Qwen for revision without teacher feedback or private source information. Twenty-three outputs were parseable and judged; one malformed output remains unresolved. No poor mathematical response was retried.', '',
            f'Resolved mean: {revised["mean_normalized_score_resolved"]:.2f}/100. All-24 missing-score bounds: {revised["mean_normalized_score_all_planned_bounds"]}. Grounded successes: {revised["successes"]}/23 resolved, versus 2/24 baseline.', '',
            f'On the eleven source families with both seeds resolved, paired score change is +{effect["mean_difference"]:.2f}/100, with descriptive bootstrap interval {effect["source_bootstrap_95_interval"]}. Grounded-success outcomes do not change on those families. A zero-width bootstrap interval for identical observed binary differences does not establish population equivalence.', '',
            f'Mean completion tokens across both calls for parseable revisions: {revised["mean_pipeline_completion_tokens"]:.1f}, versus 198.4 for the single-call baseline. This excludes the unresolved revision from that mean and is not total experiment cost; its raw usage remains in revision-study.json. Prompt/input tokens and latency must also be considered for full compute accounting.', '',
            'Decision: do not promote self-revision on this evidence. The extra call produces no demonstrated grounded-success gain. Some answers become numerically compatible while observations remain decorative: source 73 fixes a_0=2 but does not connect the power-tower observation; source 134 names eight powers but leaves the removal-process observations unexplained. Source 105 recovers the question but gives a false enumeration. These are distinct failures that a more generous answer-only metric would conceal.', '',
            'Judge-field caveat: source 40 seed 0 is marked well_posed=false yet answer_correct=true because the judge imports the underlying quartic coefficient. The question as written does not determine that coefficient. The overall low score rejects it appropriately, but the isolated answer_correct diagnostic is unreliable here. Report well_posed AND answer_correct jointly and retain this disagreement for evaluator calibration.', '',
            'Evidence: [analysis](revision-comparison.json), [raw outputs, failures, and judgments](revision-study.json). Adaptive development only; no confirmation or equal-compute superiority claim.']
        (OUT / 'revision-decision.md').write_text('\n'.join(lines) + '\n')

    if (OUT / 'answer-last-comparison.json').exists():
        result = json.loads((OUT / 'answer-last-comparison.json').read_text())
        arm = result['arms']['student_p9_answer_last']
        effect = result['comparisons']['student_p9_answer_last']['normalized_score_source_averaged']
        lines = ['# Supplied answer last: development decision', '',
            f'All {arm["resolved"]}/24 outputs are judged. Mean {arm["mean_normalized_score_resolved"]:.2f}/100, with {arm["successes"]}/24 grounded successes. Baseline mean is 31.25, with 2/24 grounded successes.', '',
            f'Paired score change: {effect["mean_difference"]:.2f}/100; descriptive source-bootstrap 95% interval {effect["source_bootstrap_95_interval"]}. This small adaptive screen provides no reason to adopt the answer-last ordering. It does not prove the baseline globally superior.', '',
            'Only the placement of the final-answer line changes; clues, instruction, example, model, sampling, and evaluator are fixed. The candidate mean falls in the requested band, but the absence of grounded successes illustrates why that criterion alone is insufficient.', '',
            'Evidence: [analysis](answer-last-comparison.json), [raw run](answer-last-study.json). No confirmation sources were used.']
        (OUT / 'answer-last-decision.md').write_text('\n'.join(lines) + '\n')

    lines = ['# RECONSTRUCT evidence and decision index', '',
        'The requested difficulty endpoint is mean normalized score20–75/100, with an additional required gate of at least5/25 grounded semantic recoveries of the original question on valid non-leaking inputs. A mean in range does not establish either recovery or reliable evaluation.', '',
        '| Comparison | Evidence | Decision supported |', '|---|---|---|',
        '| Compact baseline vs field order, instruction, and two-example variants | [96-output matched screen](prompt-screen.md) | Retain compact prompt provisionally; no demonstrated improvement, no equivalence claim. |',
        '| Full bank plus answer-role cue | [Role decision](role-decision.md) | Reject promotion: only 7/12 accepted banks, and improvement is conditional on that subset. |',
        '| Two-call self-revision | [Revision decision](revision-decision.md) | No additional grounded successes on complete matched families; extra compute is not justified by this screen. |',
        '| Judge development fixtures | [Calibration](gold-development-report.md) | 41/41 development agreements; independent final reliability remains unverified. |',
        '| Judge diagnostic field review | [Mathematical reviews](revision-math-review.json) | Source40 answer_correct flag imports an unstated source fact; report jointly with well-posedness. |',
        '| Answer-last presentation | [Decision](answer-last-decision.md) | 23.96/100 and 0/24 grounded successes; no basis for adoption. |',
        '| Public-only baseline disclosure audit | [Validity sensitivity](baseline-validity-sensitivity.md) | 11/12 banks accepted; both baseline successes occur on the rejected bank. Baseline usefulness is unestablished. |',
        '| Two observations with/without role | [Completed comparison](sparse-decision.md) | Means29.55 vs26.14; no demonstrated role benefit. One substantive no-role success. |',
        '| Answer-only/full-solution controls | [Control report](information-control-report.md) | Information availability matters on four probes; one full-solution wording dispute remains. |',
        '| Source-blind teacher feasibility | [Mathematical reviews](teacher-probe-math-review.json) | Three supported constructions, including a valid alternative; one violates a sign-change clue. |',
        '| Fresh-source readiness | [D3 preflight](d3-source-preflight.json) | Eleven sources supported with stated domains; one unresolved source interpretation retained in coverage. |',
        '| D3 full-bank exposure | [Coverage](../d3-v1/full-bank-coverage.md) | Six of12 accepted; full-bank policy fails the coverage goal. |',
        '| Auditor reasoning budget | [Budget probe](../d3-v1/audit-budget-report.md) | Resolved rejection flips on repeat; larger cap does not establish greater accuracy. |',
        '| Semantic recovery calibration | [24 controls](../semantic-v1/report.md) | Both prompts separate same/not-same on all authored controls; no demonstrated candidate accuracy gain. |',
        '| Strict disclosure calibration | [Controls and production boundaries](../disclosure-v1/report.md) | Candidate public auditor passes18/18 clear controls; broader reliability and exact-input eligibility still require review. |',
        '| Revised disclosure/count feasibility | [Decision](../disclosure-v1/decision.md) | Five required prefixes rejected; at most6 common eligible families, below the registered8. Revise conversion before the sweep. |',
        '| Restricted-copy challenge | [Six-case smoke](../disclosure-v1/copy-smoke-report.md) | Copies all4 full original questions; neither sparse original. A different same-answer question is not semantic recovery. |',
        '| p2 versus p3 converter | [Matched audits](../d3-v2/converter-comparison.md) | Accepted3/12 versus6/12; neither reaches80% coverage. Content and clue counts both change. |',
        '| Explicit original-recovery instruction | [Amendment O](../d3-v2/prompt-alignment-report.md) | Neither prompt recovers an original in eight outputs; mean score alone is insufficient. |',
        '| Worked inverse-construction example | [Amendment P decision](../d3-v2/inverse-example-decision.md) | Zero grounded semantic successes from eight attempts; seven parseable. Exact counterexamples and raw failures are retained. |',
        '| Original-question local SOLVE control | [Raw four-family control](../d3-v2/local-solve-control.json) | Two of four final answers correct; answer checking alone does not validate proofs or isolate backend effects. |',
        '| Non-identifiability of a sparse input | [Continuity certificate](../d3-v2/source33-ambiguity-certificate.md) | Distinct essential premises can support the same observations and answer. This is a concrete ambiguity example, not a population estimate. |', '',
        'No task version is currently established as paper-ready or globally best. The strongest supported conclusion is that several plausible prompt-only changes did not demonstrate improved grounding in this small development screen. The next decision concerns evidence composition and disclosure, not another unmotivated wording change.', '',
        'Confirmation sources remain untouched. Source families, not individual seeds or perturbations, are the uncertainty unit. All accepted/rejected inputs and unresolved student outputs must remain in coverage accounting.', '',
        'Reproduce reports with `scripts/report_reconstruct_calibration.py`. Cost provenance: [deduplicated recorded usage](cost-ledger.json). Research procedure: [registered follow-up](../../../docs/plans/reconstruct-followup-controlled.md) and [autoresearch protocol](../../../docs/plans/reconstruct-autoresearch.md).']
    (OUT / 'evidence-index.md').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
