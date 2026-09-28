#!/usr/bin/env python3
"""Execute the predeclared sixteen local outputs for amendment O."""
import subprocess
import sys


def main():
    # ABBA prompt order across seeds; no best-of-two selection or adaptation.
    for prompt,seed in [('student_p1',0),('student_p10_recover_original',0),
                        ('student_p10_recover_original',1),('student_p1',1)]:
        cmd=[sys.executable,'scripts/run_reconstruct.py','student',
             '--output','artifacts/reconstruct/d3-v2/prompt-diagnostic.json',
             '--report','artifacts/reconstruct/d3-v2/prompt-diagnostic-run.md',
             '--student-prompt',prompt,'--bank-prompt','convert_p3','--indices','8','27','33','77',
             '--all-clues','--selection-policy','bank_order','--style','sentence',
             '--max-tokens','8192','--temperature','.7','--top-p','.8','--top-k','20',
             '--seed',str(seed),'--timeout','300']
        print(f'Local diagnostic: {prompt}, seed{seed}',flush=True)
        subprocess.run(cmd,check=True)
    print('All sixteen planned local attempts terminal; retain failures.',flush=True)


if __name__=='__main__':main()
