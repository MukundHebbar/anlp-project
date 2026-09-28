#!/usr/bin/env python3
"""Freeze/run reviewed D4 local Qwen draws with exact input and prompt bindings."""
import argparse
import copy
import fcntl
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r

ROOT=Path('artifacts/reconstruct/verified-examples-v')
PROMPTS=['student_p10_recover_original','student_p12_verified_examples']


def freeze(root=ROOT, prompts=PROMPTS, protocol=None):
    target=root/'student.json'
    if target.exists(): raise ValueError('Student artifact already frozen')
    parent=json.loads((root/'repair-study.json').read_text())
    reviews=json.loads((root/'input-review.json').read_text())
    allocation=json.loads(Path('data/manifests/reconstruct-d4-allocation-v1.json').read_text())
    runtime=json.loads((root/'local-runtime-provenance.json').read_text())
    command=runtime['command_line']
    assert command[command.index('--reasoning')+1]=='off'
    eligible=[row for row in reviews['rows'] if row['development_eligible_after_review'] is True]
    indices=sorted(row['source_index'] for row in eligible)
    if len(indices)!=len(set(indices)) or len(indices)<8 or not set(indices)<=set(allocation['partitions']['D4']):
        raise ValueError('Need at least eight unique reviewed D4 families')
    for prompt in prompts:
        assert r.stable_hash(Path(f'data/prompts/reconstruct/runtime/{prompt}.md').read_text())==allocation['prompt_file_hashes'][prompt]
    run=dict(sources={str(i):copy.deepcopy(parent['sources'][str(i)]) for i in indices},
             partitions={'D1':indices},banks={},audits={},copy_challenges={},responses={},evaluations={},source_recovery={},failures=[],
             metadata={'protocol':protocol or allocation['protocol'],'study_root':str(root),'student_prompts':list(prompts),'created_at':r.utc_now(),'allocation_hash':r.stable_hash(allocation),
                       'input_review_hash':r.stable_hash(reviews),'original_source_denominator':12,
                       'runtime_provenance_hash':r.stable_hash(runtime),
                       'frozen_public_inputs':{},'jobs':[],'attempted_jobs':[]})
    requests={}
    for row in eligible:
        index=row['source_index'];key=row['bank_key'];bank=parent['banks'][key]
        assert r.stable_hash(bank['output'])==row['bank_output_hash']
        assert r.stable_hash(run['sources'][str(index)])==row['source_record_hash']
        for field in ['mathematical_support_passed','no_direct_source_disclosure','no_complete_solution_exposed','copy_challenge_reviewed']:
            if row.get(field) is not True: raise ValueError(f'Unverified review field {field} for {index}')
        audits={k:v for k,v in parent['audits'].items() if v['bank_key']==key}
        by_prompt={a['prompt']:a for a in audits.values()}
        for prompt in ['audit_support_p1','audit_public_p4','audit_source_disclosure_p2']:
            a=by_prompt[prompt]
            assert a['output']['status']=='ACCEPT'
            assert a['bank_output_hash']==row['bank_output_hash'] and a['source_record_hash']==row['source_record_hash']
        copies={k:v for k,v in parent.get('copy_challenges',{}).items() if v['bank_key']==key}
        if len(copies)!=1: raise ValueError('Exactly one completed copy challenge is required')
        copy_record=next(iter(copies.values()))
        assert r.stable_hash(copy_record['output'])==row['copy_output_hash']
        copy_public={'FINAL_ANSWER':run['sources'][str(index)]['final_answer'],
                     'PUBLIC_BANK':{'role_cue_id':bank['output'].get('role_cue_id'),
                                    'clues':[{'id':c['id'],'sentence':c['sentence']} for c in bank['output']['clues']]}}
        assert copy_record['public_input']==copy_public
        assert copy_record['public_input_hash']==r.stable_hash(copy_public)
        run['banks'][key]=copy.deepcopy(bank);run['audits'].update(copy.deepcopy(audits));run['copy_challenges'].update(copy.deepcopy(copies))
        evidence=r.condition_evidence(run['sources'][str(index)],'bank',bank=bank,
            clue_count=len(bank['output']['clues']),clue_seed=20260920,style='sentence',selection_policy='bank_order')
        evidence['disclosure']='medium'
        run['metadata']['frozen_public_inputs'][str(index)]={'bank_key':key,'evidence':evidence,'evidence_hash':r.stable_hash(evidence)}
        for prompt in prompts:
            text=r.render_template(r.load_prompt(prompt),{'FINAL_ANSWER':evidence['final_answer'],'RENDERED_CLUES':evidence['rendered_clues']})
            requests[f'{index}:{prompt}']={'rendered_prompt':text,'rendered_input_hash':r.stable_hash(text)}
    run['metadata']['student_readiness']={'status':'ready','scope':'Assistant-reviewed development only; not independently validated final release',
        'approved_evidence_hashes':{i:v['evidence_hash'] for i,v in run['metadata']['frozen_public_inputs'].items()}}
    for seed in [0,1]:
        for position,index in enumerate(indices):
            for prompt in (prompts if (position+seed)%2==0 else list(reversed(prompts))):
                run['metadata']['jobs'].append({'id':f'{index}:{prompt}:{seed}','source_index':index,'prompt':prompt,'seed':seed})
    run['metadata']['requests_hash']=r.stable_hash(requests)
    r.atomic_write_json(root/'student-requests.json',requests)
    r.atomic_write_json(target,run)
    print(f'Frozen {len(indices)} eligible families and {len(run["metadata"]["jobs"])} local draws; no model calls',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--study-root',type=Path,default=ROOT)
    parser.add_argument('--student-prompts',nargs='+',default=PROMPTS,choices=PROMPTS)
    parser.add_argument('--protocol')
    args=parser.parse_args()
    root=args.study_root
    if len(args.student_prompts)!=len(set(args.student_prompts)):
        parser.error('Student prompts must be unique')
    if root!=ROOT and not args.protocol:
        parser.error('A separate study requires its own prospective protocol')
    with (root/'student-controller.lock').open('w') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        if args.prepare_only: freeze(root,args.student_prompts,args.protocol);return
        target=root/'student.json'
        run=json.loads(target.read_text())
        if args.protocol and run['metadata']['protocol']!=args.protocol:
            raise ValueError('Study protocol mismatch')
        if sorted({j['prompt'] for j in run['metadata']['jobs']})!=sorted(args.student_prompts):
            raise ValueError('Frozen prompt population differs from requested study')
        requests=json.loads((root/'student-requests.json').read_text())
        assert r.stable_hash(requests)==run['metadata']['requests_hash']
        for job in run['metadata']['jobs']:
            if job['id'] in run['metadata']['attempted_jobs']:continue
            index=job['source_index'];prompt=job['prompt']
            frozen=run['metadata']['frozen_public_inputs'][str(index)]
            rendered=r.render_template(r.load_prompt(prompt),{'FINAL_ANSWER':frozen['evidence']['final_answer'],
                'RENDERED_CLUES':frozen['evidence']['rendered_clues']})
            assert r.stable_hash(rendered)==requests[f'{index}:{prompt}']['rendered_input_hash']
            bank=run['banks'][frozen['bank_key']]
            options=r.parse_args(['student','--output',str(target),'--student-prompt',prompt,
                '--bank-prompt',bank['prompt'],'--indices',str(index),'--all-clues','--selection-policy','bank_order',
                '--style','sentence','--max-tokens','8192','--temperature','.7','--top-p','.8','--top-k','20',
                '--seed',str(job['seed']),'--timeout','300'])
            # Persist before calling: an interrupted draw is never silently repeated.
            run['metadata']['attempted_jobs'].append(job['id'])
            r.atomic_write_json(target,run)
            print(f"Local draw {job['id']}",flush=True)
            r.student_sources(options,run,[index])
        print('All fixed Local draw slots terminal; retain missing outputs.',flush=True)


if __name__=='__main__':main()
