#!/usr/bin/env python3
"""Report amendment P without selecting successful seeds or hiding missing outputs."""
import json
from pathlib import Path

from analyze_reconstruct_followup import analyze
from anlp_project.reconstruct_gates import verify_response_bindings


def main():
    root = Path('artifacts/reconstruct/d3-v2')
    run = json.loads((root / 'prompt-diagnostic.json').read_text())
    arms = ['student_p10_recover_original@convert_p3', 'student_p11_inverse_example@convert_p3']
    result = analyze(run, 'reserve', arms, [0, 1],
                     run['metadata']['diagnostic_source_indices'], selection_policy='bank_order')
    result['scope'] = 'Amendment P: four fixed development families; eight planned responses per arm'
    evaluations = {v['response_key']: v for v in run['evaluations'].values() if v['prompt'] == 'evaluate_p2'}
    semantics = {v['response_key']: v for v in run['source_recovery'].values() if v['prompt'] == 'source_recovery_p2'}
    for case in result['cases']:
        key = case['response_key']
        response = run['responses'][key]
        case['judgment_bindings_verified'] = verify_response_bindings(
            key, response, evaluations.get(key, {}), semantics.get(key, {}),
            run['sources'][str(response['source_index'])])
        case['provisional_grounded_semantic_success'] = bool(
            case['success'] and case['source_recovery'] == 2 and case['judgment_bindings_verified'])
    lines = ['# Inverse-construction demonstration: amendment P', '',
             'Same ordered evidence and sampling; only the example package changes. Two seeds per family are repeated measurements. Missing outputs remain in the planned denominator. These are development results, not the 25-family confirmation.', '',
             '| Prompt | Scored / planned | Mean on resolved /100 | Grounded | Same original | Grounded semantic (provisional) |',
             '|---|---:|---:|---:|---:|---:|']
    for arm, row in result['arms'].items():
        cases = [c for c in result['cases'] if c['arm'] == arm]
        row['same_source_questions'] = sum(c['source_recovery'] == 2 for c in cases)
        row['provisional_grounded_semantic_successes'] = sum(c['provisional_grounded_semantic_success'] for c in cases)
        row['semantic_judgments_resolved'] = sum(c['source_recovery'] is not None for c in cases)
        lines.append(f"| {arm.split('@')[0]} | {row['resolved']}/{row['planned']} | {row['mean_normalized_score_resolved']} | {row['successes']} | {row['same_source_questions']} | {row['provisional_grounded_semantic_successes']} |")
    lines += ['', 'Paired comparisons and missingness bounds:', '',
              '```json', json.dumps(result['comparisons'], indent=2), '```', '',
              'Any provisional success still requires independent mathematical, semantic, and disclosure review before counting toward release. A mean in range alone cannot establish usefulness. Full conversion coverage is a separate unmet gate.', '',
              'Evidence: [raw responses, failures and judgments](prompt-diagnostic.json), [case-level analysis](inverse-example-analysis.json), [preregistration](../../../docs/plans/reconstruct-amendment-p.md).']
    (root / 'inverse-example-analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    (root / 'inverse-example-report.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(result['arms'], indent=2))


if __name__ == '__main__':
    main()
