#!/usr/bin/env python3
"""Freeze X's matched authored disclosure controls and one clarification; no calls."""
import difflib
import json
import sys
from fractions import Fraction
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash,atomic_write_json,utc_now,validate_bank
ROOT=Path('artifacts/reconstruct/inverse-disclosure-x')
PROMPTS=['audit_public_p4','audit_source_disclosure_p2','audit_public_p5','audit_source_disclosure_p3']
CLARIFICATION='''Boundary clarification: direct exposure and inverse-inference difficulty are separate. A genuinely absent essential premise may have to be inferred by using the supplied final answer as a constraint. This can be a legitimate inverse task even when the calculation is elementary or uniquely identifies that premise. Do not reject solely because answer-conditioned inversion is easy or unique. In contrast, a value already given as an arithmetic expression with all operands public is exposed; simplifying it is merely routine completion. Withholding an essential value is not enough if other clues state it equivalently or display a complete/nearly complete forward derivation. Continue rejecting complete premise-target bundles, copied questions and complete solutions. Identify the actual missing premise and the inverse inference; do not grant acceptance merely because the word "unknown" appears. This clarifies "routine arithmetic" above: forward simplification of disclosed values does not count as withholding, while using the answer to infer a genuinely missing essential premise can count.\n\n'''


def main():
    assert not (ROOT/'run.json').exists()
    previous=json.loads(Path('artifacts/reconstruct/target-example-w/student.json').read_text())
    assert len(previous['responses'])==len(previous['evaluations'])==len(previous['source_recovery'])==16
    families=[
      dict(name='rectangle',question='A rectangle has perimeter20 and area24. Find its longer side.',answer='6',solution='x+y=10, xy=24. The sides are4 and6, so the longer side is6.',
        full=['The side lengths satisfy x+y=10 and xy=24.','The requested quantity is the longer side length.'],
        cosmetic=['The side lengths satisfy x+y=5+5 and xy=3*8.','The requested quantity is the longer side length.'],
        inverse=['The rectangle side lengths satisfy x+y=10.','Its area in terms of one side x is x(10-x).','The requested quantity is the longer side length.'],
        proof=['The rectangle has side lengths4 and6.','Selecting the longer side gives6.'],
        inverse_argument='The area24 is absent. Using answer6 as the longer side, infer the other side10-6=4 and then area6*4=24.'),
      dict(name='linear',question='Solve3x+2=14 for real x.',answer='4',solution='Subtract2 to obtain3x=12; divide by3 to obtainx=4.',
        full=['The equation is3x+2=14.','The requested quantity is the real solution x.'],
        cosmetic=['The equation is(1+2)x+2=7+7.','The requested quantity is the real solution x.'],
        inverse=['The equation has the form ax+2=14 for a positive coefficient a.','The requested quantity is its real solution x.'],
        proof=['Subtracting2 from the two sides gives3x=12.','Dividing by3 givesx=4.'],
        inverse_argument='The coefficient a=3 is absent. Insert the supplied solution x=4 into ax+2=14 to infer a=(14-2)/4=3.'),
      dict(name='urn',question='An urn contains6 red balls and4 blue balls. One ball is chosen uniformly. What is the probability it is red?',answer='3/5',solution='There are10 equally likely balls,6 red, so the probability is6/10=3/5.',
        full=['The urn contains6 red balls and4 blue balls.','One ball is chosen uniformly; the requested quantity is the probability it is red.'],
        cosmetic=['The urn contains3+3 red balls and2+2 blue balls.','One ball is chosen uniformly; the requested quantity is the probability it is red.'],
        inverse=['The urn contains10 balls, each either red or blue.','One ball is chosen uniformly; the requested quantity is the probability it is red.'],
        proof=['There are6 favorable outcomes among10 equally likely outcomes.','The probability of drawing a red ball is6/10=3/5.'],
        inverse_argument='The color counts are absent. Supplied red probability3/5 and total10 imply6 red and4 blue by inverse proportion.'),
      dict(name='motion',question='A vehicle travels at a constant60 km/h for2 hours. How far does it travel?',answer='120 km',solution='Distance=speed*time=60*2=120 km.',
        full=['The vehicle travels at a constant60 km/h for2 hours.','The requested quantity is its distance traveled.'],
        cosmetic=['The vehicle travels at a constant(30+30) km/h for(1+1) hours.','The requested quantity is its distance traveled.'],
        inverse=['The vehicle travels at a constant speed for2 hours.','The requested quantity is its distance traveled.'],
        proof=['Distance equals speed times duration.','The distance calculation is60 km/h times2 hours, giving120 km.'],
        inverse_argument='Speed60 km/h is absent. Supplied distance120 km and duration2 h imply speed120/2=60 km/h.')]
    assert 6*(10-6)==24 and Fraction(14-2,4)==3 and Fraction(3,5)*10==6 and Fraction(120,2)==60
    ROOT.mkdir(parents=True,exist_ok=True)
    prompt_dir=Path('data/prompts/reconstruct/runtime')
    for old,new in [('audit_public_p4','audit_public_p5'),('audit_source_disclosure_p2','audit_source_disclosure_p3')]:
        oldtext=(prompt_dir/f'{old}.md').read_text();newpath=prompt_dir/f'{new}.md';assert not newpath.exists()
        assert oldtext.count('Return JSON only:')==1
        newtext=oldtext.replace('Return JSON only:',CLARIFICATION+'Return JSON only:')
        newpath.write_text(newtext)
        (ROOT/f'{new}.diff').write_text(''.join(difflib.unified_diff(oldtext.splitlines(True),newtext.splitlines(True),fromfile=old,tofile=new)))
    run=dict(sources={},partitions={'D1':list(range(16))},banks={},audits={},responses={},evaluations={},source_recovery={},failures=[],
        metadata={'protocol':'docs/plans/reconstruct-amendment-x.md','created_at':utc_now(),'student_readiness':{'status':'blocked_controls_only'},'source_population':'Authored development controls, not confirmation sources','maximum_substudy_cost_usd':.50})
    fixtures=[]
    for family in families:
        for condition in ['full','cosmetic','inverse','proof']:
            i=len(fixtures);clues=[{'id':f'c{j+1}','sentence':text,'fragment':text,'hidden_support':family['solution']} for j,text in enumerate(family[condition])]
            bank=validate_bank({'status':'OK','clues':clues,'withheld':family['inverse_argument'] if condition=='inverse' else 'No essential content withheld: negative disclosure control.'})
            source={'question':family['question'],'final_answer':family['answer'],'checked_solution':family['solution']}
            key=f'{i}:authored_x:{stable_hash(bank)}'
            run['sources'][str(i)]=source
            run['banks'][key]={'source_index':i,'prompt':'authored_inverse_disclosure_x','model':'authored_fixture','output':bank}
            fixtures.append({'source_index':i,'family':family['name'],'condition':condition,'reference_status':'ACCEPT' if condition=='inverse' else 'REJECT',
                'reference_argument':family['inverse_argument'] if condition=='inverse' else {'full':'All essential premises and target are public.','cosmetic':'Arithmetic spelling exposes all original numerical parameters without answer-conditioned inference.','proof':'The forward solution is already displayed; missing original wording or premise format does not make it sparse.'}[condition],
                'bank_key':key,'bank_output_hash':stable_hash(bank),'source_record_hash':stable_hash(source)})
    manifest={'protocol':run['metadata']['protocol'],'fixtures':fixtures,'prompts':PROMPTS,'prompt_file_hashes':{p:stable_hash((prompt_dir/f'{p}.md').read_text()) for p in PROMPTS},
        'planned_initial_calls':64,'families':4,'conditions':4,'technical_retry_max':1,'teacher_model':'deepseek-ai/DeepSeek-V4.1-Flash','reasoning_effort':'low','teacher_max_tokens':8192,
        'reference_scope':'Authored proposed operational definition, not independent human gold; historical disagreements not retroactively counted as errors.',
        'prespecified_gate':'Every candidate hard negative rejected; inverse acceptances must name a genuine missing premise and correct inference; any hard-negative miss blocks adoption.'}
    run['metadata']['manifest_hash']=stable_hash(manifest)
    atomic_write_json(ROOT/'manifest.json',manifest);atomic_write_json(ROOT/'run.json',run)
    print('Frozen16 authored controls,4 prompt versions and64 initial judgments. No calls.')


if __name__=='__main__':main()
