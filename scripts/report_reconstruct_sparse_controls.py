#!/usr/bin/env python3
"""Report completed sparse comparisons and preserve control adjudication limits."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'artifacts/reconstruct/followup-v2'


def main():
    result = json.loads((OUT / 'sparse-comparison.json').read_text())
    a = result['arms']['student_p1@base_sparse_2']
    b = result['arms']['student_p1@role_sparse_2']
    assert a['resolved']==b['resolved']==22
    effect = result['comparisons']['student_p1@role_sparse_2']['normalized_score_source_averaged']
    lines = ['# Sparse evidence +/- answer role: completed development comparison', '',
        'The two-observation condition passes disclosure audit on12/12 sources; adding the existing role cue passes on11/12. Source40 violates the no-number role rule. Both student conditions use exactly the same eleven common sources and two decoding seeds, fixed before inference. All44 responses now have judgments. Four technical judge failures were retried once without changing prompts or student outputs; original failures remain saved.', '',
        '| Outcome | Two observations | Same observations plus role |', '|---|---:|---:|',
        f'| Mean /100 | {a["mean_normalized_score_resolved"]:.2f} | {b["mean_normalized_score_resolved"]:.2f} |',
        f'| Source-bootstrap 95% interval | {a["normalized_score_complete_sources"]["source_bootstrap_95_interval"]} | {b["normalized_score_complete_sources"]["source_bootstrap_95_interval"]} |',
        f'| Grounded successes | {a["successes"]}/22 | {b["successes"]}/22 |',
        f'| Score bins0,1,2,3,4 | {a["score_histogram_0_to_4"]} | {b["score_histogram_0_to_4"]} |', '',
        f'Paired role-minus-no-role difference: {effect["mean_difference"]:.2f}/100, with interval {effect["source_bootstrap_95_interval"]}. There is no demonstrated benefit from adding the role cue. Do not promote that added complexity. The sparse no-role condition has one substantive success, independently checked in the [factorial case study](sparse-factorial-case-study.md), but this single family and seed do not establish a robust optimal clue count.', '',
        'Both means meet the requested difficulty band, yet most responses remain mathematically wrong. Task validity, distribution, and meaningful reconstructions remain separate from the mean. Sparse versus historical full-bank results are not a clean count-only contrast: the sparse composition reshuffles its selected base observations, and audit eligibility differs. A fresh nested-count study must preserve ordering and common source eligibility.', '',
        'Evidence: [analysis](sparse-comparison.json), [eligibility fixed before inference](sparse-eligibility.json), [raw run](sparse-role-study.json), [smoke checks](sparse-smoke-review.json). Adaptive D2 development only. No C outcomes were used.']
    (OUT / 'sparse-decision.md').write_text('\n'.join(lines)+'\n')

    run = json.loads((OUT / 'information-controls.json').read_text())
    rows = []
    for judgment in run['evaluations'].values():
        response = run['responses'][judgment['response_key']]
        if response['condition'] in ['answer_only','full_solution']:
            rows.append({'source':response['source_index'],'condition':response['condition'],
                         'score':judgment['output']['score'],'response_key':judgment['response_key']})
    assert len(rows)==8
    lines = ['# Matched information controls', '',
             '| Source | Answer only | Full solution |', '|---|---:|---:|']
    for source in [11,22,30,49]:
        pair = {r['condition']:r['score'] for r in rows if r['source']==source}
        lines.append(f'| {source} | {pair["answer_only"]} | {pair["full_solution"]} |')
    lines += ['', 'Scores are on the original0–4 rubric. All four answer-only questions have demonstrably wrong supplied answers: C(4,2)=6, the independent-set count on a path with five vertices is13, 2^3=8, and the count of multiples of3 in1..10 is3. The raw full-solution judgments give three successes in four examples.', '',
        'Source11 remains a wording-adjudication issue: the complete ratio list1:2 can describe exactly two gaps and therefore three divisors, which uniquely gives n=4. The judge instead demanded the original general ratio formulation. The original and an explicit three-divisor counterpart are being checked separately; do not silently replace its score.', '',
        'These controls support an information-availability bottleneck on these four chosen development examples. They do not establish direct SOLVE ability, training transfer, a population-wide effect, or that additional sparse clues necessarily help. Answer-only correctness would not count as evidence-grounded reconstruction.', '',
        'Evidence: [raw run](information-controls.json), [case export](information-control-cases.md), [boundary fixtures](../../../data/manifests/reconstruct-judge-production-development-v3.json).']
    (OUT / 'information-control-report.md').write_text('\n'.join(lines)+'\n')

    teacher = json.loads((OUT / 'teacher-reconstruction-probe.json').read_text())
    assert len(teacher['teacher_reconstructions'])==4
    references = {
        11: ('supported', 'With all positive divisors ordered, the gap bound gives k<4. Composite n requires k>=3, so n=p^2; p(p-1)=2(p-1) forces p=2. Divisors1,2,4 verify existence.'),
        22: ('supported', 'The exponents for primes2,3,5,7 are97,48,24,16, all at least the prime. At11 the exponent is9. These exhaust smaller primes and prove minimality.'),
        30: ('supported_alternative', 'Log z has a simple zero at1 since Log(1)=0 and Log prime(1)=1. Its squared reciprocal therefore has a pole of order2. The translation w=z-1 and both qualitative observations are grounded. This differs from the original function Log(z)/(z-1)^3 and is still a valid reconstruction.'),
        49: ('clue_violation', 'The positive recurrence a_(n+1)=a_n(1-a_n) decreases to0 and reciprocal increments tend to1, so n*a_n tends to1. But at the chosen r=1,p=0, F(x)-x=-x^2 has the same negative sign on both sides of0. The stated sign-change clue is false. Correct final answer does not establish grounded reconstruction.')}
    review = {'reviewer':'assistant mathematical review, not independent human labels',
              'scope':'four preselected development inputs; not a judge accuracy estimate or a held-out model benchmark',
              'model_and_compute_confounds':'DeepSeek uses reasoning; Qwen is non-thinking and differs in model size/runtime. This does not isolate either factor.',
              'cases':[]}
    for key,row in teacher['teacher_reconstructions'].items():
        status, certificate = references[row['source_index']]
        review['cases'].append({'source_index':row['source_index'],'record_key':key,
                               'review_status':status,'certificate':certificate})
    (OUT / 'teacher-probe-math-review.json').write_text(json.dumps(review,indent=2)+'\n')


if __name__ == '__main__':
    main()
