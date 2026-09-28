#!/usr/bin/env python3
"""Bind AA pre-student analytic decisions to exact completed audit/copy records."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
parser=argparse.ArgumentParser();parser.add_argument('--study-root',type=Path,default=Path('artifacts/reconstruct/richer-exposure-aa'));parser.add_argument('--bank-prompt',default='convert_p6_rich');args=parser.parse_args();root=args.study_root
run=json.loads((root/'run.json').read_text());manual=json.loads((root/'prestudent-content-review.json').read_text())
refs={x['source_index']:x for x in manual['rows']};required=run['metadata']['required_bank_audits'][args.bank_prompt];rows=[]
for i in sorted(map(int,run['sources'])):
    bs=[(k,b) for k,b in run['banks'].items() if b['source_index']==i]
    row={'source_index':i,'eligible':False,'source_hash':r.stable_hash(run['sources'][str(i)])}
    if not bs:
        excluded=run['metadata'].get('source_preflight_exclusions',{}).get(str(i))
        row['reason']='Source preflight exclusion: '+excluded if excluded else 'Conversion technical failure'
        rows.append(row);continue
    assert len(bs)==1
    key,b=bs[0];row['bank_hash']=r.stable_hash(b['output'])
    if b['output']['status']!='OK':row['reason']='Converter NOT_SUITABLE: '+b['output']['reason'];rows.append(row);continue
    ref=refs[i];assert ref['bank_hash']==row['bank_hash'] and ref['source_hash']==row['source_hash']
    audits={a['prompt']:a for a in run['audits'].values() if a['bank_key']==key}
    for a in audits.values():assert a['bank_output_hash']==row['bank_hash'] and a['source_record_hash']==row['source_hash']
    copies=[c for c in run.get('copy_challenges',{}).values() if c['bank_key']==key]
    assert len(copies)<=1
    cp=copies[0] if copies else None
    if cp:
        expected={'FINAL_ANSWER':run['sources'][str(i)]['final_answer'],'PUBLIC_BANK':{'role_cue_id':b['output'].get('role_cue_id'),'clues':[{'id':c['id'],'sentence':c['sentence']} for c in b['output']['clues']]}}
        assert cp['public_input']==expected and cp['public_input_hash']==r.stable_hash(expected)
    row.update({'audit_statuses':{p:audits.get(p,{}).get('output',{}).get('status','missing') for p in required},'copy_status':cp['output']['status'] if cp else 'missing','copy_hash':r.stable_hash(cp['output']) if cp else None,'manual_content_pass':ref['manual_content_pass'],'reason':ref['reason'],'derived_inputs_reviewed':ref['manual_content_pass']})
    row['support_pass']=row['audit_statuses']['audit_support_p1']=='ACCEPT'
    row['disclosure_pass']=all(row['audit_statuses'][p]=='ACCEPT' for p in required[1:]) and ref['manual_content_pass']
    row['copy_pass']=row['copy_status']=='no_direct_reconstruction'
    row['eligible']=row['support_pass'] and row['disclosure_pass'] and row['copy_pass']
    rows.append(row)
assert not (root/'input-review.json').exists()
r.atomic_write_json(root/'input-review.json',{'reviewer':'Assistant analytic review, not human gold','manual_review_hash':r.stable_hash(manual),'protocol':run['metadata']['protocol'],'rows':rows})
print('Eligible',[x['source_index'] for x in rows if x['eligible']])
