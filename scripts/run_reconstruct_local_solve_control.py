#!/usr/bin/env python3
"""Run four fixed exact historical SOLVE prompts on current local Qwen."""
import json
from pathlib import Path
from anlp_project.reconstruct import local_client, student_call, SamplingConfig, has_generated_thinking, stable_hash
from anlp_project.solution_verification import verify_record
from anlp_project.storage import atomic_write_json


def main():
    p=Path('artifacts/reconstruct/d3-v2/local-solve-control.json')
    if p.exists():raise ValueError('One registered attempt per source; refuse rerun')
    historical=json.load(open('artifacts/qwen3-4b/solve/113/reevaluated-v2-results.json'))
    sources={r['source_index']:r for r in historical['results'] if r['source_index'] in [8,27,33,77]}
    assert sorted(sources)==[8,27,33,77]
    config=SamplingConfig(max_tokens=8192,seed=0)
    run={'metadata':{'study':'matched local SOLVE diagnostic','model':'Qwen/Qwen3-4B',
         'quantization':'Q4_K_M','thinking':False,'seed':0,'max_tokens':8192,
         'historical_backend':'vllm','historical_generation_seed':'not recorded',
         'comparison_limitation':'four sources; backend, quantization and draw differences not isolated'},'results':[]}
    client=local_client(timeout=300)
    for index,source in sources.items():
        row={'source_index':index,'question':source['question'],'final_answer':source['final_answer'],
             'prompt':source['prompt'],'prompt_hash':stable_hash(source['prompt']),
             'historical_verification':source['verification']}
        try:
            raw=student_call(client,source['prompt'],'Qwen/Qwen3-4B',config)
            if has_generated_thinking(raw):raise ValueError('Unexpected generated thinking')
            row.update(raw=raw,solve_solution=raw['content'],status='completed')
            row['verification']=verify_record(row)
            print(index,row['verification']['answer_status'],row['verification']['extracted_final_answer'],flush=True)
        except Exception as exc:
            row.update(status='failed',error=f'{type(exc).__name__}: {exc}')
            print(index,'FAILED',str(exc),flush=True)
        run['results'].append(row)
        atomic_write_json(p,run)


if __name__=='__main__':main()
