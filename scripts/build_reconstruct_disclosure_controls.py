#!/usr/bin/env python3
"""Freeze public disclosure controls and isolated standard-runner artifacts."""
import copy
import json
from pathlib import Path


def main():
    examples=[
      ('dice','1/6','Roll two independent fair six-sided dice. What is the probability their sum is7?',
       'Conditioning on the first die partitions the sample space into six equally probable cases.',
       'Two independent fair six-sided dice are rolled; the event is that their sum is7.',
       'There are36 equally likely ordered outcomes.'),
      ('derivative','12','Find the derivative of f(x)=x³ at x=2.',
       'Differentiation uses the power rule.',
       'The function is f(x)=x³ and the required quantity is its derivative at x=2.',
       'The derivative function is3x².'),
      ('modular','8','Find the least positive integer n with n≡2(mod3) and n≡3(mod5).',
       'One divisibility condition can be written n=3k+2 for integer k.',
       'The integer n is positive, n≡2(mod3), n≡3(mod5), and the smallest such n is required.',
       'Every common solution is congruent to8 modulo15.'),
      ('integral','1','Evaluate the definite integral of2x from0 to1.',
       'An antiderivative differs from another by an arbitrary constant on the interval.',
       'The integrand is2x, the integration limits are0 and1, and the target is the definite integral.',
       'The integral equals[x²] evaluated at1 minus its value at0.'),
      ('graph','16','How many spanning trees does K4 on four labelled vertices have?',
       'Removing a leaf and its incident edge from a tree reduces its vertex count by one.',
       'Count the spanning trees of the complete graph on four labelled vertices.',
       'Cayley’s formula gives4 to the power4-2.'),
      ('sequence','162','Let a1=2 and a(n+1)=3a(n). Find a5.',
       'Each successive term is three times its predecessor.',
       'The sequence starts at2, each successive term is three times its predecessor, and its fifth term is required.',
       'The fifth term is2 times3 to the fourth power.'),
    ]
    cases=[]
    for family,answer,question,sparse,full,extra in examples:
        for label,clues,expected in [('sparse',[sparse],'ACCEPT'),('full',[full],'REJECT'),('superset',[full,extra],'REJECT')]:
            cases.append({'id':family+'-'+label,'family':family,'question':question,'answer':answer,
                          'clues':clues,'expected':expected,
                          'reference_reason':('Essential source premises/target remain absent' if expected=='ACCEPT'
                                              else 'Complete source premise-target bundle appears explicitly'),
                          'reference_provenance':'assistant-authored development control'})
    original=json.loads(Path('artifacts/reconstruct/d3-v1/prefix-study.json').read_text())
    for index,k in [(123,1),(141,1),(8,3),(33,3),(112,3),(86,3)]:
        b=next(b for b in original['banks'].values() if b['source_index']==index and b['prompt']==f'nested_k{k}')
        s=original['sources'][str(index)]
        cases.append({'id':f'production-{index}-k{k}','family':f'production-{index}',
                      'question':s['question'],'answer':s['final_answer'],
                      'clues':[c['sentence'] for c in b['output']['clues']],
                      'expected':None,'reference_reason':'Boundary diagnostic: no frozen binary gold label',
                      'reference_provenance':'existing D3 exact public prefix, not independent validation'})
    path=Path('data/manifests/reconstruct-disclosure-development-v1.json')
    path.write_text(json.dumps({'status':'development; 18 clear controls plus6 unlabeled production boundaries',
                                'fixtures':cases},indent=2,ensure_ascii=False)+'\n')
    run={'metadata':{'study':'amendment L2','reference_manifest':str(path)},
         'sources':{},'banks':{},'audits':{},'responses':{},'evaluations':{},'failures':[]}
    for i,c in enumerate(cases):
        run['sources'][str(i)]={'question':c['question'],'final_answer':c['answer'],'checked_solution':'Not used by this public-only calibration'}
        run['banks'][f'fixture-{i}']={'source_index':i,'prompt':'disclosure_controls','model':'authored_fixture','output':{'status':'OK',
           'clues':[{'id':f'c{j+1}','sentence':s,'fragment':s,'hidden_support':'Not used by public-only calibration'}
                    for j,s in enumerate(c['clues'])]}}
    root=Path('artifacts/reconstruct/disclosure-v1')
    root.mkdir(parents=True,exist_ok=True)
    for arm in ['incumbent','candidate']:
        output=root/f'{arm}.json'
        if output.exists(): raise ValueError(f'Refusing overwrite: {output}')
        output.write_text(json.dumps(copy.deepcopy(run),indent=2,ensure_ascii=False)+'\n')
    print('Saved24 cases and isolated public-audit artifacts; no calls made')


if __name__=='__main__':main()
