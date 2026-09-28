#!/usr/bin/env python3
"""Compare frozen converter packages using identical audit versions."""
import json
import argparse
from pathlib import Path


def summarize(run, converter):
    prompts=['audit_support_p1','audit_public_p4','audit_source_disclosure_p2']
    rows=[]
    banks={b['source_index']:(k,b) for k,b in run['banks'].items() if b['prompt']==converter}
    for index in [8,20,27,33,77,86,112,122,123,136,141,143]:
        key,bank=banks.get(index,(None,{}))
        latest={a['prompt']:a['output'] for a in run['audits'].values() if a.get('bank_key')==key}
        status={p:latest.get(p,{}).get('status','unresolved') for p in prompts}
        rows.append({'source_index':index,'bank_key':key,'clue_count':len(bank.get('output',{}).get('clues',[])),
                     'bank_status':bank.get('output',{}).get('status','source_ineligible' if index==20 else 'missing'),
                     'audit_status':status,'accepted':all(s=='ACCEPT' for s in status.values()),
                     'audit_reasons':{p:latest.get(p,{}).get('reason') for p in prompts},
                     'withheld':bank.get('output',{}).get('withheld')})
    potential=[r['source_index'] for r in rows if r['source_index']!=20
               and r['bank_status'] in {'OK','missing'}
               and not r['accepted'] and 'REJECT' not in r['audit_status'].values()]
    return {'converter':converter,'original_sources':12,'source_eligible':11,
            'accepted':sum(r['accepted'] for r in rows),
            'potential_additional_acceptances':potential,
            'missing_conversions':[r['source_index'] for r in rows if r['bank_status']=='missing'],
            'upper_bound_interpretation':'All unresolved eligible conversions/audits could pass; known rejected and NOT_SUITABLE cases cannot pass without changing the procedure. This bound is not a forecast.',
            'coverage_upper_bound':(sum(r['accepted'] for r in rows)+len(potential))/12,
            'accepted_source_ids':[r['source_index'] for r in rows if r['accepted']],
            'unresolved_eligible':sum(r['source_index']!=20 and 'unresolved' in r['audit_status'].values() for r in rows),
            'rows':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compare-p4',action='store_true',help='Report amendment Q separately; preserve p2/p3 report')
    args=parser.parse_args()
    root=Path('artifacts/reconstruct/d3-v2')
    specifications=([('incumbent','run.json','convert_p3'),('candidate','run.json','convert_p4')]
                    if args.compare_p4 else
                    [('incumbent','incumbent-audits.json','convert_p2'),('candidate','run.json','convert_p3')])
    basename='converter-p4-comparison' if args.compare_p4 else 'converter-comparison'
    result={name:summarize(json.loads((root/file).read_text()),prompt) for name,file,prompt in
            specifications}
    result['common_accepted']=sorted(set(result['incumbent']['accepted_source_ids'])&set(result['candidate']['accepted_source_ids']))
    (root/f'{basename}.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    lines=['# D3 converter comparison under matched audit versions','',
      'Development data only. The intervention changes the converter prompt package; it does not isolate example count, clue count, or any one wording change. Source20 remains in the12-source coverage denominator.','',
      '| Policy | Accepted/original | Accepted/eligible | Eligible with unresolved audits | Coverage upper bound |',
      '|---|---:|---:|---:|---:|']
    for name in ['incumbent','candidate']:
        r=result[name];lines.append(f'| {r["converter"]} | {r["accepted"]}/12 | {r["accepted"]}/11 | {r["unresolved_eligible"]} | {100*r["coverage_upper_bound"]:.1f}% |')
    lines+=['','| Source | Old clues | New clues | Old support/public/source | New support/public/source |','|---|---:|---:|---|---|']
    for a,b in zip(result['incumbent']['rows'],result['candidate']['rows']):
        lines.append(f'| {a["source_index"]} | {a["clue_count"]} | {b["clue_count"]} | '+
                     '/'.join(a['audit_status'].values())+' | '+'/'.join(b['audit_status'].values())+' |')
    lines+=['','These are teacher audit decisions, not independently certified validity. A released bank must also pass the restricted-copy challenge and review. No D3 Qwen recovery score is inferred from converter coverage.','',
            f'Evidence: [candidate raw](run.json), [incumbent under the same auditors]({specifications[0][1]}), [per-source reasons and withheld content]({basename}.json), [preregistered intervention](../../../docs/plans/reconstruct-amendment-{"q" if args.compare_p4 else "m"}.md).']
    (root/f'{basename}.md').write_text('\n'.join(lines)+'\n')
    print('Saved current converter comparison; unresolved stages explicitly reported')


if __name__=='__main__':main()
