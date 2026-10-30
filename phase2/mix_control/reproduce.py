"""Reproduce the original mixture-control decision offline from committed compressed scores."""
import contextlib
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import decide
import decide_lr


def main():
    result=ROOT/'phase2/results/mix-control'
    with gzip.open(result/'validation-scores.jsonl.gz','rt') as stream:
        records=[json.loads(line) for line in stream]
    assert len(records)==11200
    groups={}
    for record in records:
        key=(record['split'],record['run'],record['sample'])
        groups.setdefault(key,[]).append(record['score'])
    assert len(groups)==56
    with tempfile.TemporaryDirectory(prefix='anlp-mixture-reproduction-') as directory:
        decide.E=Path(directory)
        for (split,run,sample),rows in groups.items():
            assert len(rows)==200 and len({r['uid'] for r in rows})==200
            path=decide.E/decide.SPLITS[split].format(run=run)/f's{sample}'
            path.mkdir(parents=True,exist_ok=True)
            (path/'scores.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
        arms={run:decide.per_question(run) for run in ['mixed75']+[r for pair in decide_lr.LRS.values() for r in pair]}
        questions=sorted(set.intersection(*(set(arm) for arm in arms.values())))
        assert len(questions)==348 and sum(q.startswith('dev:') for q in questions)==199
        with gzip.open(result/'paired-question-outcomes.jsonl.gz','rt') as stream:
            paired={r['question']:r['correct_by_sample'] for r in map(json.loads,stream)}
        assert set(paired)==set(questions)
        assert all(arms[run][q]==paired[q][run] for run in arms for q in questions)
        summary=json.loads((result/'summary.json').read_text())
        for run in arms:
            mean=100*sum(sum(arms[run][q])/4 for q in questions)/len(questions)
            assert abs(mean-summary['models'][run]['pooled']['avg_at_4_percent'])<1e-10
        output=io.StringIO()
        with contextlib.redirect_stdout(output):decide_lr.main()
    text=output.getvalue()
    assert text==(result/'lower-lr-decision.txt').read_text(),'Decision output differs from the saved result'
    print(text,end='')
    print('Verified: raw scores, exclusions, paired outcomes, published means and decision output match.')


if __name__=='__main__':main()
