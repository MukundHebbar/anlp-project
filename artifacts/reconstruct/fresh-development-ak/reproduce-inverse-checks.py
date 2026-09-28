"""Independent exact checks of returned AK certificates; not student outputs."""
from fractions import Fraction
from math import factorial,isqrt
import json
from pathlib import Path
root=Path(__file__).resolve().parent
# Long-cycle events are disjoint above half the100 symbols.
counts={t:sum((Fraction(factorial(100),k) for k in range(t,101)),Fraction()) for t in range(51,101)}
answer=factorial(100)*sum((Fraction(1,k) for k in range(51,101)),Fraction())
assert [t for t,v in counts.items() if v==answer]==[51]
assert all(counts[t]>counts[t+1] for t in range(51,100))
# N=2^4*5^k => N^2/4=2^6*5^(2k), so signed ordered factor count14(2k+1).
k=(Fraction(98,14)-1)/2
assert k==3
N=2**4*5**int(k);M=N*N//4;divisors=set()
for a in range(1,isqrt(M)+1):
    if M%a==0:divisors.update((a,M//a))
points={(sign*(a+M//a),sign*(M//a-a)) for a in divisors for sign in (-1,1)}
assert N==2000 and len(points)==98 and all(x*x-y*y==N*N for x,y in points)
residues=[n for n in range(61) if factorial(n)%61==27]
assert residues==[51]
result={'source5':{'derived_count':'100!*(H100-H(t-1)) for51<=t<=100; zero ift>100','strictly_decreasing_for_51_to_100':True,'unique_matching_threshold':51,'exact_answer':str(answer)},'source16':{'derived_count':'14*(2k+1)','inferred_k':str(k),'inferred_N':N,'verified_integer_points':len(points),'points':sorted(points)},'source10_auxiliary':{'factorial_indices_with_residue27_mod61':residues,'note':'Independent arithmetic check; do not assume this is the converter-selected missing premise.'}}
(root/'inverse-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print('Verified threshold51, exponent3 and all98 integer points; auxiliary factorial inverse unique at51.')
