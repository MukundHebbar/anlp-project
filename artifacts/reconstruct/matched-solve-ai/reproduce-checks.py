"""Exact arithmetic checks supporting selected SOLVE review findings."""
from fractions import Fraction as F
from math import gcd, prod, factorial
units = [a for a in range(1,24) if gcd(a,24)==1]
assert prod(units) % 24 == 1
assert factorial(8)//(factorial(3)*factorial(3)*factorial(2)) == 560
moment1, moment2 = F(2), F(8,3)
pair_product = (moment1**2-moment2)/2
assert 3*(moment2-2*pair_product) == 4
assert (5**2-1)//8 == 3 and 2*3//2 == 3
assert 111111 % 7 == 0 and 111111 % 3 == 0
assert 4*6 == 6*6-12
print('Verified: units product mod24=1; target orders=560; quadrature expression=4; witness5; repunit has smaller divisor3; graph n6.')
print('These checks do not automate all proof or source-equivalence judgments.')
