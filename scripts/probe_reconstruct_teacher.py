#!/usr/bin/env python3
"""Source-blind stronger-model feasibility probe on four preselected public inputs."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project.reconstruct import (deepinfra_client, load_prompt, render_template, stable_hash,
    teacher_call, parse_student_response, reserve_teacher_request, failure)
from anlp_project.storage import atomic_write_json


def public_probe_inputs(run):
    inputs = {}
    for row in run['responses'].values():
        bank = run['banks'].get(row.get('bank_key'), {})
        if (row['source_index'] in [11,22,30,49] and row['prompt']=='student_p1'
            and row['sampling']['seed']==0 and bank.get('prompt')=='role_sparse_2'):
            inputs[row['source_index']] = row['public_evidence']
    if sorted(inputs) != [11,22,30,49]:
        raise ValueError('Missing registered public probe input')
    return inputs


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args()
    inputs = public_probe_inputs(json.loads(a.base.read_text()))
    model = 'deepseek-ai/DeepSeek-V4.1-Flash'
    template = load_prompt('student_p1')
    run = json.loads(a.output.read_text()) if a.output.exists() else {
        'metadata': {'study':'amendment G teacher feasibility, not independent gold',
                     'base_artifact':str(a.base),'student_template':'student_p1',
                     'template_hash':stable_hash(template)},
        'banks':{}, 'teacher_reconstructions':{}, 'failures':[]}
    client = deepinfra_client(180)
    for index, evidence in sorted(inputs.items()):
        prompt = render_template(template, {'FINAL_ANSWER':evidence['final_answer'],
                                           'RENDERED_CLUES':evidence['rendered_clues']})
        key = f'{index}:{stable_hash(prompt)}:{model}:low'
        if key in run['teacher_reconstructions']:
            continue
        raw = None
        try:
            reserve_teacher_request(run,prompt,8192,1.)
            raw = teacher_call(client,prompt,model,8192,'low')
            output, flag = parse_student_response(raw['content'])
            run['teacher_reconstructions'][key] = {
                'source_index':index,'model':model,'reasoning_effort':'low','max_tokens':8192,
                'public_evidence':evidence,'rendered_prompt':prompt,'output':output,
                'format_error':flag,'raw_content':raw['content'],
                'request':{k:v for k,v in raw.items() if k!='content'}}
            print(f'teacher-public {index}: saved',flush=True)
        except Exception as exc:
            failure(run,'teacher_reconstruction',index,key,exc,raw)
            print(f'teacher-public {index}: failed: {exc}',flush=True)
        atomic_write_json(a.output,run)


if __name__ == '__main__':
    main()
