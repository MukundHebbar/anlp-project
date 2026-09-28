#!/usr/bin/env python3
"""Bounded parallel teacher stages using the existing runner and one artifact writer.

All arguments after -- are standard run_reconstruct arguments. Example:
  ... --workers 4 -- evaluate --output run.json --split D2 --evaluate-prompt evaluate_p2
"""
import copy
import fcntl
import json
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from argparse import ArgumentParser

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project import reconstruct as r


def retryable_evaluation_jobs(run, jobs, prompt_hash, model, effort):
    attempts = Counter(item['key'] for item in run.get('failures', []) if item['stage']=='evaluate')
    result = []
    for response_key, index in jobs:
        key = f'{response_key}:{prompt_hash}:{model}:{effort}'
        if attempts[key] == 1 and key not in run.get('evaluations', {}):
            result.append((response_key,index))
    return result


def retryable_audit_jobs(run, jobs, bank_prompt, prompt_hash, model, effort):
    attempts = Counter(item['key'] for item in run.get('failures', []) if item['stage']=='audit')
    result = []
    for _, index in jobs:
        _, bank = r.latest_bank(run, index, bank_prompt)
        key = f"{index}:{r.stable_hash(bank['output'])}:{prompt_hash}:{model}:{effort}"
        if attempts[key] == 1 and key not in run.get('audits', {}):
            result.append((None, index))
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--retry-failed-once', action='store_true',
                        help='Evaluate/audit only unresolved requests with exactly one recorded technical failure')
    parser.add_argument('runner_args', nargs='*')
    cut = sys.argv.index('--')
    outer = parser.parse_args(sys.argv[1:cut])
    args = r.parse_args(sys.argv[cut+1:])
    functions = {'evaluate':r.evaluate_responses, 'recover':r.source_recovery_responses,
                 'convert':r.convert_sources, 'audit':r.audit_sources,
                 'validate-judge':r.validate_judge_fixtures,'copy-challenge':r.copy_challenge_sources}
    sections = {'evaluate':'evaluations', 'recover':'source_recovery', 'convert':'banks', 'audit':'audits',
                'validate-judge':'judge_fixtures','copy-challenge':'copy_challenges'}
    if args.command not in functions or not 1 <= outer.workers <= 4:
        raise ValueError('Use convert/audit/evaluate/recover/validate-judge and 1..4 workers')
    lock_path = args.output.with_suffix(args.output.suffix+'.lock')
    with lock_path.open('w') as lock, tempfile.TemporaryDirectory(prefix='reconstruct-batch-') as tmp:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        run = json.loads(args.output.read_text())
        indices = r.selected_indices(run, args.split, args.limit, args.indices)
        section = sections[args.command]
        run.setdefault(section, {})
        jobs = [(None, i) for i in indices]
        if args.command in {'evaluate','recover'}:
            jobs = [(k,v['source_index']) for k,v in run['responses'].items() if v['source_index'] in indices]
        if outer.retry_failed_once:
            if args.command not in {'evaluate','audit'} or args.force:
                raise ValueError('Bounded retry requires evaluate or audit without --force')
            if args.command == 'evaluate':
                jobs = retryable_evaluation_jobs(run,jobs,r.stable_hash(r.load_prompt(args.evaluate_prompt,args.prompt_dir)),
                                                 args.teacher_model,args.reasoning_effort)
            else:
                jobs = retryable_audit_jobs(run,jobs,args.bank_prompt,
                    r.stable_hash(r.load_prompt(args.audit_prompt,args.prompt_dir)),
                    args.teacher_model,args.reasoning_effort)
            print(f'Bounded technical retry: {len(jobs)} unresolved requests; scored outputs untouched',flush=True)
        if args.command == 'validate-judge':
            jobs = [(fixture,-1) for fixture in json.loads(args.fixtures.read_text())['fixtures']]
        # Reserve the whole submitted batch, including cached/filtered jobs, using
        # the project's conservative pricing ceiling; do not parallelize past it.
        maximum_input_chars = max((len(json.dumps(s)) for s in run['sources'].values()), default=0)
        reserve = len(jobs)*((maximum_input_chars/4*0.20 + args.teacher_max_tokens*0.60)/1_000_000)
        if r.actual_cost(run)+reserve > args.max_cost_usd:
            raise RuntimeError('Whole-batch reserve exceeds cost ceiling')
        snapshot = copy.deepcopy(run)
        def worker(position, key, index):
            local = copy.deepcopy(snapshot)
            local['failures'] = []
            if args.command in {'evaluate','recover'}:
                local['responses'] = {key:local['responses'][key]}
            options = copy.copy(args)
            options.output = Path(tmp)/f'{position}.json'
            if args.command == 'validate-judge':
                options.fixtures = Path(tmp)/f'fixture-{position}.json'
                options.fixtures.write_text(json.dumps({'fixtures':[key]}))
                functions[args.command](options, local)
            else:
                functions[args.command](options, local, [index])
            changes = {k:v for k,v in local[section].items() if k not in snapshot[section] or v != snapshot[section][k]}
            return changes, local['failures']
        with ThreadPoolExecutor(max_workers=outer.workers) as pool:
            futures = [pool.submit(worker, n,k,i) for n,(k,i) in enumerate(jobs)]
            for future in as_completed(futures):
                changes, failures = future.result()
                run[section].update(changes)
                run['failures'].extend(failures)
                r.atomic_write_json(args.output,run)
        print(json.dumps({'stage':args.command,'records':len(run[section]),'failures':len(run['failures']),
                          'recorded_cost_usd':r.actual_cost(run)}))


if __name__=='__main__':
    main()
