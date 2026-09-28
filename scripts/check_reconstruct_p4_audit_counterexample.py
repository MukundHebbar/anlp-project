#!/usr/bin/env python3
"""Check a public-auditor premise-bundle claim against an exact counterexample."""
import json
import math
from pathlib import Path
from anlp_project.reconstruct import stable_hash


def main():
    root=Path('artifacts/reconstruct/d3-v2')
    run=json.loads((root/'run.json').read_text())
    key,bank=next((k,b) for k,b in run['banks'].items()
                  if b['prompt']=='convert_p4' and b['source_index']==122)
    audit=next(a for a in run['audits'].values()
               if a.get('bank_key')==key and a['prompt']=='audit_public_p4')
    witnesses=[]
    for m,n in [(2,2),(2,4)]:
        s=m+n; q=m*m-m*n+n*n; d=q+1
        primes=[p for p in range(2,d+1) if d%p==0 and all(p%j for j in range(2,math.isqrt(p)+1))]
        checks={'cube_identity':m**3+n**3==s*q, 'd_odd':d%2==1,
                'both_even':m%2==n%2==0, 'all_prime_divisors_exceed_s':all(p>s for p in primes)}
        remainders=[(pow(3,s,d)+math.factorial(s))%d,(pow(3,m**3+n**3,d)+s)%d]
        assert all(checks.values())
        witnesses.append({'m':m,'n':n,'s':s,'q':q,'d':d,'prime_divisors':primes,
                          'displayed_observations':checks,'original_divisibility_remainders':remainders})
    assert witnesses[0]['original_divisibility_remainders']==[0,0]
    assert witnesses[1]['original_divisibility_remainders']==[6,7]
    output={'provenance':'Exact integer arithmetic; assistant interpretation, not human adjudication',
       'source_index':122,'bank_key':key,'bank_output_hash':stable_hash(bank['output']),
       'audit_output_hash':stable_hash(audit['output']), 'raw_audit_status':audit['output']['status'],
       'witnesses':witnesses,
       'finding':'The displayed observations do not expose equivalent defining conditions for the original problem: (2,4) satisfies them but violates both original divisibility conditions. They also do not uniquely yield (2,2). The supplied answer is intentional and cannot supply missing premises.',
       'scope':'Refutes the recorded premise-bundle/routine-verification rationale. It does not by itself certify all aspects of non-leakage, prove recoverability, or change the preregistered raw audit gate.',
       'next_action':'Review this disagreement using source-aware disclosure and independently calibrated controls; do not silently relabel the bank.'}
    (root/'p4-audit-counterexample.json').write_text(json.dumps(output,indent=2)+'\n')
    print('Verified (2,4) satisfies all displayed conditions but fails the original by remainders6,7')


if __name__=='__main__':main()
