"""One Llama GRPO arm inside one Turing job: train, choose the checkpoint on dev, evaluate it on the three test sets.

Replicates the Qwen study's chains with the Llama evaluation flags:
- JUDGE / RECONSTRUCT (scripts/turing/drgrpo_post.sh): train 104 steps; dev on the arm's own task at steps
  26/52/78/104 (scripts/select_dev_checkpoint.py rule); test of the selected step, and of step 104 if different.
  RECONSTRUCT dev scores come from the Gemma reward judge in place of Jev.
- SOLVE (scripts/solve_grpo_pipeline.sh): the two 8-step LR probes (probes.py), then the winner continued from
  step 8 with its optimizer state to step 106; candidates = last step, best by 8-step rolling reward, best
  every-8 step by rolling reward; dev 200 x 4 (scripts/select_solve_step.py); test of the selected step.
27B judging of the JUDGE / RECONSTRUCT test answers runs separately, on node06 (it holds the 27B).

    python phase2/llama_transfer/arm.py judge|reconstruct|solve
"""
import argparse
import importlib.util
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'phase2/llama_transfer'))
from probes import run_training  # noqa: E402

BASE = Path('/scratch/mukund.hebbar/llama-transfer')
MODEL = BASE / 'models/llama'
GEMMA = '/scratch/mukund.hebbar/local-judge-calibration/models/gemma'
CALIBRATION = ROOT / 'phase2/results/local-judge-calibration/gemma-full-explicit'
PROBES = BASE / 'runs/llama3b-probes-20261028'
LLAMA = ['--model', 'meta-llama/Llama-3.2-3B-Instruct', '--model-path', str(MODEL), '--chat-mode', 'instruct',
         '--first-cap', '16384', '--max-cap', '32768', '--samples', '4', '--samples-tasks', 'solve']


def log(msg):
    print(msg, flush=True)


def evaluate(name, adapter, out, gpus, split, tasks):
    if (out / 'done').exists():
        return
    cmd = [sys.executable, str(ROOT / 'scripts/turing/eval_matrix.py'), '--name', name, '--out', str(out),
           '--split', split, '--tasks', tasks, *LLAMA] + (['--adapter', str(adapter)] if adapter else [])
    with open(f'{out}.log', 'w') as fh:
        subprocess.run(cmd, env={**os.environ, 'CUDA_VISIBLE_DEVICES': gpus}, stdout=fh, stderr=fh, check=True)


def in_pairs(jobs, gpus, task):  # dev evaluations [(name, adapter, out)], one per GPU at a time
    with ThreadPoolExecutor(len(gpus)) as pool:
        for i in range(0, len(jobs), len(gpus)):
            list(pool.map(lambda jg: evaluate(*jg[0], jg[1], 'dev', task), zip(jobs[i:i + len(gpus)], gpus)))


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def gemma_reconstruct_metric(gpu, out):
    """select_dev_checkpoint's RECONSTRUCT metric (score_100 on sample 0) with the Gemma reward judge."""
    import statistics as st
    from anlp_project import jev_judging as jj
    from anlp_project.gemma_judging import GemmaJudge
    from anlp_project.opd import slice_rows
    from anlp_project.opd_train import serve, wait_ready
    server = serve(GEMMA, 'reward-judge', 8102, gpu, ['--gpu-memory-utilization', '0.90', '--max-model-len', '40960',
                   '--max-num-seqs', '32', '--max-logprobs', '256'], out, {})
    wait_ready(8102, server, 'reward-judge', out)
    judge = GemmaJudge(GEMMA, CALIBRATION, 8102)
    rows = {r['uid']: r for r in slice_rows('reconstruct', 'dev')}

    def metric(d):
        path = d / 's0' / 'judged-scores.gemma.jsonl'
        if not path.exists():
            resp = [json.loads(l) for l in (d / 's0' / 'responses.jsonl').open()]
            resp = [x for x in resp if x['uid'] in rows]

            def work(x):
                rec = jj.reconstruct_answer(rows[x['uid']], x['text'], judge, None)
                return jj.score_record(rows[x['uid']], x['text'], rec, judge.cutoffs)
            with ThreadPoolExecutor(16) as pool:
                scored = list(pool.map(work, resp))
            path.write_text(''.join(json.dumps(o, ensure_ascii=False) + '\n' for o in scored))
        xs = [json.loads(l) for l in path.open()]
        return st.mean(x['score_100'] for x in xs), len(xs)
    return metric, server


