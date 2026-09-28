#!/usr/bin/env python3
"""Exact arithmetic counterexamples/checks; not a substitute for all analytic proofs."""
import itertools,json,math
from fractions import Fraction as F
from pathlib import Path
matrices=[]
for a,b,c,d in itertools.product([-1,0,1],repeat=4):
 if (a*a+b*c,a*b+b*d,c*a+d*c,c*b+d*d)==(-1,0,0,-1):
  matrices.append({'matrix':[[a,b],[c,d]],'determinant':a*d-b*c})
x=F(1,3);series=x*(1+x)/(1-x)**3
u_real=F(-99,100);u_imag_sq=F(99,10000)
count_divisors=sum(1 for d in range(1,1000001) if 1000000%d==0)
checks={
 'factorial_remainder':{'factorial_n':51,'modulus':61,'actual':math.factorial(51)%61,'student':58},
 'hyperbola':{'N':2000,'N_squared_over4':1000000,'positive_divisors':count_divisors,'signed_ordered_pairs':2*count_divisors,'student':32},
 'series_formula_at_one_third':{'actual':str(series),'student':'9/2'},
 'geometry_attained_counterexample_to_one_hundredth':{'circle_radius_squared':str((u_real+1)**2+u_imag_sq),'attained_tan_squared':str(u_imag_sq/u_real**2),'greater_than_student':u_imag_sq/u_real**2>F(1,100),'global_upper_bound_proof':'See fresh-development-ak/analytic-inverse-certificates.json'},
 'matrix_square_negative_identity':{'enumerated':81,'valid':matrices,'probability_det_minus_one':sum(v['determinant']==-1 for v in matrices)/len(matrices)},
 'false_factorial_identity_at_k2':{'student_left':1*math.factorial(1),'student_right':math.factorial(2)},
 'polynomial_option_A_counterexample':{'objects':1,'colors':1,'polynomial':'x+1','a0':1,'k_greater_a0':False},
 'inverse_matrix_counterexample_to_only_n1':{'A':[[1,0],[1,1]],'inverse':[[1,0],[-1,1]],'determinant':1,'inverse_entry_sum':1},
 'scope':'These exact finite calculations substantiate specific observed errors; general analytical claims are in analytic-review.json and linked source certificates.'}
assert checks['factorial_remainder']['actual']==27 and count_divisors==49 and series==F(3,2)
assert len(matrices)==2 and all(v['determinant']==1 for v in matrices)
assert (u_real+1)**2+u_imag_sq==F(1,100) and u_imag_sq/u_real**2==F(1,99)
Path(__file__).with_name('exact-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print('Exact arithmetic and enumeration checks passed')
