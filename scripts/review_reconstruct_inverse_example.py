#!/usr/bin/env python3
"""Save reproducible counterexamples for amendment P; not independent human gold."""
import hashlib
import json
from pathlib import Path
import sympy as s


def main():
    root = Path('artifacts/reconstruct/d3-v2')
    run = json.loads((root / 'prompt-diagnostic.json').read_text())
    x = s.symbols('x', real=True)
    a, b, c = map(s.Integer, [1, 2, -3])
    quantities = [2*a*a+b*c, 2*b*b+c*a, 2*c*c+a*b]
    denominator = (a-b)*(a-c)*(b-c)
    assert a+b+c == 0 and denominator != 0
    assert quantities == [(a-b)*(a-c), (b-c)*(b-a), (c-a)*(c-b)]
    product = s.prod(quantities)
    asserted_product = (a-b)*(a-c)*(b-c)**2
    altered_sum = sum(quantities) / denominator
    assert product != asserted_product and altered_sum != 1
    notes = {
        8: f'Witness a=1,b=2,c=-3 meets distinctness and all three factorizations. Seed0 asserted identity has LHS {product} versus RHS {asserted_product}. Seed1 altered sum is {altered_sum}, not 1. Both change the original sum of a^2/(2a^2+bc).',
        27: 'Both candidates ask for a radical sum rather than its minimal number of radical terms. Every sqrt(n)>=1 for n=1..100, and some are >1, so the sum is >100, not 60. This elementary bound disproves the proposed answer without a numerical approximation.',
        33: 'Both candidates ask whether a difference can change sign while f is nonzero. The existential answer Yes has witness f=1 and g=2x on [0,1]; f-g=1-2x changes sign. This does not recover the original equal-maxima universal meeting theorem, and the nonzero-continuous-function clue is not substantively used to obtain this witness.',
        77: 'Seed0 changes the fixed cubic x^3-x to x^3-3x and asks for area in terms of two translations rather than its maximum. Its |a|<2,|b|<2 restrictions even allow a=b, where the curves coincide. The unparseable seed1 raw output also changes the cubic and target; retain it as a format failure, not a rescued success.'
    }
    assert (1-2*x).subs(x, 0) == 1 and (1-2*x).subs(x, 1) == -1
    rows = []
    for key, response in run['responses'].items():
        if response['prompt'] != 'student_p11_inverse_example':
            continue
        rows.append({'response_key': key, 'source_index': response['source_index'],
                     'seed': response['sampling']['seed'],
                     'evidence_hash': response['evidence_hash'],
                     'output_sha256_sorted_json': hashlib.sha256(json.dumps(response['output'], sort_keys=True).encode()).hexdigest(),
                     'review': notes[response['source_index']],
                     'same_original_supported': False})
    result = {'provenance': 'Assistant mathematical review with exact SymPy counterexamples; not independent human validation',
              'scope': 'All parseable amendment P responses; mathematical counterexamples reject claimed results but do not assign rubric scores',
              'cases': rows, 'notes_by_source': notes}
    (root / 'inverse-example-math-review.json').write_text(json.dumps(result, indent=2)+'\n')
    print(f'Saved {len(rows)} response-bound reviews and exact counterexamples')


if __name__ == '__main__':
    main()
