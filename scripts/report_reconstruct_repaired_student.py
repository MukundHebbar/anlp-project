#!/usr/bin/env python3
"""Reproduce S's nine-family screen and four-family historical paired comparison."""
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash
from anlp_project.reconstruct_gates import verify_response_bindings
from analyze_reconstruct_followup import analyze


def annotate(result,run):
    evaluations={v['response_key']:v for v in run['evaluations'].values() if v['prompt']=='evaluate_p2'}
    semantics={v['response_key']:v for v in run['source_recovery'].values() if v['prompt']=='source_recovery_p2'}
    for case in result['cases']:
        key=case['response_key'];response=run['responses'][key]
        case['bindings_verified']=verify_response_bindings(key,response,evaluations.get(key,{}),semantics.get(key,{}),run['sources'][str(response['source_index'])])
        case['provisional_grounded_semantic_success']=bool(case['success'] and case['source_recovery']==2 and case['bindings_verified'])
    for arm,row in result['arms'].items():
        cases=[c for c in result['cases'] if c['arm']==arm]
        row['semantic_resolved']=sum(c['source_recovery'] is not None for c in cases)
        row['same_original']=sum(c['source_recovery']==2 for c in cases)
        row['provisional_grounded_semantic_successes']=sum(c['provisional_grounded_semantic_success'] for c in cases)
    return result


def main():
    root=Path('artifacts/reconstruct/d3-v2')
    original=json.loads((root/'repaired-student.json').read_text())
    run=copy.deepcopy(original)
    for bank in run['banks'].values():bank['prompt']='policy_r'
    indices=run['metadata']['diagnostic_source_indices']
    primary=annotate(analyze(run,'reserve',['student_p1@policy_r'],[0,1],indices,selection_policy='bank_order'),run)
    historical=json.loads((root/'prompt-diagnostic.json').read_text())
    common=[8,27,33,77]
    old_keys=set()
    for key,response in historical['responses'].items():
        bank=historical['banks'][response['bank_key']]
        if response['prompt']!='student_p1' or bank['prompt']!='convert_p3' or response['source_index'] not in common:continue
        index=str(response['source_index'])
        assert stable_hash(run['sources'][index])==stable_hash(historical['sources'][index])
        for new in original['responses'].values():
            if new['source_index']==response['source_index'] and new['sampling']['seed']==response['sampling']['seed']:
                assert (new['sampling'],new['model'],new['prompt_hash'])==(response['sampling'],response['model'],response['prompt_hash'])
        assert key not in run['responses']
        run['responses'][key]=copy.deepcopy(response)
        run['banks'][response['bank_key']]=copy.deepcopy(bank)
        old_keys.add(key)
    assert len(old_keys)==8
    for section in ['evaluations','source_recovery']:
        run[section].update({k:copy.deepcopy(v) for k,v in historical[section].items() if v['response_key'] in old_keys})
    paired=annotate(analyze(run,'reserve',['student_p1@convert_p3','student_p1@policy_r'],[0,1],common,selection_policy='bank_order'),run)
    result={'scope':'Amendment S developmental screen; input coverage9/12 fails release; historical common-family outputs reused',
       'nine_family_screen':primary,'four_family_paired':paired,
       'historical_reuse':{'artifact':'prompt-diagnostic.json','response_keys':sorted(old_keys),
          'source_records_and_matching_observed_sampling_checked':True},
       'primary_end_to_end_denominator':12,
       'final_25_family_confirmation':False}
    local_failures=[f for f in original['failures'] if f['stage']=='student']
    attempts=[v['request'] for v in original['responses'].values()]+[f.get('raw') or {} for f in local_failures]
    known=[v for v in attempts if v.get('usage',{}).get('completion_tokens') is not None]
    result['all_local_attempt_runtime']={
        'attempts_including_failed_outputs':len(attempts),'parseable_outputs':len(original['responses']),
        'failed_outputs':len(local_failures),'attempts_with_recorded_usage':len(known),
        'total_known_completion_tokens':sum(v['usage']['completion_tokens'] for v in known),
        'mean_known_completion_tokens_per_attempt':sum(v['usage']['completion_tokens'] for v in known)/len(known) if known else None,
        'length_stops_including_failed_outputs':sum(v.get('finish_reason')=='length' for v in attempts),
        'summed_request_elapsed_seconds':sum(v.get('elapsed_seconds',0) for v in attempts),
        'note':'Arm-level means from the shared analyzer describe parsed responses; this separate accounting includes failed raw completions.'}
    (root/'repaired-student-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Reviewed one-repair policy: local Qwen screen','',result['scope'], '',
       '| Arm | Scored / planned | Resolved mean /100 | Grounded | Same original | Provisional grounded semantic |',
       '|---|---:|---:|---:|---:|---:|']
    for arm,row in primary['arms'].items():
        lines.append(f'| {arm} | {row["resolved"]}/{row["planned"]} | {row["mean_normalized_score_resolved"]} | {row["successes"]} | {row["same_original"]} | {row["provisional_grounded_semantic_successes"]} |')
    lines+=['', 'Semantic judgments unresolved must not be read as confirmed failures. All provisional successes require mathematical and semantic case review. Seed0 is primary; seed1 cannot rescue it. Reported full analysis includes missingness bounds and paired source-bootstrap uncertainty.', '',
       'This compares evidence-policy packages, not isolated clue counts or repair effects. New inputs are fixed before student output; no poor-answer replacement. Neither this conditional nine-family screen nor its four-family historical comparison satisfies the5/25 gate.', '',
       'Evidence: [analysis and cases](repaired-student-analysis.json), [raw outputs and judgments](repaired-student.json), [exact public inputs](repaired-student-inputs.json), [preregistration](../../../docs/plans/reconstruct-amendment-s.md).']
    lines+=['', 'All local attempts, including the coefficient truncation: `'+json.dumps(result['all_local_attempt_runtime'])+'`.']
    (root/'repaired-student-report.md').write_text('\n'.join(lines)+'\n')
    print('Saved partial/final screen with explicit missingness and reused baseline provenance')


if __name__=='__main__':main()
