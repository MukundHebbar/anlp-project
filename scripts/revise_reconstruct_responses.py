#!/usr/bin/env python3
"""Second-pass local Qwen revision with no private source or teacher feedback."""
import argparse
import copy
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import (SamplingConfig,local_client,student_call,load_prompt,render_template,
    stable_hash,parse_student_response,has_generated_thinking,failure)
from anlp_project.storage import atomic_write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--split',default='D2');a=p.parse_args()
    base=json.loads(a.base.read_text())
    run=json.loads(a.output.read_text()) if a.output.exists() else copy.deepcopy(base)
    template=load_prompt('student_p8_revision');client=local_client(timeout=180)
    chosen=[]
    for key,row in base['responses'].items():
        bank=base['banks'].get(row.get('bank_key'),{})
        if (row['source_index'] in base['partitions'][a.split] and row['prompt']=='student_p1'
            and bank.get('prompt')=='convert_p2' and row['public_evidence'].get('disclosure')=='medium'
            and row['public_evidence'].get('selection_policy','random')=='random'
            and row['public_evidence']['clue_count']==len(bank['output']['clues'])):
            chosen.append((key,row))
    for n,(parent,row) in enumerate(chosen,1):
        prompt_hash=stable_hash({'template':template,'parent_key':parent,'draft':row['raw_content']})
        config=SamplingConfig(**row['sampling'])
        key=f"{row['source_index']}:{row['evidence_hash']}:{prompt_hash}:{row['model']}:{stable_hash(asdict(config))}"
        if key in run['responses']:continue
        prompt=render_template(template,{'FINAL_ANSWER':row['public_evidence']['final_answer'],
            'RENDERED_CLUES':row['public_evidence']['rendered_clues'],'DRAFT':row['output']})
        raw=None
        try:
            raw=student_call(client,prompt,row['model'],config)
            if has_generated_thinking(raw):raise RuntimeError('Thinking mode unexpectedly active')
            output,flag=parse_student_response(raw['content'])
            result=copy.deepcopy(row)
            result.update({'prompt':'student_p8_revision','prompt_hash':prompt_hash,'prompt_template_hash':stable_hash(template),
                'parent_response_key':parent,'pipeline_calls':2,'output':output,'format_error':flag,
                'raw_content':raw['content'],'request':{k:v for k,v in raw.items() if k!='content'},
                'pipeline_completion_tokens':(row['request'].get('usage',{}).get('completion_tokens',0)
                     +raw.get('usage',{}).get('completion_tokens',0))})
            run['responses'][key]=result
            print(f'revision {n}/{len(chosen)} source={row["source_index"]} seed={config.seed}: saved',flush=True)
        except Exception as exc:
            failure(run,'student_revision',row['source_index'],key,exc,raw)
            print(f'revision {n}/{len(chosen)} failed: {exc}',flush=True)
        atomic_write_json(a.output,run)


if __name__=='__main__':main()
