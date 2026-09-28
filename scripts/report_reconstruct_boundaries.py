#!/usr/bin/env python3
"""Reproduce semantic/disclosure development counts without relabeling raw calls."""
import json
from pathlib import Path


def semantic_report():
    root=Path('artifacts/reconstruct/semantic-v1')
    fixtures=json.loads(Path('data/manifests/reconstruct-semantic-development-v1.json').read_text())['fixtures']
    outputs={}
    for arm in ['incumbent','candidate']:
        run=json.loads((root/f'{arm}.json').read_text())
        records={v['fixture_id']:v for v in run['judge_fixtures'].values()}
        rows=[]
        for c in fixtures:
            r=records.get(c['id'],{})
            value=r.get('output',{}).get('source_recovery')
            rows.append({'id':c['id'],'family':c['family'],'expected':c['expected'],'observed':value,
                         'exact_agreement':value==c['expected'],
                         'binary_agreement':value is not None and (value==2)==(c['expected']==2)})
        outputs[arm]={'planned':len(fixtures),'resolved':len(records),
                      'exact_agreements':sum(x['exact_agreement'] for x in rows),
                      'binary_agreements':sum(x['binary_agreement'] for x in rows),
                      'families':len({x['family'] for x in rows}),
                      'recorded_cost_usd':sum(v['request']['usage']['estimated_cost'] for v in records.values()),
                      'rows':rows}
    (root/'comparison.json').write_text(json.dumps(outputs,indent=2)+'\n')
    lines=['# Semantic calibration: development controls','',
           '| Prompt | Resolved | Three-way agreement | Same/not-same agreement |',
           '|---|---:|---:|---:|']
    for arm,row in outputs.items():
        lines.append(f'| {arm} | {row["resolved"]}/{row["planned"]} | {row["exact_agreements"]}/{row["planned"]} | {row["binary_agreements"]}/{row["planned"]} |')
    lines += ['', 'These are24 authored cases from8 families, not24 independent validation families. The candidate disagrees only on graph-1: it labels the change from labelled spanning trees to unlabelled trees as different(0), while the reference calls it related(1). Both correctly reject semantic equivalence. Preserve the disagreement; do not alter the reference to improve agreement.',
      '', 'Assistant inspection of all eight candidate equivalence correspondences found the stated mappings valid: polynomial factorization, ordered dice outcomes, tangent slope, congruence/divisibility, definite integral/signed area, labelled trees, geometric recurrence, and algebraic rewriting of a universal inequality. This is assistant review, not human adjudication or independent final gold.',
      '', 'Decision: the added schema is usable for development because it makes semantic checks inspectable. No accuracy gain is established; the incumbent has higher three-way agreement on these controls. Before promotion, test production-derived boundary cases and independent families. The5/25 Qwen recovery gate has not been evaluated by this calibration.',
      '', 'Evidence: [frozen references](../../../data/manifests/reconstruct-semantic-development-v1.json), [incumbent raw](incumbent.json), [candidate raw](candidate.json), [counts](comparison.json).']
    (root/'report.md').write_text('\n'.join(lines)+'\n')


def disclosure_report():
    root=Path('artifacts/reconstruct/disclosure-v1')
    if not (root/'candidate.json').exists():return
    cases=json.loads(Path('data/manifests/reconstruct-disclosure-development-v1.json').read_text())['fixtures']
    result={}
    arms=['incumbent','candidate']+[arm for arm in ['source-aware','source-aware-p2']
                                 if (root/f'{arm}.json').exists()]
    for arm in arms:
        r=json.loads((root/f'{arm}.json').read_text())
        by_id={v['source_index']:v for v in r['audits'].values()}
        rows=[]
        for i,c in enumerate(cases):
            value=by_id.get(i,{}).get('output',{})
            rows.append({'id':c['id'],'family':c['family'],'expected':c['expected'],
                         'observed':value.get('status'),'reason':value.get('reason'),
                         'agrees':value.get('status')==c['expected'] if c['expected'] is not None else None})
        result[arm]={'planned':len(cases),'resolved':len(by_id),'failure_records':len(r['failures']),
                     'deterministically_revalidated':sum('validation_recovery' in a for a in r['audits'].values()),
                     'labeled_controls':sum(c['expected'] is not None for c in cases),
                     'control_agreements':sum(x['agrees'] is True for x in rows),'rows':rows}
    (root/'comparison.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    lines=['# Public disclosure calibration','',
           'Development controls only; six production boundaries have no frozen binary reference and are excluded from agreement counts. Unresolved outputs remain in the planned denominator.','',
           '| Arm | Resolved inputs | Clear-control agreement | Failure records | Revalidated without calls |','|---|---:|---:|---:|---:|']
    for arm,r in result.items():
        lines.append(f'| {arm} | {r["resolved"]}/{r["planned"]} | {r["control_agreements"]}/{r["labeled_controls"]} | {r["failure_records"]} | {r["deterministically_revalidated"]} |')
    lines += ['','## Production boundaries','','| Input | '+' | '.join(arms)+' |','|---|'+'---|'*len(arms)]
    for i,a in enumerate(result['incumbent']['rows']):
        if a['expected'] is None:
            lines.append('| '+a['id']+' | '+' | '.join(result[arm]['rows'][i]['observed'] or 'unresolved' for arm in arms)+' |')
    lines+=['','Counts alone do not authorize the D3 sweep. Inspect reasons, public quotes, source-aware exposure, and the direct-copy challenge before accepting exact inputs. A passing public auditor is not proof of non-leakage.',
            '', 'Evidence: [frozen cases](../../../data/manifests/reconstruct-disclosure-development-v1.json), [incumbent raw](incumbent.json), [candidate raw](candidate.json), [per-case comparison](comparison.json).']
    (root/'report.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    semantic_report()
    disclosure_report()
    print('Saved semantic and disclosure development reports; raw labels unchanged')
