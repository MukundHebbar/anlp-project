#!/usr/bin/env python3
"""Record content observations before audit outcomes; no eligibility overrides."""
import json
from collections import Counter
from pathlib import Path
from anlp_project.reconstruct import stable_hash


def main():
    root=Path('artifacts/reconstruct/d3-v2')
    target=root/'p4-initial-content-review.json'
    if target.exists():
        raise SystemExit('Refusing to overwrite the pre-audit content review')
    run=json.loads((root/'run.json').read_text())
    observations={
        8: 'Names the denominator role explicitly, but adds the final numerator-equals-denominator cancellation. Check whether the combined bank exposes nearly all proof despite hiding original squared numerators and zero-sum premise. No acceptance inferred from omission alone.',
        27: 'Removes the range 1..100 retained in p3 and still omits the count/minimality target. Adds the positive-coefficient consequence of a direct squarefree term. This is not uniformly more informative than p3 and does not implement the preferred target-role retention.',
        33: 'Replaces the generic constant-sign lemma with a strict pointwise-dominance versus maxima relationship. The equal-maxima premise and meeting target remain absent. More distinctive source structure is visible; its copying/proof disclosure still requires review.',
        86: 'Gives the split interval, left pointwise limit, and right-tail bound. Exact integrand and limit target are withheld. These may still expose nearly the complete convergence argument; shortness or a hidden formula is not sufficient acceptance evidence.',
        122: 'Retains algebraic substitution, parity and large-prime consequences while withholding both divisibility conditions. Neither recovery of the original nor a target-role improvement is established by these true observations.',
        136: 'Gives pairwise intersection size, a degree sum, and the degree bound44 under no-common-element. The private withheld explanation says size45 is omitted, although44 indirectly constrains size in the intended argument. Review semantic disclosure rather than literal occurrence of45.',
        141: 'Explicitly retains a coefficient/count target role and four factor exponent ranges; omits the requested exponent. Distinguish inference of the target from simply copying a coefficient expression. The claim that answer204 uniquely identifies shifted exponent9 needs qualification because coefficient symmetry also gives19.',
        143: 'Retains nested binomial roles, X in{21,7}, and exclusion ofY=1. The latter indirectly reveals restrictions on equality and zero values. The outer equation and total-count request remain implicit; inspect joint disclosure.'
    }
    rows=[]
    for key,bank in run['banks'].items():
        if bank['prompt']!='convert_p4' or bank['source_index'] not in observations:
            continue
        rows.append({'source_index':bank['source_index'],'bank_key':key,
                     'bank_output_hash':stable_hash(bank['output']),
                     'observation':observations[bank['source_index']]})
    assert len(rows)==8
    coefficients=Counter({0:1})
    for _ in range(4):
        expanded=Counter()
        for exponent,coefficient in coefficients.items():
            for addend in range(8): expanded[exponent+addend]+=coefficient
        coefficients=expanded
    assert coefficients[9]==coefficients[19]==204
    target.write_text(json.dumps({'provenance':'Assistant qualitative review; neither independent human gold nor an acceptance decision',
        'scope':'Eight first-pass p4 banks, reviewed before p4 audit outcomes; the three technical-retry sources are not included',
        'eligibility_effect':'none; run all preregistered audits and copying checks',
        'source141_exact_check':{'polynomial':'(1+x+...+x^7)^4','coefficient_9':coefficients[9],
          'coefficient_19':coefficients[19],
          'interpretation':'The answer alone does not uniquely identify the exponent. Complementing four exponents gives a bijection, so this does not by itself prove failure of semantic equivalence under the permitted correspondence rule.'},
        'rows':rows},indent=2)+'\n')
    print('Saved eight input-bound content observations without changing eligibility')


if __name__=='__main__':main()
