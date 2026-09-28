#!/usr/bin/env python3
"""Compare amendment R's effective policy against its frozen first-pass banks."""
import copy
import json
from pathlib import Path
from report_reconstruct_converter import summarize


def main():
    root=Path('artifacts/reconstruct/d3-v2')
    run=json.loads((root/'repair-study.json').read_text())
    base=summarize(run,'convert_p4')
    effective=copy.deepcopy(run)
    effective['banks']={}
    pending=[]
    for key,bank in run['banks'].items():
        if bank['prompt']!='convert_p4':continue
        index=str(bank['source_index'])
        if index in run['metadata']['repair_inputs']:
            outcome=run['metadata']['repair_outcomes'].get(index)
            if outcome is None:
                key=f'pending_repair_{index}'
                bank={'source_index':int(index),'output':{'status':'missing'}}
                pending.append(int(index))
            else:
                key=outcome['effective_bank_key'];bank=run['banks'][key]
        effective['banks'][key]={**copy.deepcopy(bank),'prompt':'effective_one_repair_policy'}
    result={'scope':'D3 adaptive development; first-pass and one-repair pipeline use different compute',
            'first_pass':base,'effective_policy':summarize(effective,'effective_one_repair_policy'),
            'pending_repairs':pending,'repair_outcomes':run['metadata']['repair_outcomes'],
            'new_failure_records':len(run['failures']),
            'student_outputs':len(run['responses']),
            'public_source_disagreement122_remains_excluded':True}
    repaired_keys={o['candidate_bank_key'] for o in run['metadata']['repair_outcomes'].values()}
    requests=[b['request'] for k,b in run['banks'].items() if k in repaired_keys]
    requests += [a['request'] for a in run['audits'].values() if a.get('bank_key') in repaired_keys]
    requests += [f['raw'] for f in run['failures'] if f.get('raw')]
    result['additional_recorded_usage']={
        'cost_bearing_records':len(requests),
        'prompt_tokens':sum((r.get('usage') or {}).get('prompt_tokens',0) for r in requests),
        'completion_tokens':sum((r.get('usage') or {}).get('completion_tokens',0) for r in requests),
        'estimated_cost_usd':sum((r.get('usage') or {}).get('estimated_cost',0) for r in requests),
        'summed_request_elapsed_seconds':sum(r.get('elapsed_seconds',0) for r in requests),
        'limitation':'Excludes inherited first-pass requests. Summed request time is not concurrent wall time. Missing-usage failures can incur unrecorded cost.'}
    review_path=root/'repair-copy-review.json'
    if review_path.exists():
        review=json.loads(review_path.read_text())
        result['reviewed_development_eligibility']={
            'accepted_original_sources':review['reviewed_development_eligible'],
            'original_denominator':review['original_sources'],
            'known_direct_source_disclosures':[r['source_index'] for r in review['rows'] if r['known_direct_source_disclosure']],
            'release_coverage_passed':review['release_coverage_passed'],
            'review_provenance':review['provenance']}
    (root/'repair-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# One disclosure-feedback repair: amendment R','',
           'Original twelve-source denominator retained. Only corroborated disclosure failures8,86,123 receive a repair; no student feedback is used. Other banks retain their original records and labels. A changed bank must pass all three fixed auditors. Unchanged public facts cannot obtain a favorable fresh audit.','',
           '| Policy | Accepted / original | Upper bound including unresolved |',
           '|---|---:|---:|']
    for name in ['first_pass','effective_policy']:
        v=result[name];lines.append(f'| {name} | {v["accepted"]}/12 | {100*v["coverage_upper_bound"]:.1f}% |')
    lines+=['','| Source | First-pass support/public/source | Effective support/public/source |',
             '|---|---|---|']
    for before,after in zip(base['rows'],result['effective_policy']['rows']):
        lines.append(f'| {before["source_index"]} | '+ '/'.join(before['audit_status'].values())+' | '+ '/'.join(after['audit_status'].values())+' |')
    lines+=['', 'Additional recorded compute: `'+json.dumps(result['additional_recorded_usage'])+'`.',
             '', 'These are teacher-audit outcomes, not independently certified non-leakage or Qwen recovery. Copying challenges and exact-input review remain required. No confirmation or optimum-policy claim follows from this development comparison.',
             '', 'Evidence: [raw frozen inputs and all records](repair-study.json), [analysis](repair-comparison.json), [preregistration](../../../docs/plans/reconstruct-amendment-r.md).']
    if 'reviewed_development_eligibility' in result:
        lines+=['', 'After copying and assistant source review: `'+json.dumps(result['reviewed_development_eligibility'])+'`.',
                '', 'Teacher acceptance and reviewed eligibility differ. Repaired123 hides the witness but exposes the original question; it is excluded before student generation. See [copy review](repair-copy-review.json) and [mathematical input review](repair-input-math-review.json).']
    (root/'repair-comparison.md').write_text('\n'.join(lines)+'\n')
    print(f'Effective accepted: {result["effective_policy"]["accepted"]}/12; pending repairs: {pending}')


if __name__=='__main__':main()
