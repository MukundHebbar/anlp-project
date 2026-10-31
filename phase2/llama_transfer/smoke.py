"""Actual Gemma server parity and one Llama GRPO update before the scheduled experiments."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    from anlp_project.opd_train import serve,wait_ready
    from anlp_project.gemma_judging import GemmaJudge
    gpus=os.environ['CUDA_VISIBLE_DEVICES'].split(',')
    model='/scratch/mukund.hebbar/local-judge-calibration/models/gemma'
    server=serve(model,'reward-judge',8102,gpus[2],
                 ['--gpu-memory-utilization','0.90','--max-model-len','40960',
                  '--max-num-seqs','32','--max-logprobs','256'],out,{})
    try:
        wait_ready(8102,server,'reward-judge',out)
        judge=GemmaJudge(model,ROOT/'phase2/results/local-judge-calibration/gemma-full-explicit',8102)
        differences=[]
        for line in (ROOT/'local/llama-transfer/reward-parity.jsonl').open():
            r=json.loads(line)
            actual=judge.call(r['state'],r['questions'])['answers']
            for name, expected in r['expected'].items():
                got=actual[name]
                field='probabilities' if 'probabilities' in expected else None
                delta=(max(abs(got[field][key]-value) for key,value in expected[field].items())
                       if field else abs(got['noul']-expected['noul']))
                if expected['type']=='score':
                    scale=len(expected['probabilities'])-1
                    normalized_drift=abs(got['score']-expected['score'])/scale
                    passed=normalized_drift<=.01
                elif expected['type']=='noul':
                    normalized_drift=delta
                    passed=delta<=.03 and (got['noul']>.5)==(expected['noul']>.5)
                else:
                    normalized_drift=delta
                    passed=delta<=.03 and got['choice']==expected['choice']
                differences.append({'key':r['key'],'question':name,'max_probability_difference':delta,
                                    'normalized_score_difference':normalized_drift,'passed':passed,
                                    'expected':expected,'actual':got,'mass':got['mass']})
        maximum=max(r['max_probability_difference'] for r in differences)
        (out/'reward-parity.json').write_text(json.dumps({'questions':len(differences),
             'max_probability_difference':maximum,
             'criteria':'score: expected rubric value within 1% of range; choice/noul: probability within .03 and same decision',
             'rows':differences},indent=2))
        if not all(r['passed'] for r in differences):
            raise RuntimeError('Gemma transport changed an expected score or categorical decision beyond tolerance')
    finally:
        server.terminate()
        try:server.wait(timeout=60)
        except subprocess.TimeoutExpired:
            server.kill();server.wait()
    subprocess.run([sys.executable,str(ROOT/'phase2/llama_transfer/run.py'),
        '--arm','solve-probe-low','--steps','1',
        '--model-path','/scratch/mukund.hebbar/llama-transfer/models/llama',
        '--out',str(out/'llama-update')],check=True)
    metric=json.loads((out/'llama-update/metrics.jsonl').read_text().splitlines()[-1])
    if metric['update_skipped'] or metric['rollouts_used']==0 or metric['grad_norm']<=0:
        raise RuntimeError('Smoke run had no actual backpropagation/update signal')
    (out/'done').write_text('ok\n')
    print('LLAMA_GEMMA_SMOKE_COMPLETE',flush=True)


if __name__=='__main__':main()
