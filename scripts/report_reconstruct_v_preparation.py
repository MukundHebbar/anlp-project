#!/usr/bin/env python3
"""Account for every allocated V source without treating pending audits as passes."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project.reconstruct import stable_hash

PROMPTS=['audit_support_p1','audit_public_p4','audit_source_disclosure_p2']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('artifacts/reconstruct/verified-examples-v'))
    parser.add_argument('--bank-prompt',default='convert_p4')
    parser.add_argument('--protocol')
    args=parser.parse_args()
    root=args.root
    allocation=json.loads(Path('data/manifests/reconstruct-d4-allocation-v1.json').read_text())
    base=json.loads((root/'run.json').read_text())
    run=json.loads((root/'repair-study.json').read_text()) if (root/'repair-study.json').exists() else base
    review=json.loads((root/'input-review.json').read_text()) if (root/'input-review.json').exists() else {'rows':[]}
    manual={row['source_index']:row for row in review['rows']}
    rows=[]
    for index in allocation['partitions']['D4']:
        banks=[(k,b) for k,b in run['banks'].items() if b['source_index']==index and b['prompt']==args.bank_prompt]
        assert len(banks)<=1
        row=dict(source_index=index,conversion='missing',support='missing',public='missing',source_disclosure='missing',
                 joint_audit_accept=False,reviewed_eligible=False,bank_key=None)
        if banks:
            original_key,bank=banks[0]
            outcome=run.get('metadata',{}).get('repair_outcomes',{}).get(str(index))
            key=outcome['effective_bank_key'] if outcome else original_key
            bank=run['banks'][key]
            row.update(bank_key=key,conversion=bank['output']['status'],bank_output_hash=stable_hash(bank['output']),
                       source_record_hash=stable_hash(run['sources'][str(index)]),repaired=key!=original_key)
            for prompt,field in zip(PROMPTS,['support','public','source_disclosure']):
                audits=[a for a in run['audits'].values() if a['bank_key']==key and a['prompt']==prompt]
                assert len(audits)<=1
                if audits:
                    audit=audits[0]
                    assert audit['bank_output_hash']==row['bank_output_hash']
                    assert audit['source_record_hash']==row['source_record_hash']
                    row[field]=audit['output']['status']
            row['joint_audit_accept']=row['conversion']=='OK' and all(row[f]=='ACCEPT' for f in ['support','public','source_disclosure'])
            if index in manual:
                m=manual[index]
                assert m['bank_key']==key and m['bank_output_hash']==row['bank_output_hash']
                assert m['source_record_hash']==row['source_record_hash']
                row['reviewed_eligible']=row['joint_audit_accept'] and m['development_eligible_after_review'] is True
                row['manual_review']=m['reason']
        rows.append(row)
    count=sum(row['reviewed_eligible'] for row in rows)
    report=dict(protocol=args.protocol or allocation['protocol'],allocated_sources=12,rows=rows,
                raw_joint_audit_accepts=sum(row['joint_audit_accept'] for row in rows),
                reviewed_eligible=count,exploratory_eight_family_minimum_met=count>=8,
                production_coverage_80pct_met=count/12>=.8,
                student_ready=False,
                note='Readiness requires a separately frozen exact-input artifact and all independent review records; this summary never authorizes generation.')
    (root/'preparation-report.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Input preparation','',f"Reviewed eligible: {count}/12. Raw joint audit accepts: {report['raw_joint_audit_accepts']}/12.",'',
           '| Source | Conversion | Support | Public disclosure | Source disclosure | Independently reviewed eligible |',
           '|---|---|---|---|---|---|']
    for row in rows:
        lines.append(f"| {row['source_index']} | {row['conversion']} | {row['support']} | {row['public']} | {row['source_disclosure']} | {row['reviewed_eligible']} |")
    lines+=['',report['note'],'Review provenance is assistant/analytic unless explicitly recorded otherwise; it is not human gold.']
    (root/'preparation-report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))


if __name__=='__main__':main()
