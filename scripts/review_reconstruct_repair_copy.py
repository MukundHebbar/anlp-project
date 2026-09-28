#!/usr/bin/env python3
"""Keep copying candidates separate from actual original-question disclosure."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash


def main():
    root=Path('artifacts/reconstruct/d3-v2')
    run=json.loads((root/'repair-study.json').read_text())
    manifest=json.loads((root/'repair-copy-manifest.json').read_text())
    rows=[]
    for entry in manifest['rows']:
        index=entry['source_index']
        record=next(c for c in run['copy_challenges'].values() if c['bank_key']==entry['bank_key'])
        bank=run['banks'][entry['bank_key']]['output']
        assert stable_hash(bank)==entry['bank_output_hash']
        output=record['output']
        if index==33:
            reason='The copied question assumes strict pointwise dominance and asks about maxima. The original assumes equal maxima and asks for a meeting point. Premises and target differ; copying this lemma is not recovery of the original.'
        elif index==86:
            reason='The copied question asks for the named scale point a, not the limit of the original specified integral. This is a trivial same-answer question, not original recovery, and should not earn substantive reconstruction credit.'
        elif index==123:
            reason='The raw candidate adds eventual constancy and evenness. Selecting only its natural-sequence, every-partial-sum and perfect-power-exclusion spans yields the original existence question without mathematical inference. The withheld witness and mod4 argument are solution content, not withheld essential question premises. Reject direct question disclosure despite all three teacher accepts.'
        else:
            assert output['status']=='no_direct_reconstruction'
            reason='The attack supplies no original candidate. Manual source comparison agrees that the exact target/premise material identified as missing is not supplied by copying alone; mathematical and full-solution review is recorded separately. A negative attack is not a guarantee of non-leakage.'
        row={**entry,'copy_output_hash':stable_hash(output),'copy_status':output['status'],
             'known_direct_source_disclosure':index==123,'review':reason,
             'development_eligible_after_review':index!=123}
        if index==123:
            row['assistant_copy_candidate']='Does there exist an infinite sequence of natural numbers such that every partial sum is not a perfect power?'
            row['public_alignment']=[
              {'candidate_span':'an infinite sequence of natural numbers','public_quote':'an infinite sequence of natural numbers','operation':'copy'},
              {'candidate_span':'every partial sum','public_quote':'every partial sum','operation':'copy'},
              {'candidate_span':'is not a perfect power','public_quote':'The solution rules out perfect powers','operation':'paraphrase'},
              {'candidate_span':'Does there exist','public_quote':'The proposed example','operation':'grammatical_assembly'}]
            public='\n'.join(c['sentence'] for c in bank['clues'])
            assert all(a['public_quote'] in public for a in row['public_alignment'])
        rows.append(row)
    result={'provenance':'Assistant semantic/transformation review; not independent human gold',
       'raw_three_auditor_accepted':10,'reviewed_development_eligible':9,'original_sources':12,
       'release_coverage_passed':False,'scope':'Development input eligibility only; final teacher reliability and confirmation remain unproven',
       'rows':rows}
    (root/'repair-copy-review.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Reviewed ten attacks: exclude123; nine development inputs remain')


if __name__=='__main__':main()
