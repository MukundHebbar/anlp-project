#!/usr/bin/env python3
"""Freeze Z's missing-witness contrast and unchanged X/Y regressions; no calls."""
import difflib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash,atomic_write_json,utc_now,validate_bank
ROOT=Path('artifacts/reconstruct/witness-boundary-z')
ADDITION='''Question versus solution: a missing essential element must be needed to STATE the original mathematical question, not merely to SOLVE or prove it. First check whether its objects, premises and target can already be assembled from the public text by paraphrase and grammar. If so, reject question disclosure even when a witness, construction, counterexample, formula for the requested object, or verification is absent. In particular, an existence question does not require its witness to be specified in its statement. Omitting that witness withholds a solution, not a question premise. This does not prohibit a truly missing question parameter that must be inferred using the answer.\n\nExample: private question asks whether some integer square ends in digit6. Public answer Yes and observation "The proposed example is an integer square whose final digit is6" expose that existence question. REJECT even if the witness16 and its verification are absent.\n\n'''


def save_population(name,cases,prompts):
    root=ROOT/name;root.mkdir(parents=True)
    run=dict(sources={},partitions={'D1':list(range(len(cases)))},banks={},audits={},responses={},evaluations={},source_recovery={},failures=[],
      metadata={'protocol':'docs/plans/reconstruct-amendment-z.md','created_at':utc_now(),'student_readiness':{'status':'blocked_calibration_only'}})
    fixtures=[]
    for i,case in enumerate(cases):
        source=case['source'];bank=validate_bank(case['bank']);key=f'{i}:witness_boundary_z:{stable_hash(bank)}'
        run['sources'][str(i)]=source
        run['banks'][key]={'source_index':i,'prompt':'frozen_witness_boundary_z','model':'authored_fixture','output':bank}
        fixtures.append({k:v for k,v in case.items() if k not in ['source','bank']} | {'source_index':i,'bank_key':key,'bank_output_hash':stable_hash(bank),'source_record_hash':stable_hash(source)})
    m={'protocol':run['metadata']['protocol'],'fixtures':fixtures,'prompts':prompts,
       'prompt_file_hashes':{p:stable_hash(Path(f'data/prompts/reconstruct/runtime/{p}.md').read_text()) for p in prompts},
       'teacher_model':'deepseek-ai/DeepSeek-V4.1-Flash','reasoning_effort':'low','teacher_max_tokens':8192,
       'planned_initial_calls':len(cases)*len(prompts),'maximum_substudy_cost_usd':.10,'technical_retry_max':1,
       'reference_scope':'Assistant-authored/archived development references; not independent human gold.'}
    run['metadata']['manifest_hash']=stable_hash(m)
    atomic_write_json(root/'manifest.json',m);atomic_write_json(root/'run.json',run)
    return {'root':str(root),'manifest_hash':stable_hash(m),'planned_initial_calls':m['planned_initial_calls']}


