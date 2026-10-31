"""Run one explicit Llama GRPO arm inside an allocated Turing job; never submits jobs itself."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
MODEL = 'meta-llama/Llama-3.2-3B-Instruct'
REVISION = '0cb88a4f764b7a12671c53f0838cd831a0843b95'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--arm', choices=['solve-probe-low', 'solve-probe-high', 'solve', 'judge', 'reconstruct'], required=True)
    parser.add_argument('--model-path', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--judge-path', default='/scratch/mukund.hebbar/local-judge-calibration/models/gemma')
    parser.add_argument('--calibration-dir', default=str(ROOT / 'phase2/results/local-judge-calibration/gemma-full-explicit'))
    parser.add_argument('--steps', type=int, default=0, help='shorten a run for a smoke test')
    parser.add_argument('--resume-from')
    parser.add_argument('--start-step', type=int, default=0)
    parser.add_argument('--lr', type=float, help='the SOLVE LR chosen by the probes (lr-selection.json)')
    parser.add_argument('--student-port', type=int, default=8100)
    parser.add_argument('--judge-port', type=int, default=8102)
    args = parser.parse_args()
    provenance = json.loads((ROOT / 'phase2/llama_transfer/provenance.json').read_text())
    for relative, expected in provenance['files'].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            parser.error(f'Code/config changed since the reviewed snapshot: {relative}')
    cfg = json.loads((ROOT / 'phase2/llama_transfer/configs' / (args.arm + '.json')).read_text())
    task, planned = cfg.pop('task'), cfg.pop('planned_steps')
    if args.lr:
        cfg['optimizer']['lr'] = args.lr
    steps = args.steps or planned - args.start_step
    if not 0 < steps <= planned - args.start_step:
        parser.error('steps must fit the planned schedule')
    if bool(args.start_step) != bool(args.resume_from):
        parser.error('resume requires both --resume-from and a positive --start-step')
    source = json.loads((Path(args.model_path) / 'source.json').read_text())
    if source['model'] != MODEL or source['revision'] != REVISION:
        parser.error('student path must be the verified pinned Llama download')
    gpus = os.environ.get('CUDA_VISIBLE_DEVICES', '').split(',')
    needs_judge = task != 'solve'
    if len([g for g in gpus if g]) < (3 if needs_judge else 2):
        parser.error('allocate 2 GPUs for SOLVE, 3 for JUDGE/RECONSTRUCT (including Gemma)')
    # Set before any transformers/torch import; vLLM's child gets the rollout GPU explicitly.
    os.environ['CUDA_VISIBLE_DEVICES'] = gpus[1]
    from anlp_project import opd
    from anlp_project.opd_train import run_opd, serve, wait_ready
    from anlp_project.student_models import family
    import torch
    torch.manual_seed(cfg['seed'])
    if family(args.model_path) != 'llama':
        parser.error('expected Llama model_type')
    cfg.update(reward_judge_path=args.judge_path, reward_calibration_dir=args.calibration_dir,
               reward_judge_port=args.judge_port)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'config.json').exists() and not args.resume_from:
        parser.error('output already contains a run; use a fresh output or explicit resume')
    (out / 'code-provenance.json').write_text(json.dumps(provenance, indent=2))
    # Use the same seeded historical train order, which excludes the 200-item development slice.
    b = cfg['prompts_per_step']
    prompts = opd.matrix_prompts(task, (args.start_step + steps)*b)[args.start_step*b:]
    if len(prompts) != steps*b:
        raise RuntimeError('insufficient training prompts')
    judge = None
    try:
        if needs_judge:
            judge = serve(args.judge_path, 'reward-judge', args.judge_port, gpus[2],
                          ['--gpu-memory-utilization', '0.90', '--max-model-len', '40960',
                           '--max-num-seqs', '32', '--max-logprobs', '256'], out, {})
            wait_ready(args.judge_port, judge, 'reward-judge', out)
        result = run_opd(task, prompts, cfg, out, args.model_path, None, steps=steps,
                         meta={'platform': 'turing-l40s', 'arm': args.arm, 'student_revision': REVISION,
                               'reward_judge_revision': '707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7',
                               'reward_judge_limitations_accepted': True,
                               'final_evaluator': 'Qwen/Qwen3.8-27B'},
                         student_gpu=gpus[0], trainer_gpu=gpus[1], student_mem=.88,
                         student_port=args.student_port, resume_from=args.resume_from,
                         start_step=args.start_step, save_optimizer=True,
                         keep_steps=(8, 26, 52, 78, 104, 106))
        (out / f'result-{args.start_step}.json').write_text(json.dumps(result, indent=2))
        if not result['ok']:
            raise RuntimeError(result['error'])
    finally:
        if judge is not None:
            judge.terminate()
            try:
                judge.wait(timeout=60)
            except Exception:
                judge.kill()
                judge.wait()


if __name__ == '__main__':
    main()
