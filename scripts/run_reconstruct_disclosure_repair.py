#!/usr/bin/env python3
"""Freeze and execute amendment R's single bounded repair; never read student records."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import fcntl
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r

PROMPT='repair_disclosure_p1'
MODEL='deepseek-ai/DeepSeek-V4.1-Flash'
BASE=Path('artifacts/reconstruct/d3-v2/run.json')
OUTPUT=Path('artifacts/reconstruct/d3-v2/repair-study.json')


def public_content(bank):
    # Production/audit condition uses sentences. Cosmetic IDs, ordering, hidden
    # support or fragment changes cannot buy a new judgment of the same facts.
    return sorted(c['sentence'] for c in bank.get('clues',[]))


def prepare(base, template, *, base_path=BASE, protocol='docs/plans/reconstruct-amendment-r.md',
            expected_indices=(8,86,123), expected_bank_count=11, base_bank_prompt='convert_p4'):
    banks={k:copy.deepcopy(b) for k,b in base['banks'].items() if b['prompt']==base_bank_prompt}
    if expected_bank_count is not None:
        assert len(banks)==expected_bank_count
    audits={k:copy.deepcopy(a) for k,a in base['audits'].items() if a.get('bank_key') in banks}
    inputs={}
    for key,bank in banks.items():
        if bank['output'].get('status')!='OK':
            continue
        by_prompt={a['prompt']:a for a in audits.values() if a['bank_key']==key}
        if not all(p in by_prompt for p in ['audit_support_p1','audit_public_p4','audit_source_disclosure_p2']):
            continue  # An unresolved audit is not a corroborated repair reason.
        if not (by_prompt['audit_support_p1']['output']['status']=='ACCEPT'
                and by_prompt['audit_public_p4']['output']['status']=='REJECT'
                and by_prompt['audit_source_disclosure_p2']['output']['status']=='REJECT'):
            continue
        index=bank['source_index'];source=base['sources'][str(index)]
        prompt=r.render_template(template,{'SOURCE_QUESTION':source['question'],
            'FINAL_ANSWER':source['final_answer'],'CHECKED_SOLUTION':source['checked_solution'],
            'ORIGINAL_BANK':json.dumps(bank['output'],ensure_ascii=False),
            'PUBLIC_REVIEW':json.dumps(by_prompt['audit_public_p4']['output'],ensure_ascii=False),
            'SOURCE_REVIEW':json.dumps(by_prompt['audit_source_disclosure_p2']['output'],ensure_ascii=False)})
        inputs[str(index)]={'source_index':index,'base_bank_key':key,
            'base_bank_output_hash':r.stable_hash(bank['output']),
            'source_record_hash':r.stable_hash(source),'rendered_prompt':prompt,
            'rendered_input_hash':r.stable_hash(prompt)}
    if expected_indices is not None:
        assert sorted(map(int,inputs))==list(expected_indices)
    return {'metadata':{'study':'one audit-feedback disclosure repair','base_bank_prompt':base_bank_prompt,
             'protocol':protocol,'created_at':r.utc_now(),'base_artifact':str(base_path),'template_hash':r.stable_hash(template),
             'repair_inputs':inputs,'repair_outcomes':{},'student_readiness':{'status':'pending'},
             'original_source_denominator':len(base['sources']),'student_records_used':False},
            'sources':copy.deepcopy(base['sources']),'partitions':copy.deepcopy(base['partitions']),
            'banks':banks,'audits':audits,'responses':{},'evaluations':{},'source_recovery':{},'failures':[]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--retry-failed-once',action='store_true')
    parser.add_argument('--base',type=Path,default=BASE)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--protocol',default='docs/plans/reconstruct-amendment-r.md')
    parser.add_argument('--base-bank-prompt',default='convert_p4')
    args=parser.parse_args()
    template=r.load_prompt(PROMPT)
    output_path=args.output
    with output_path.with_suffix('.json.lock').open('w') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        if not output_path.exists():
            legacy=args.base==BASE and args.base_bank_prompt=='convert_p4'
            run=prepare(json.loads(args.base.read_text()),template,base_path=args.base,protocol=args.protocol,
                        expected_indices=(8,86,123) if legacy else None,
                        expected_bank_count=11 if legacy else None,base_bank_prompt=args.base_bank_prompt)
            r.atomic_write_json(output_path,run)
        else:run=json.loads(output_path.read_text())
        assert run['metadata']['base_artifact']==str(args.base)
        assert run['metadata'].get('base_bank_prompt','convert_p4')==args.base_bank_prompt
        assert run['metadata']['template_hash']==r.stable_hash(template)
        if args.prepare_only:
            print(f"Frozen repair inputs for {sorted(run['metadata']['repair_inputs'])}; no model calls")
            return
        attempts=Counter(f['key'] for f in run['failures'] if f['stage']=='convert')
        jobs=[]
        for index,item in run['metadata']['repair_inputs'].items():
            assert r.stable_hash(run['sources'][index])==item['source_record_hash']
            assert r.stable_hash(run['banks'][item['base_bank_key']]['output'])==item['base_bank_output_hash']
            assert r.stable_hash(item['rendered_prompt'])==item['rendered_input_hash']
            key=f'{index}:{r.stable_hash(template)}:{MODEL}:low'
            if key in run['banks']:continue
            if attempts[key] != (1 if args.retry_failed_once else 0):continue
            jobs.append((key,item))
        def worker(key,item):
            raw=None
            try:
                raw=r.teacher_call(r.deepinfra_client(180),item['rendered_prompt'],MODEL,8192,'low')
                output=r.validate_bank(r.extract_json_object(raw['content']))
                return key,item,raw,output,None
            except Exception as exc:return key,item,raw,None,exc
        # At most one repair per frozen corroborated defect, conservatively reserved.
        reserve=sum((len(i['rendered_prompt'])/4*.20+8192*.60)/1e6 for _,i in jobs)
        if r.actual_cost(run)+reserve>.50:raise RuntimeError('Repair artifact cost ceiling exceeded')
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures=[pool.submit(worker,k,i) for k,i in jobs]
            for future in as_completed(futures):
                key,item,raw,output,error=future.result();index=item['source_index']
                if error is not None:
                    r.failure(run,'convert',index,key,error,raw)
                    print(f'repair {index}: technical failure {error}',flush=True)
                else:
                    unchanged=(output['status']=='OK' and public_content(output)==public_content(run['banks'][item['base_bank_key']]['output']))
                    run['banks'][key]={'source_index':index,'prompt':PROMPT,'prompt_hash':r.stable_hash(template),
                        'model':MODEL,'reasoning_effort':'low','output':output,'raw_content':raw['content'],
                        'request':{k:v for k,v in raw.items() if k!='content'},
                        'rendered_input_hash':item['rendered_input_hash'],'base_bank_key':item['base_bank_key']}
                    run['metadata']['repair_outcomes'][str(index)]={'candidate_bank_key':key,
                        'public_unchanged':unchanged,'status':output['status'],
                        'effective_bank_key':item['base_bank_key'] if unchanged else key}
                    print(f'repair {index}: {output["status"]}; unchanged public={unchanged}',flush=True)
                r.atomic_write_json(output_path,run)


if __name__=='__main__':main()
