#!/usr/bin/env python3
"""Save authored semantic controls before teacher scoring; no provider calls."""
import json
from pathlib import Path


def fixtures():
    families = [
        ('polynomial', 'Find all real roots of x²-5x+6=0.',
         'Find all real t satisfying (t-2)(t-3)=0.', 'Factorization preserves exactly the real roots.',
         'Find the larger real root of x²-5x+6=0.', 'Only one root is requested instead of all roots.',
         'List the prime integers between1 and4.', 'Coincident answer set{2,3}; primality and polynomial roots are different constraints.'),
        ('dice', 'Roll two independent fair six-sided dice. Find the probability their sum is7.',
         'Choose an ordered pair uniformly from{1,2,3,4,5,6}². What fraction have coordinates summing7?', '36 equally likely ordered outcomes correspond bijectively to dice results.',
         'Roll two fair six-sided dice without assuming independence. Find the probability their sum is7.', 'Marginal fairness does not fix joint probabilities.',
         'What is the reciprocal of6?', 'Same answer1/6 but no dice event.'),
        ('derivative', 'For f(x)=x³ on the reals, find f\u2032(2).',
         'Find the tangent slope of y=t³ at t=2.', 'Derivative is the tangent slope at the same point.',
         'For f(x)=x³ on the reals, find f\u2032(-2).', 'Evaluation point changes although both slopes equal12.',
         'Find the area of a rectangle with sides3 and4.', 'Answer12 does not preserve the derivative task.'),
        ('modular', 'Find the least positive integer n with n≡2(mod3) and n≡3(mod5).',
         'Find the smallest positive n such that3 divides n-2 and5 divides n-3.', 'Divisibility and congruence assertions are equivalent.',
         'Find any positive integer n with n≡2(mod3) and n≡3(mod5).', 'Any solution is weaker than the least solution.',
         'How many subsets does a set of three elements have?', 'Answer8 is shared but the defining problem differs.'),
        ('integral', 'Evaluate the definite integral of2x from0 to1.',
         'Compute the signed area under y=2t between t=0 and t=1.', 'Same integrand, bounds, and integral target.',
         'Evaluate the definite integral of2x from-1 to0.', 'Bounds differ and change the result.',
         'How many positive divisors does1 have?', 'Same numerical answer1 but unrelated mathematical object.'),
        ('graph', 'How many spanning trees does the complete graph on four labelled vertices have?',
         'On fixed vertex set{a,b,c,d}, count connected acyclic simple graphs.', 'Every tree on these vertices is a spanning subgraph of K4, and conversely.',
         'How many unlabelled trees are there on four vertices?', 'Counting up to isomorphism changes the objects counted.',
         'Compute2 to the fourth power.', 'Answer16 alone omits the graph counting task.'),
        ('sequence', 'Let a1=2 and a(n+1)=3a(n). Find a5.',
         'A geometric sequence starts at2 with ratio3. Find its fifth term.', 'Equivalent initial value, recurrence, and index.',
         'Let a1=2 and a(n+1)=3a(n). Find a4.', 'Target index is different.',
         'Compute the area of a rectangle with sides9 and18.', 'Answer162 does not establish sequence equivalence.'),
        ('quantifiers', 'Is it true that every real x satisfies x²≥x?',
         'Does x(x-1)≥0 hold for all real numbers x?', 'Subtracting x preserves inequality and universal real quantifier.',
         'Is there a real x satisfying x²≥x?', 'Existential replaces universal quantification.',
         'Is9 a prime number?', 'Both original and candidate answer No, but propositions differ.'),
    ]
    result = []
    for family, source, same, same_reason, related, related_reason, different, different_reason in families:
        for label, candidate, reason in [(2,same,same_reason),(1,related,related_reason),(0,different,different_reason)]:
            result.append({'id':f'{family}-{label}', 'family':family, 'source_question':source,
                           'candidate_question':candidate, 'expected':label, 'reference_reason':reason})
    return result


if __name__ == '__main__':
    path=Path('data/manifests/reconstruct-semantic-development-v1.json')
    data={'status':'authored development controls, not independent final validation',
          'reference_provenance':'assistant-authored explicit mathematical correspondences and mismatches',
          'families':8, 'fixtures':fixtures()}
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    print(f'Saved{len(data["fixtures"])} controls across8 families to{path}')
