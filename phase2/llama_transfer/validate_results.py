"""Validate the published Llama evidence offline, without starting models or calling APIs."""
import argparse
import gzip
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def records(path):
    path=Path(path)
    if not path.exists():path=path.with_name(path.name+'.gz')
    with (gzip.open(path,'rt') if path.suffix=='.gz' else path.open()) as stream:
        return [json.loads(line) for line in stream]


def unique(rows):
    keys=[(r['task'],r['uid']) for r in rows]
    assert len(keys)==len(set(keys)),'duplicated task/UID'
    return set(keys)


def validate(base):
    selection=json.loads((base/'selection.json').read_text())
    assert selection=={'judge':78,'reconstruct':104,'solve':106},selection
    test_ids={task:{r['uid'] for r in records(ROOT/f'data/manifests/final-v3/{task}-test.jsonl.gz')}
              for task in ('solve','judge','reconstruct')}
    assert all(len(ids)==400 for ids in test_ids.values())
    expected_models={'llama3b-base','llama3b-grpo-solve-step106','llama3b-grpo-judge-step78',
                     'llama3b-grpo-judge-step104','llama3b-grpo-reconstruct-step104'}
    assert {p.name for p in (base/'test').iterdir() if p.is_dir()}==expected_models
    model_summary={}
    for name in sorted(expected_models):
        folder=base/'test'/name
        correct=[]
        for sample in range(4):
            target=folder/f's{sample}'
            expected={(task,uid) for task,ids in test_ids.items() if sample==0 or task=='solve' for uid in ids}
            scores=records(target/'scores.jsonl');responses=records(target/'responses.jsonl')
            assert unique(scores)==expected,(name,sample,'scores')
            assert unique(responses)==expected,(name,sample,'responses')
            metadata=json.loads((target/'metadata.json').read_text())
            assert metadata['model']=='meta-llama/Llama-3.2-3B-Instruct'
            assert metadata['chat_mode']=='instruct'
            assert metadata['sampling']['temperature']==1 and metadata['sampling']['top_p']==1
            assert metadata['sampling']['top_k']==0
            assert metadata['two_pass']['first_cap']==16384 and metadata['two_pass']['max_cap']==32768
            correct.extend(bool(row['correct_strict']) for row in scores if row['task']=='solve')
        expected={(task,uid) for task in ('judge','reconstruct') for uid in test_ids[task]}
        judged=records(folder/'s0/judged-scores.qwen.jsonl')
        calls=records(folder/'s0/judgments.qwen.jsonl')
        assert unique(judged)==expected and unique(calls)==expected,name
        assert all(row.get('score_100') is not None and 0<=row['score_100']<=100 for row in judged),name
        model_summary[name]={'solve_responses':len(correct),'mean_strict_solve_accuracy':sum(correct)/len(correct),
                             'final_qwen_scored':len(judged)}
    training_summary={}
    for task,total in [('solve',106),('judge',104),('reconstruct',104)]:
        folder=base/'training'/task
        cfg=json.loads((folder/'config.json').read_text())
        assert cfg['method']=='grpo' and cfg['seed']==0 and cfg['student']=='meta-llama/Llama-3.2-3B-Instruct'
        assert cfg['optimizer']['lr']==(2e-5 if task=='solve' else 5e-5)
        assert cfg['lora']['r']==64 and cfg['lora']['alpha']==64
        metrics=records(folder/'metrics.jsonl')
        assert [r['step'] for r in metrics]==list(range(1,total+1)),task
        result=json.loads((folder/('result-8.json' if task=='solve' else 'result-0.json')).read_text())
        assert result['ok'] and result['steps_done']==total-(8 if task=='solve' else 0),task
        train_ids=set(json.loads((folder/'train-uids.json').read_text()))
        order=json.loads((ROOT/f'data/manifests/final-v3/opd-matrix-{task}.json').read_text())['uids']
        dev_ids=set(json.loads((ROOT/f'data/manifests/final-v3/opd-trial-{task}.json').read_text())['uids']['dev'])
        assert train_ids==set(order[:total*cfg['prompts_per_step']]),task
        assert not train_ids&dev_ids and not train_ids&test_ids[task],task
        candidates=(folder/'dev').glob('step*' if task=='solve' else f'{task}-step*')
        for candidate in candidates:
            if not candidate.is_dir():continue
            for sample in range(4 if task=='solve' else 1):
                rows=records(candidate/f's{sample}/scores.jsonl')
                assert unique(rows)=={(task,uid) for uid in dev_ids},str(candidate)
        dev_selection=json.loads((folder/'dev/selection.json').read_text())
        own=dev_selection if task=='solve' else dev_selection[task]
        assert own['selected_step']==selection[task]
        if task=='solve':
            best=max(own['steps'],key=lambda k:(own['steps'][k]['dev_acc'],int(k)))
        else:
            best=max(own['dev_scores'],key=lambda k:(round(own['dev_scores'][k],6),int(k)))
        assert int(best)==selection[task]
        training_summary[task]={'updates':total,'train_questions':len(train_ids),
                               'dev_questions':len(dev_ids),'selected_step':selection[task]}
    probes=json.loads((base/'training/probes/lr-selection.json').read_text())
    accuracies=[]
    for suffix in ('low','high'):
        values=[]
        for sample in range(4):
            rows=records(base/f'training/probes/dev-{suffix}/s{sample}/scores.jsonl')
            assert unique(rows)=={('solve',uid) for uid in
                                    json.loads((ROOT/'data/manifests/final-v3/opd-trial-solve.json').read_text())['uids']['dev']}
            values.extend(bool(r['correct_strict']) for r in rows)
        accuracies.append(sum(values)/len(values))
    assert accuracies==[r['mean_dev_accuracy'] for r in probes['candidates']]
    winner=max(probes['candidates'],key=lambda r:(r['mean_dev_accuracy'],-r['lr']))
    assert probes['selected']==winner and winner['lr']==2e-5 and probes['test_used_for_selection'] is False
    return {'status':'passed','models':model_summary,'training':training_summary,
            'probe_mean_dev_accuracy':{'1e-5':accuracies[0],'2e-5':accuracies[1]},
            'new_training_or_api_calls':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base',type=Path,default=ROOT/'artifacts/baselines/llama3b')
    parser.add_argument('--out',type=Path);args=parser.parse_args()
    result=validate(args.base)
    text=json.dumps(result,indent=2)+'\n'
    if args.out:args.out.write_text(text)
    print(text)


if __name__=='__main__':main()
