"""Both frozen 8-step SOLVE LR probes followed by dev-only LR selection."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import signal
import time

ROOT=Path(__file__).resolve().parents[2]
MODEL='/scratch/mukund.hebbar/llama-transfer/models/llama'


def run_training(command, report_path, shutdown_timeout=30, poll_interval=5, steps=8, limit=90*60):
    """Bound interpreter teardown after a verified result; reclaim this child's whole server group."""
    proc=subprocess.Popen(command,start_new_session=True)
    deadline=time.monotonic()+limit
    try:
        while True:
            if report_path.exists():
                try:report=json.loads(report_path.read_text())
                except json.JSONDecodeError:report=None
                if report is not None:
                    if not report.get('ok') or steps is not None and report.get('steps_done')!=steps:
                        raise RuntimeError(f'Training did not complete {steps} steps: {report_path}')
                    try:proc.wait(timeout=shutdown_timeout)
                    except subprocess.TimeoutExpired:
                        print('Completed training result saved; terminating stuck interpreter/server group.',flush=True)
                    break
            if proc.poll() is not None:
                raise RuntimeError(f'Training exited without a completed result: {proc.returncode}')
            if time.monotonic()>deadline:raise TimeoutError(f'Training exceeded its {limit/60:.0f}-minute limit')
            time.sleep(poll_interval)
    finally:
        try:os.killpg(proc.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        try:proc.wait(timeout=shutdown_timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        # The parent can exit before its engine descendants; do not leave them on the rollout GPU.
        try:os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError:pass


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    results=[]
    for suffix, lr in [('low',1e-5),('high',2e-5)]:
        train=out/f'solve-probe-{suffix}'
        report_path=train/'result-0.json'
        if not report_path.exists():
            run_training([sys.executable,str(ROOT/'phase2/llama_transfer/run.py'),
                '--arm',f'solve-probe-{suffix}','--model-path',MODEL,'--out',str(train)],report_path)
        report=json.loads((train/'result-0.json').read_text())
        if not report['ok'] or report['steps_done']!=8 or any('AUTO-STOP:' in line for line in report['events']):
            raise RuntimeError(f'{suffix} LR probe ended before its scheduled eight updates')
        if not (train/'adapters/step8/adapter_model.safetensors').exists():
            raise RuntimeError('Completed probe has no step-8 adapter')
        dev=out/f'dev-{suffix}'
        if not (dev/'done').exists():
          subprocess.run([sys.executable,str(ROOT/'scripts/turing/eval_matrix.py'),
             '--name',f'llama-probe-{suffix}-dev','--out',str(dev),'--model',
             'meta-llama/Llama-3.2-3B-Instruct','--model-path',MODEL,'--chat-mode','instruct',
             '--adapter',str(train/'adapters/step8'),'--tasks','solve','--split','dev',
             '--samples','4','--samples-tasks','solve','--first-cap','16384','--max-cap','32768'],check=True)
        scored=[[json.loads(line) for line in (dev/f's{i}/scores.jsonl').open()] for i in range(4)]
        if any(len(rows)!=200 or len({r['uid'] for r in rows})!=200 for rows in scored):
            raise RuntimeError('Probe evaluation must contain exactly 200 unique dev items per sample')
        accuracy=[sum(bool(r['correct_strict']) for r in rows)/len(rows) for rows in scored]
        results.append({'arm':f'solve-probe-{suffix}','lr':lr,'mean_dev_accuracy':sum(accuracy)/4,
                        'sample_accuracy':accuracy,'adapter':str(train/'adapters/step8')})
    winner=max(results,key=lambda r:(r['mean_dev_accuracy'],-r['lr']))
    (out/'lr-selection.json').write_text(json.dumps({'rule':'mean strict accuracy on 200 dev x4; lower LR on tie',
             'candidates':results,'selected':winner,'test_used_for_selection':False},indent=2))
    (out/'done').write_text('ok\n')
    print('LLAMA_LR_PROBES_COMPLETE',json.dumps(winner),flush=True)


if __name__=='__main__':main()