def judge_or_reconstruct(task, gpus):
    run = BASE / f'runs/llama3b-{task}'
    if not (run / 'result-0.json').exists():
        log(f'training {task}')
        run_training([sys.executable, str(ROOT / 'phase2/llama_transfer/run.py'), '--arm', task,
                      '--model-path', str(MODEL), '--out', str(run)], run / 'result-0.json', steps=None, limit=20 * 3600)
    log(f"trained: {json.loads((run / 'result-0.json').read_text())['steps_done']} steps")
    dev = run / 'post/dev'
    dev.mkdir(parents=True, exist_ok=True)
    steps = [k for k in (26, 52, 78, 104) if (run / f'adapters/step{k}/adapter_model.safetensors').exists()]
    in_pairs([(f'llama-{task}-dev-step{k}', run / f'adapters/step{k}', dev / f'{task}-step{k}') for k in steps], gpus[:2], task)
    sel = script('select_dev_checkpoint')
    server = None
    if task == 'reconstruct':
        sel.METRIC['reconstruct'], server = gemma_reconstruct_metric(gpus[2], run / 'post')
    try:
        scores = {k: sel.METRIC[task](dev / f'{task}-step{k}') for k in steps}
    finally:
        if server is not None:
            server.terminate()
            server.wait()
    best = max(scores, key=lambda k: (round(scores[k][0], 6), k))  # ties -> later step
    (dev / 'selection.json').write_text(json.dumps({
        'rule': 'best own-task dev score among steps 26/52/78/104; ties -> later step' +
                ('; RECONSTRUCT scored by the Gemma reward judge' if task == 'reconstruct' else ''),
        task: {'selected_step': best, 'dev_scores': {str(k): v[0] for k, v in scores.items()},
               'n': {str(k): v[1] for k, v in scores.items()}}}, indent=1) + '\n')
    log(f'{task} dev {dict((k, round(v[0], 4)) for k, v in scores.items())} -> step {best}')
    for k in dict.fromkeys([best, max(steps)]):
        evaluate(f'llama-{task}-test-step{k}', run / f'adapters/step{k}', run / f'post/test-step{k}', ','.join(gpus),
                 'test', 'solve,judge,reconstruct')
        log(f'test evaluated: step {k}')


def solve(gpus):
    if not (PROBES / 'done').exists():
        subprocess.run([sys.executable, str(ROOT / 'phase2/llama_transfer/probes.py'), '--out', str(PROBES)], check=True)
    chosen = json.loads((PROBES / 'lr-selection.json').read_text())['selected']
    log(f"LR probes: {chosen['arm']} (lr {chosen['lr']}, dev {chosen['mean_dev_accuracy']:.4f})")
    run = BASE / 'runs/llama3b-solve'
    if not (run / 'metrics.jsonl').exists():  # continue inside a copy of the winning probe: metrics.jsonl, best.json span all steps
        if run.exists():  # launch.py creates runs/<job name> before the job starts; keep anything else in it aside
            run.rename(run.with_name(f'{run.name}-aside-{int(time.time())}'))
        shutil.copytree(PROBES / chosen['arm'], run)
    if not (run / 'result-8.json').exists():
        log('training solve from step 8')
        run_training([sys.executable, str(ROOT / 'phase2/llama_transfer/run.py'), '--arm', 'solve', '--lr', str(chosen['lr']),
                      '--model-path', str(MODEL), '--out', str(run), '--resume-from', str(run / 'adapters/step8'),
                      '--start-step', '8'], run / 'result-8.json', steps=None, limit=20 * 3600)
    rewards = [json.loads(l)['reward_mean'] for l in (run / 'metrics.jsonl').open()]
    final = len(rewards)
    roll = lambda k: sum(rewards[k - 8:k]) / 8 if k >= 8 else -1  # noqa: E731
    cands = {final: run / f'adapters/step{final}'}
    if (run / 'best.json').exists():
        top = json.loads((run / 'best.json').read_text())[0]['step']
        cands.setdefault(top, run / f'adapters/best-step{top}')
    every8 = [k for k in range(8, final + 1, 8) if (run / f'adapters/step{k}').exists()]
    if every8:
        k = max(every8, key=roll)
        cands.setdefault(k, run / f'adapters/step{k}')
    log(f'candidates: {sorted(cands)}')
    dev = run / 'post/dev'
    dev.mkdir(parents=True, exist_ok=True)
    in_pairs([('llama-solve-dev-base', None, run / 'post/dev-base')] +
             [(f'llama-solve-dev-step{k}', a, dev / f'step{k}') for k, a in sorted(cands.items())], gpus, 'solve')
    subprocess.run([sys.executable, str(ROOT / 'scripts/select_solve_step.py'), str(dev), str(run / 'post/dev-base')], check=True)
    best = json.loads((dev / 'selection.json').read_text())['selected_step']
    (run / 'post/selected-adapter').write_text(str(cands[best]) + '\n')
    evaluate(f'llama-solve-test-step{best}', cands[best], run / f'post/test-step{best}', ','.join(gpus),
             'test', 'solve,judge,reconstruct')
    log(f'solve: selected step {best}, test evaluated')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('task', choices=['solve', 'judge', 'reconstruct'])
    a = ap.parse_args()
    gpus = os.environ['CUDA_VISIBLE_DEVICES'].split(',')
    solve(gpus) if a.task == 'solve' else judge_or_reconstruct(a.task, gpus)
    log(f'LLAMA_ARM_COMPLETE {a.task}')


if __name__ == '__main__':
    main()
