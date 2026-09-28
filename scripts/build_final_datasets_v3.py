#!/usr/bin/env python3
"""FINAL-v3 = FINAL-v2 plus a uniform `training` block on every row. No API calls, no row changes.

training = {input, chain_of_thought, final_answer}
  solve        question                          -> r1_solution_1 (full DeepMath R1 CoT), final answer
  judge        problem + proposed solution + instr -> no CoT in the source data,  friend's teacher response
  reconstruct  final answer + 4 clues            -> r1_solution_1 of the original problem, original question
"""
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

SRC = Path('data/manifests/final-v2')
OUT = Path('data/manifests/final-v3')


def render_clues(clues):
    return '\n'.join(f'{n}. {c}' for n, c in enumerate(clues, 1))


def training_block(x):
    if x['task'] == 'solve':
        return dict(input=x['question'], chain_of_thought=x['reference_solutions'][0], final_answer=x['final_answer'])
    if x['task'] == 'judge':
        p = x['public']
        steps = '\n'.join(f"{s['step_id']}: {s['text']}" for s in p['proposed_solution'])
        return dict(input=f"Problem:\n{p['problem']}\n\nProposed solution:\n{steps}\n\n{p['instruction']}",
                    chain_of_thought=None, final_answer=x['private']['teacher_target_response'])
    pi = x['public_input']
    return dict(input=f"Final answer: {pi['final_answer']}\nObservations:\n{render_clues(pi['clues'])}",
                chain_of_thought=x['reference_solutions'][0], final_answer=x['question'])


def deepmath_answers():
    files = sorted(Path('data/datasets/deepmath-103k').glob('train-*-of-00010.parquet'))
    return [a for f in files for a in pq.read_table(f, columns=['final_answer']).column('final_answer').to_pylist()]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw_answers = deepmath_answers()
    for task in ('solve', 'judge', 'reconstruct'):
        for split in ('train', 'test'):
            with (SRC / f'{task}-{split}.jsonl').open() as src, (OUT / f'{task}-{split}.jsonl').open('w') as dst:
                for line in src:
                    x = json.loads(line)
                    # Uniform field on every task: a bare option label resolved to its option text
                    # during pool building (RECONSTRUCT and SOLVE); null when the answer is DeepMath's.
                    if 'answer_normalization' not in x:
                        raw = str(raw_answers[x['dataset_row_index']]).strip()
                        x['answer_normalization'] = None if str(x['final_answer']).strip() == raw else dict(
                            method='unique explicit option-label lookup, no mathematical repair',
                            original_answer=raw, normalized_answer=x['final_answer'])
                    x['training'] = training_block(x)
                    dst.write(json.dumps(x, ensure_ascii=False) + '\n')
    summary = json.loads((SRC / 'summary.json').read_text())
    summary.update(version='FINAL-v3', derived_from='FINAL-v2 (rows unchanged; adds the training block)',
                   training_block={'solve': 'question -> r1_solution_1 + final_answer',
                                   'judge': 'public (problem + proposed solution + instruction) -> teacher_target_response (no CoT)',
                                   'reconstruct': 'public_input (answer + 4 clues) -> r1_solution_1 + original question'},
                   v3_runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
