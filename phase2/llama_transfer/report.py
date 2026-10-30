"""Dr. GRPO transfer matrix for Llama-3.2-3B-Instruct, in the Qwen report's format (scripts/report_grpo_matrix.py:
same metrics, per-question pass@1, paired deltas against the untrained model, 2,000-resample bootstrap).

    python phase2/llama_transfer/report.py     # writes artifacts/baselines/llama3b/grpo-matrix.md

Eval folders under artifacts/baselines/llama3b/test/: llama3b-base (untrained) and llama3b-grpo-<task>-step<k>;
artifacts/baselines/llama3b/selection.json gives each arm's dev-selected step.
"""
import json
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from report_grpo_matrix import METRICS, OWN, boot, fmt, per_question  # noqa: E402

BASE = ROOT / 'artifacts/baselines/llama3b'
NOTE = ('Student meta-llama/Llama-3.2-3B-Instruct, seed 0, the Qwen study\'s per-task Dr. GRPO recipes. Training '
        'rewards for JUDGE / RECONSTRUCT come from Gemma 4 12B (explicit-label calibration) instead of Jev; '
        'JUDGE V/L/E/M and RECONSTRUCT PC-v4 use the Qwen3.8-27B judge as in the Qwen study. SOLVE lr 2e-5 '
        '(chosen by the 8-step probes on dev; the Qwen study used 1e-5).')


def main():
    sel = json.loads((BASE / 'selection.json').read_text())
    base = per_question(BASE / 'test/llama3b-base')
    rows = [('Untrained Llama-3.2-3B', base, None)]
    for task in ('solve', 'judge', 'reconstruct'):
        for d in sorted((BASE / 'test').glob(f'llama3b-grpo-{task}-step*'), key=lambda p: int(p.name.rsplit('step', 1)[1])):
            k = int(d.name.rsplit('step', 1)[1])
            kind = 'dev-selected' if k == sel.get(task) else 'fixed endpoint'
            rows.append((f'Dr. GRPO on {task.upper()}, step {k} ({kind})', per_question(d), task))
    L = ['# Dr. GRPO transfer matrix (Llama-3.2-3B-Instruct, FINAL-v3 test)', '', NOTE, '',
         '## Scores (pass@1 unless noted)', '',
         '| Model | ' + ' | '.join(n for _, n, _ in METRICS) + ' |', '|---|' + '---:|' * len(METRICS)]
    for name, v, _ in rows:
        L.append(f'| {name} | ' + ' | '.join(fmt(boot(list(v[m].values())), pct) if v[m] else '—'
                                             for m, _, pct in METRICS) + ' |')
    L += ['', '## Δ against the untrained Llama (paired; **bold** = own task)', '',
          '| Model | ' + ' | '.join(n for _, n, _ in METRICS) + ' |', '|---|' + '---:|' * len(METRICS)]
    for name, v, task in rows[1:]:
        cells = []
        for m, _, pct in METRICS:
            both = sorted(set(v[m]) & set(base[m]))
            c = fmt(boot([v[m][u] - base[m][u] for u in both]), pct, sign=True) if both else '—'
            cells.append(f'**{c}**' if m in OWN[task] else c)
        L.append(f'| {name} | ' + ' | '.join(cells) + ' |')
    L += ['', '## JUDGE by answer-key label (pass@1)', '',
          '| Model | verdict, key correct % | verdict, key incorrect % | combined, key correct % | '
          'combined, key incorrect % |', '|---|---:|---:|---:|---:|']
    for name, v, _ in rows:
        cells = []
        for m in ('judge_verdict', 'judge_combined'):
            for lab in ('correct', 'incorrect'):
                xs = [v[m][u] for u in v[m] if v['_label'].get(u) == lab]
                cells.append(f'{100 * st.mean(xs):.1f}' if xs else '—')
        L.append(f'| {name} | ' + ' | '.join(cells) + ' |')
    (BASE / 'grpo-matrix.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