def main():
    assert not ROOT.exists()
    y=json.loads(Path('artifacts/reconstruct/production-boundary-y/comparison.json').read_text())
    assert y['adoption_blocked_by_hard_negative_miss']
    old=Path('data/prompts/reconstruct/runtime/audit_source_disclosure_p3.md').read_text()
    path=Path('data/prompts/reconstruct/runtime/audit_source_disclosure_p4.md');assert not path.exists()
    assert old.count('Return JSON only:')==1
    new=old.replace('Return JSON only:',ADDITION+'Return JSON only:');path.write_text(new)
    ROOT.mkdir(parents=True)
    (ROOT/'prompt.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='audit_source_disclosure_p3',tofile='audit_source_disclosure_p4')))
    families=[
      ('integer','Does there exist a positive integer n satisfying2n=6?','n=3 is a witness. For the changed parameter5 there is no integer witness.',
       ['The proposed n is a positive integer.','It satisfies2n=6.'],
       ['The proposed n is a positive integer.','It satisfies2n=m for an unspecified positive integer m.'],
       'The right-hand parameter6 is missing, unlike the witness n=3. Yes constrains m to be even, but does not uniquely identify6.'),
      ('graph','Does there exist a simple undirected graph on6 vertices with every vertex of degree3?','K3,3 has6 vertices,9 edges and all degrees3. Five degree3 vertices are impossible by handshaking.',
       ['The proposed example is a simple undirected graph on6 vertices.','Every vertex has degree3.'],
       ['The proposed example is a simple undirected graph with an unspecified number n of vertices.','Every vertex has degree3.'],
       'Vertex count6 is missing; the actual edge set is merely a witness. Degree3 existence restricts n but allows different counts.'),
      ('triple','Do there exist three strictly increasing positive integers whose sum is15?','The triple4,5,6 works. Such a triple has sum at least1+2+3=6, so changing the sum to5 gives No.',
       ['The proposed example consists of three strictly increasing positive integers.','Their sum is15.'],
       ['The proposed example consists of three strictly increasing positive integers.','Their sum is an unspecified positive integer m.'],
       'The specified sum15 is missing. A particular triple is a solution witness, not a parameter needed to state the question.'),
      ('affine','Does there exist a real polynomial f of degree at most1 with f(0)=1, f(1)=2 and f(2)=3?','f(x)=1+x is a witness. The first two values force that polynomial and hence f(2)=3.',
       ['The desired f is a real polynomial of degree at most1.','It satisfies f(0)=1, f(1)=2 and f(2)=3.'],
       ['The desired f is a real polynomial of degree at most1.','It satisfies f(0)=1, f(1)=2 and f(2)=b for an unspecified real b.'],
       'The required third ordinate3 is missing. The first two values and Yes allow inferring b=3; this differs from withholding the polynomial witness formula.')]
    assert 2*3==6 and 4+5+6==15 and 1+2+3>5
    edges=[(u,v) for u in range(3) for v in range(3,6)]
    assert len(edges)==9 and all(sum(i in e for e in edges)==3 for i in range(6))
    cases=[]
    for family,question,solution,full,partial,reason in families:
        for condition,sentences,status in [('complete_question_missing_witness',full,'REJECT'),('missing_question_parameter',partial,'ACCEPT')]:
            bank={'status':'OK','clues':[{'id':f'c{j+1}','sentence':s,'fragment':s,'hidden_support':solution} for j,s in enumerate(sentences)],'withheld':reason}
            cases.append({'source':{'question':question,'final_answer':'Yes','checked_solution':solution},'bank':bank,'family':family,'condition':condition,
                'reference_status':status,'reference_argument':reason if status=='ACCEPT' else 'The complete existential proposition is public. An unknown witness is part of its solution, not missing question information.'})
    populations=[save_population('authored',cases,['audit_source_disclosure_p3','audit_source_disclosure_p4'])]
    for name,origin in [('x-regression','artifacts/reconstruct/inverse-disclosure-x'),('y-regression','artifacts/reconstruct/production-boundary-y')]:
        oldrun=json.loads(Path(origin,'run.json').read_text());oldm=json.loads(Path(origin,'manifest.json').read_text());cases=[]
        for f in oldm['fixtures']:
            cases.append({'source':oldrun['sources'][str(f['source_index'])],'bank':oldrun['banks'][f['bank_key']]['output'],
                'family':f['family'],'condition':f['condition'],'reference_status':f['reference_status'],'reference_argument':f['reference_argument'],
                'origin_artifact':str(Path(origin,'run.json')),'origin_bank_key':f['bank_key'],'origin_source_index':f['source_index'],
                'comparator_prompt':'audit_source_disclosure_p3'})
        populations.append(save_population(name,cases,['audit_source_disclosure_p4']))
    assert sum(p['planned_initial_calls'] for p in populations)==39
    atomic_write_json(ROOT/'manifest.json',{'protocol':'docs/plans/reconstruct-amendment-z.md','populations':populations,'planned_initial_calls':39,'aggregate_cost_cap_usd':.30,
        'source_prompt_only_changed':True,'public_prompt_fixed':'audit_public_p5','teacher_and_sampling_unchanged':True})
    print('Frozen8 witness controls,16 X regressions,7 Y boundaries;39 initial calls planned, none made.')


if __name__=='__main__':main()
