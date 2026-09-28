#!/usr/bin/env python3
"""Reproduce amendment O's paired results and semantic endpoint separately."""
import json
from pathlib import Path
from analyze_reconstruct_followup import analyze
from anlp_project.reconstruct_gates import verify_response_bindings


def main():
    root=Path('artifacts/reconstruct/d3-v2')
    run=json.loads((root/'prompt-diagnostic.json').read_text())
    arms=['student_p1@convert_p3','student_p10_recover_original@convert_p3']
    indices=run['metadata']['diagnostic_source_indices']
    result=analyze(run,'reserve',arms,[0,1],indices,selection_policy='bank_order')
    result['scope']='Four preregistered D3 development families, drawn earlier from reserve; not held-out confirmation'
    evaluations={x['response_key']:x for x in run['evaluations'].values() if x['prompt']=='evaluate_p2'}
    semantics={x['response_key']:x for x in run['source_recovery'].values() if x['prompt']=='source_recovery_p2'}
    for case in result['cases']:
        key=case['response_key'];response=run['responses'][key]
        case['judgment_bindings_verified']=verify_response_bindings(key,response,evaluations.get(key,{}),
            semantics.get(key,{}),run['sources'][str(response['source_index'])])
        case['provisional_grounded_semantic_success']=bool(case['success'] and case['source_recovery']==2
                                                          and case['judgment_bindings_verified'])
    for arm,row in result['arms'].items():
        cases=[c for c in result['cases'] if c['arm']==arm]
        row['semantic_score_histogram_0_to_2']=[sum(c['source_recovery']==i for c in cases) for i in range(3)]
        row['same_source_questions']=sum(c['source_recovery']==2 for c in cases)
        row['provisional_grounded_semantic_successes']=sum(c['provisional_grounded_semantic_success'] for c in cases)
    (root/'prompt-alignment-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Original-recovery instruction: four-family diagnostic','',
      'Same fixed p3 evidence, local non-thinking Qwen3-4B Q4_K_M, seeds0/1, and8192 cap. Only the instruction paragraph differs; the example and schema are identical. These16 outputs are eight per prompt, not16 independent source families.','',
      '| Prompt | Judged | Mean /100 | Grounded rubric successes | Same source questions | Grounded semantic successes |',
      '|---|---:|---:|---:|---:|---:|']
    for arm,r in result['arms'].items():
        mean=r['mean_normalized_score_resolved']
        lines.append(f'| {arm.split("@")[0]} | {r["resolved"]}/{r["planned"]} | {mean:.2f} | {r["successes"]}/{r["planned"]} | {r["same_source_questions"]}/{r["planned"]} | {r["provisional_grounded_semantic_successes"]}/{r["planned"]} |')
    comparison=result['comparisons'][arms[1]]['normalized_score_source_averaged']
    lines+=['',f'Paired normalized-score comparison: `{json.dumps(comparison)}`. The bootstrap resamples source means; four families give limited precision.',
       '', 'The new instruction does not produce original recovery on this set. Any generic grounded success must not be counted toward the5/25 requirement when its question differs from the source. A numerical mean inside20–75 is insufficient.',
       '', 'Common failures: treating observed denominators as numerators; asking for a radical sum whose value is not60; turning continuity observations into a different theorem question; and specifying an invalid shift boundary or leaving the cubic/area target underdetermined. Preserve all outputs and source-recovery categories, including related-but-not-equivalent questions.',
       '', 'Decision: no support for promoting the wording change as a recovery improvement. A subsequent hypothesis should distinguish teaching inverse construction with a worked example from merely requesting original recovery. It must be registered before new draws. Full conversion coverage remains a separate failed gate.',
       '', 'Evidence: [raw responses and both judgments](prompt-diagnostic.json), [paired analysis and every case](prompt-alignment-analysis.json), [fixed inputs](prompt-diagnostic-inputs.json), [input review](prompt-input-review.json), [copy review](prompt-copy-review.json), [preregistered comparison](../../../docs/plans/reconstruct-amendment-o.md).']
    (root/'prompt-alignment-report.md').write_text('\n'.join(lines)+'\n')
    print('Saved paired prompt comparison and separate semantic counts')


if __name__=='__main__':main()
