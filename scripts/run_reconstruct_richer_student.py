#!/usr/bin/env python3
"""Freeze and execute AA transformations of explicitly reviewed full banks."""
import argparse,copy,json,sys
from dataclasses import asdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
ROOT=Path('artifacts/reconstruct/richer-exposure-aa')
ARMS=['sparse3','rich6','dense3']

def freeze():
    target=ROOT/'student.json'
    if target.exists():raise ValueError('Already frozen')
    parent=json.loads((ROOT/'run.json').read_text())
    review=json.loads((ROOT/'input-review.json').read_text())
    runtime=json.loads((ROOT/'local-runtime-provenance.json').read_text())
    assert runtime['command_line'][runtime['command_line'].index('--reasoning')+1]=='off'
    prompt=r.load_prompt('student_p10_recover_original')
    run=copy.deepcopy(parent);run.update(responses={},evaluations={},source_recovery={},failures=[])
    run['metadata'].update({'input_review_hash':r.stable_hash(review),'runtime_hash':r.stable_hash(runtime),'student_prompt_hash':r.stable_hash(prompt),'jobs':[],'attempted_jobs':[],'original_denominator':12,'arms':ARMS})
    requests={}
    for pos,row in enumerate(review['rows']):
        if not row['eligible']:continue
        index=row['source_index'];key,bank=r.accepted_bank(parent,index,'convert_p6_rich')
        assert row['bank_hash']==r.stable_hash(bank['output']) and row['source_hash']==r.stable_hash(parent['sources'][str(index)])
        assert row['support_pass'] and row['disclosure_pass'] and row['derived_inputs_reviewed'] and row['copy_pass']
        copies=[v for v in parent.get('copy_challenges',{}).values() if v['bank_key']==key]
        assert len(copies)==1 and r.stable_hash(copies[0]['output'])==row['copy_hash']
        assert copies[0]['output']['status']=='no_direct_reconstruction'
        clues=bank['output']['clues'];assert len(clues)==6
        variants={'sparse3':clues[:3],'rich6':clues,'dense3':[
            {'id':f'p{i+1}','sentence':clues[2*i]['sentence']+' '+clues[2*i+1]['sentence']} for i in range(3)]}
        assert ' '.join(c['sentence'] for c in variants['dense3']) == ' '.join(c['sentence'] for c in variants['rich6'])
        for arm in ARMS[pos%3:]+ARMS[:pos%3]:
            evidence=r.public_evidence(parent['sources'][str(index)]['final_answer'],variants[arm],'sentence')
            evidence['selection_policy']='frozen_AA_'+arm;evidence['disclosure']='medium'
            text=r.render_template(prompt,{'FINAL_ANSWER':evidence['final_answer'],'RENDERED_CLUES':evidence['rendered_clues']})
            jobid=f'{index}:{arm}:0'
            requests[jobid]={'source_index':index,'arm':arm,'bank_key':key,'public_evidence':evidence,'evidence_hash':r.stable_hash(evidence),'rendered_prompt':text,'rendered_input_hash':r.stable_hash(text)}
            run['metadata']['jobs'].append(jobid)
    assert requests
    run['metadata']['requests_hash']=r.stable_hash(requests)
    r.atomic_write_json(ROOT/'student-requests.json',requests);r.atomic_write_json(target,run)
    print('Frozen',len(requests),'local draws',flush=True)

def main():
    global ROOT
    p=argparse.ArgumentParser();p.add_argument('--prepare-only',action='store_true');p.add_argument('--study-root',type=Path,default=ROOT);a=p.parse_args()
    ROOT=a.study_root
    if a.prepare_only:freeze();return
    target=ROOT/'student.json';run=json.loads(target.read_text());requests=json.loads((ROOT/'student-requests.json').read_text())
    assert r.stable_hash(requests)==run['metadata']['requests_hash']
    prompt_name=run['metadata'].get('student_prompt','student_p10_recover_original')
    assert r.stable_hash(r.load_prompt(prompt_name))==run['metadata']['student_prompt_hash']
    assert r.stable_hash(json.loads((ROOT/'input-review.json').read_text()))==run['metadata']['input_review_hash']
    seed=run['metadata'].get('student_seed',0)
    assert type(seed) is int and seed>=0, 'Student seed must be a frozen nonnegative integer'
    config=r.SamplingConfig(.7,.8,20,8192,seed);client=r.local_client(r.DEFAULT_LOCAL_URL,300)
    for jobid in run['metadata']['jobs']:
        if jobid in run['metadata']['attempted_jobs']:continue
        job=requests[jobid];index=job['source_index'];run['metadata']['attempted_jobs'].append(jobid);r.atomic_write_json(target,run)
        raw=None
        try:
            raw=r.student_call(client,job['rendered_prompt'],r.DEFAULT_MODEL,config)
            if r.has_generated_thinking(raw):raise ValueError('Thinking output forbidden')
            output,error=r.parse_student_response(raw['content'])
            run['responses'][jobid]={'source_index':index,'bank_key':job['bank_key'],'condition':'bank','arm':job['arm'],'public_evidence':job['public_evidence'],'evidence_hash':job['evidence_hash'],'prompt':prompt_name,'prompt_hash':run['metadata']['student_prompt_hash'],'model':r.DEFAULT_MODEL,'sampling':asdict(config),'output':output,'format_error':error,'request':{k:v for k,v in raw.items() if k!='content'},'raw_content':raw['content'],'rendered_input_hash':job['rendered_input_hash']}
            print(jobid,'completed',raw['elapsed_seconds'],flush=True)
        except Exception as exc:r.failure(run,'student',index,jobid,exc,raw);print(jobid,'FAILED',str(exc),flush=True)
        r.atomic_write_json(target,run)
    print('All declared AA local slots terminal',flush=True)
if __name__=='__main__':main()
