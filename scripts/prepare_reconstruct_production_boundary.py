#!/usr/bin/env python3
"""Freeze Y's archived exact production boundaries, without changing originals."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash,atomic_write_json,utc_now
ROOT=Path('artifacts/reconstruct/production-boundary-y')


def main():
    assert not (ROOT/'run.json').exists()
    x=json.loads(Path('artifacts/reconstruct/inverse-disclosure-x/comparison.json').read_text())
    for p in ['audit_public_p5','audit_source_disclosure_p3']:
        assert x['summaries'][p]['all_authored_references_matched']
    W='artifacts/reconstruct/target-example-w/';V='artifacts/reconstruct/verified-examples-v/';D='artifacts/reconstruct/d3-v2/'
    cases=[(W+'run.json',46,'convert_p5','ACCEPT','Essential column heights omitted; answer-conditioned multinomial inversion needed.'),
           (W+'run.json',129,'convert_p5','ACCEPT','Essential length omitted; inverse recurrence search needed, with documented multiple matches.'),
           (W+'repair-study.json',80,'repair_disclosure_p1','ACCEPT','Exact linear integrand coefficients omitted; curve, general form and target do not supply them.'),
           (W+'run.json',80,'convert_p5','REJECT','Equal partial derivatives and zero Green integrand expose complete zero-integral argument.'),
           (W+'run.json',96,'convert_p5','REJECT','F(x)~x^8/12 plus target sin(F(x))/x^8 leaves only routine sine asymptotic, exposing nearly complete proof.'),
           (V+'run.json',62,'convert_p4','REJECT','Shifted function, sole principal term and entire regular part disclose the convergence proof.'),
           (D+'repair-study.json',123,'repair_disclosure_p1','REJECT','Existential source question can be assembled from proposed infinite natural sequence and partial sums excluding perfect powers. Missing witness is missing proof, not missing question premise.')]
    run=dict(sources={},partitions={'D1':list(range(7))},banks={},audits={},responses={},evaluations={},source_recovery={},failures=[],
        metadata={'protocol':'docs/plans/reconstruct-amendment-y.md','created_at':utc_now(),'student_readiness':{'status':'blocked_diagnostics_only'}})
    fixtures=[]
    for i,(path,index,prompt,expected,reason) in enumerate(cases):
        old=json.loads(Path(path).read_text())
        matches=[(k,b) for k,b in old['banks'].items() if b['source_index']==index and b['prompt']==prompt]
        assert len(matches)==1
        key,bank=matches[0];source=old['sources'][str(index)];newkey=f'{i}:archived_boundary:{stable_hash(bank["output"])}'
        run['sources'][str(i)]=source
        run['banks'][newkey]={'source_index':i,'prompt':'archived_production_boundary_y','model':'authored_fixture','output':bank['output'],
                              'provenance':'Exact archived bank copied without alteration; original converter request remains in origin artifact.'}
        fixtures.append({'source_index':i,'original_source_index':index,'family':str(index),'condition':f'{index}:{prompt}',
            'reference_status':expected,'reference_argument':reason,'bank_key':newkey,'bank_output_hash':stable_hash(bank['output']),
            'source_record_hash':stable_hash(source),'origin_artifact':path,'origin_bank_key':key})
    prompts=['audit_public_p5','audit_source_disclosure_p3']
    manifest={'protocol':run['metadata']['protocol'],'fixtures':fixtures,'prompts':prompts,
        'prompt_file_hashes':{p:stable_hash(Path(f'data/prompts/reconstruct/runtime/{p}.md').read_text()) for p in prompts},
        'planned_initial_calls':14,'families':6,'conditions':7,'technical_retry_max':1,'teacher_model':'deepseek-ai/DeepSeek-V4.1-Flash',
        'reasoning_effort':'low','teacher_max_tokens':8192,'maximum_substudy_cost_usd':.20,
        'reference_scope':'Selected archived development boundaries; assistant mathematical/semantic references, not independent human gold.'}
    run['metadata']['manifest_hash']=stable_hash(manifest)
    ROOT.mkdir(parents=True,exist_ok=True);atomic_write_json(ROOT/'manifest.json',manifest);atomic_write_json(ROOT/'run.json',run)
    print('Frozen7 archived cases across6 families,14 judgments; no original records changed and no calls made.')


if __name__=='__main__':main()
