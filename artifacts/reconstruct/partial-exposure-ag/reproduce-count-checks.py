"""Independent exact checks for AF/AG word-count claims; standard library only."""
from itertools import product

counts = [1] * 7
for length in range(1, 13):
    if length in (6, 10, 12):
        print({'length': length, 'total': sum(counts), 'remainder_mod_2008': sum(counts) % 2008})
    if length == 6:
        six = counts[:]
    if length == 10:
        assert sum(counts) == 1584
    if length == 12:
        assert sum(counts) == 5408 and sum(counts) % 2008 == 1392
    counts = [(counts[d-1] if d else 0) + (counts[d+1] if d < 6 else 0) for d in range(7)]

words = [w for w in product(range(7), repeat=6) if all(abs(a-b) == 1 for a,b in zip(w,w[1:]))]
assert len(words) == sum(six) == 136
assert sum(w[0] != 0 for w in words) == sum(six) - six[0] == 126
print('Six-digit word and number counts also match exhaustive enumeration.')
