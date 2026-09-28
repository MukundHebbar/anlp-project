#!/usr/bin/env python3
"""Freeze amendment U controls and prompt hashes before any paid judgments."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project.reconstruct import stable_hash


def main():
    root = Path('artifacts/reconstruct/inference-u')
    root.mkdir(parents=True, exist_ok=True)
    dest = root / 'fixtures.json'
    if dest.exists():
        raise SystemExit('Frozen fixtures already exist; refusing overwrite')
    families = [
        ('linear', 'Every real equation ax+b=0 with a nonzero has exactly one real solution.',
         'Does every real equation ax+b=0 with a nonzero have exactly one real solution?',
         'Subtract b and divide by nonzero a: the unique solution is -b/a.',
         '3', 'Subtract the constant term before dividing by the coefficient.',
         'Solve 2x+5=11 over the reals.', 'Subtract 5 to get 2x=6, then divide by 2 to get x=3.',
         'Solve 2x+5=13 over the reals.', 'Subtract 5 and divide by 2: x=4, which I claim matches 3.'),
        ('probability', 'For disjoint events E and F, P(E union F)=P(E)+P(F).',
         'For disjoint events E and F, is P(E union F)=P(E)+P(F)?',
         'The probability additivity axiom gives the displayed equality for disjoint events.',
         '1/2', 'The event is partitioned into two disjoint pieces and their probabilities are added.',
         'Roll a fair six-sided die. What is the probability of rolling 1, 2 or 3?',
         'The disjoint pieces {1} and {2,3} have probabilities 1/6 and 2/6; their sum is 1/2.',
         'Roll a fair six-sided die. What is the probability of rolling 1 or 2?',
         'The disjoint singleton pieces have probabilities 1/6 each, totaling 1/3, which I claim matches 1/2.'),
        ('graph', 'In a finite simple undirected graph, the sum of vertex degrees is twice the number of edges.',
         'In every finite simple undirected graph, is the sum of vertex degrees twice the number of edges?',
         'Each edge has two endpoints and contributes one to each endpoint degree, hence two to the total.',
         '6', 'Each edge contributes two to the total of the vertex degrees.',
         'A finite simple undirected graph has degree sum 12. How many edges does it have?',
         'Each edge contributes two to the degree sum, so the number of edges is 12/2=6.',
         'A finite simple undirected graph has degree sum 14. How many edges does it have?',
         'Each edge contributes two, so there are 14/2=7 edges, which I claim matches 6.'),
        ('geometric', 'For real a and r with r not equal to 1 and positive integer n, the sum a+ar+...+ar^(n-1) is a(1-r^n)/(1-r).',
         'For real a and r with r not equal to 1 and positive integer n, is a+ar+...+ar^(n-1)=a(1-r^n)/(1-r)?',
         'Set S to the sum. Subtract rS from S: intermediate terms cancel, giving (1-r)S=a-ar^n. Divide by 1-r.',
         '31', 'Multiplying the finite sum by its common ratio and subtracting cancels the intermediate terms.',
         'Find the sum 1+2+4+8+16.',
         'Let S be the sum. Then 2S-S=32-1, so S=31; intermediate terms cancel.',
         'Find the sum 1+2+4+8.',
         'With S the sum, 2S-S=16-1=15, which I claim matches 31.'),
    ]
    fixtures = []
    for family, theorem, copy_q, proof, answer, clue, positive_q, positive_j, wrong_q, wrong_j in families:
        for kind, a, c, q, j, score, rationale in [
            ('copy', 'Yes', theorem, copy_q, proof, 0,
             'The complete proposition is supplied; changing it into a yes/no question adds no essential content.'),
            ('decorated_copy', 'Yes', theorem, 'A student named Mira asks on Tuesday: '+copy_q, proof, 0,
             'The name and day have no mathematical role; the proposition is still entirely supplied.'),
            ('substantive', answer, clue, positive_q, positive_j, 4,
             'The candidate supplies missing numerical premises/objects/target; its displayed calculation verifies the answer and uses the clue.'),
            ('wrong', answer, clue, wrong_q, wrong_j, 1,
             'The explicit calculation in the response contradicts the supplied final answer.'),
        ]:
            fixtures.append(dict(id=f'{family}-{kind}', family=family, category='authored_'+kind,
                final_answer=a, clues=[c], student_response={'question':q,'justification':j},
                acceptable_scores=[score], expected_shortcut=score==0,
                reference_reason=rationale, reference_derivation=j,
                reference_provenance='assistant-authored, analytically checked; not human gold'))
    base = Path('artifacts/reconstruct/d3-v2')
    for filename, index, label, score in [
        ('repaired-student.json',33,'qwen-33-copy',0),
        ('stronger-feasibility.json',33,'stronger-33-copy',0),
        ('stronger-feasibility.json',112,'stronger-112-target',4),
    ]:
        run = json.loads((base/filename).read_text())
        matches = [(k,v) for k,v in run['responses'].items() if v['source_index']==index
                   and v['sampling'].get('seed') in (0,None)]
        assert len(matches)==1
        key,response=matches[0]
        fixtures.append(dict(id=label,family=f'production-{index}',category='production_diagnostic',
            final_answer=response['public_evidence']['final_answer'],clues=response['public_evidence']['clues'],
            student_response=response['output'],acceptable_scores=[score],expected_shortcut=score==0,
            provenance={'artifact':str(base/filename),'response_key':key,'response_hash':stable_hash(response)},
            reference_reason=('Restates the supplied dominance theorem.' if score==0 else
                              'Infers the missing greatest-integer target. Largest k with 23k+1 <= -1000 is -44, giving -1011.'),
            reference_provenance='assistant review of saved production response'))
    repair = json.loads((base/'repair-study.json').read_text())
    attack = next(v for v in repair['copy_challenges'].values() if v['source_index']==86)
    teacher = json.loads((base/'stronger-feasibility.json').read_text())
    response = next(v for v in teacher['responses'].values() if v['source_index']==86)
    fixtures.append(dict(id='scale-86-copy',family='production-86',category='production_diagnostic',
        final_answer=response['public_evidence']['final_answer'],clues=response['public_evidence']['clues'],
        student_response={'question':attack['output']['question'],'justification':attack['output']['reason']},
        acceptable_scores=[0],expected_shortcut=True,
        reference_reason='Requests the scale point x=a explicitly named in the supplied clue.',
        provenance={'artifact':str(base/'repair-study.json'),'attack_hash':stable_hash(attack)},
        reference_provenance='copy challenge repackaged as response diagnostic; not a student generation'))
    assert len(fixtures)==20
    prompts={name:stable_hash(Path(f'data/prompts/reconstruct/runtime/{name}.md').read_text())
             for name in ['evaluate_p2','evaluate_p3']}
    payload=dict(protocol='docs/plans/reconstruct-amendment-u.md',fixtures=fixtures,
        prompt_hashes=prompts,planned_calls=40,maximum_cost_usd=.20,
        interpretation='Expected labels operationalize the proposed U criterion; p2 differences are not automatically old-spec errors.',
        gate='All 16 authored controls and 4 diagnostics must meet expected scores/shortcut; p3 substantive positives require substantive inference. Report groups separately.')
    dest.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    for name in prompts:
        (root/f'{name}.json').write_text(json.dumps(dict(sources={},banks={},partitions={'D1':[]},failures=[],judge_fixtures={},
            metadata={'fixtures_hash':stable_hash(payload),'prompt_hash':prompts[name],'planned_calls':20}),indent=2)+'\n')
    print(f'Frozen {len(fixtures)} cases; 4 authored families; 40 paired calls maximum.')


if __name__=='__main__':
    main()
