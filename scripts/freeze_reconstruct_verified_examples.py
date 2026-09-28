#!/usr/bin/env python3
"""Freeze V demonstrations and metadata-only D4/C25-extension allocation."""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project.reconstruct import stable_hash


def main():
    root=Path('artifacts/reconstruct/verified-examples-v')
    prompt_path=Path('data/prompts/reconstruct/runtime/student_p12_verified_examples.md')
    manifest_path=Path('data/manifests/reconstruct-d4-allocation-v1.json')
    if prompt_path.exists() or manifest_path.exists():
        raise SystemExit('V freeze already exists; refusing overwrite')
    comparison=json.loads(Path('artifacts/reconstruct/inference-u/comparison.json').read_text())
    assert comparison['decision']=='passes_development_gate'
    teacher_path=Path('artifacts/reconstruct/d3-v2/stronger-feasibility.json')
    teacher=json.loads(teacher_path.read_text())
    incumbent_path=Path('data/prompts/reconstruct/runtime/student_p10_recover_original.md')
    incumbent=incumbent_path.read_text()
    head,rest=incumbent.split('\n\nExample:\n',1)
    _,tail=rest.split('\n\nReturn JSON only:\n',1)
    examples=[];provenance=[]
    for index in [8,112,141]:
        key,response=next((k,v) for k,v in teacher['responses'].items() if v['source_index']==index)
        evidence=response['public_evidence']
        examples.append('Example:\nAnswer: '+evidence['final_answer']+'\nObservations:\n'+evidence['rendered_clues']+
                        '\nOutput: '+json.dumps(response['output'],ensure_ascii=False))
        provenance.append(dict(source_index=index,artifact=str(teacher_path),response_key=key,
                               response_hash=stable_hash(response),evidence_hash=stable_hash(evidence)))
    candidate=head+'\n\n'+'\n\n'.join(examples)+'\n\nReturn JSON only:\n'+tail
    parent_path=Path('data/manifests/reconstruct-reserve-allocation-v1.json')
    parent=json.loads(parent_path.read_text())
    pool=sorted(parent['partitions']['contingency'])
    rng=random.Random(20260923)
    extension=rng.choice(pool)
    by_topic=defaultdict(list)
    for index in pool:
        if index!=extension: by_topic[parent['source_metadata'][str(index)]['broad_topic']].append(index)
    d4=[]
    for topic in sorted(by_topic):
        group=sorted(by_topic[topic]);rng.shuffle(group)
        assert len(group)>=3
        d4.extend(group[:3])
    d4=sorted(d4)
    assert len(d4)==12 and extension not in d4
    assert not set(d4)&set(parent['partitions']['D3']+parent['partitions']['R']+parent['existing_partitions_unchanged']['C'])
    manifest=dict(protocol='docs/plans/reconstruct-amendment-v.md',allocation_seed=20260923,
        parent_manifest=str(parent_path),parent_hash=stable_hash(parent),
        rule='Choose one C25 extension ID from sorted contingency, then shuffle remaining IDs per sorted broad topic and take three per topic.',
        partitions={'D4':d4,'C25_proposed':parent['existing_partitions_unchanged']['C']+[extension],
                    'R':parent['partitions']['R'],'contingency_remaining':sorted(set(pool)-set(d4)-{extension})},
        proposed_C25_extension=extension,
        semantic_family_review='pending; metadata-only allocation does not prove independence',
        D4_metadata={str(i):parent['source_metadata'][str(i)] for i in d4},
        demonstrations=provenance,
        prompt_file_hashes={'student_p10_recover_original':stable_hash(incumbent),'student_p12_verified_examples':stable_hash(candidate)},
        interpretation='Demonstration package changes count, content, and prompt length together; no isolated optimal-count claim.')
    root.mkdir(parents=True,exist_ok=True)
    prompt_path.write_text(candidate)
    manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    (root/'freeze.json').write_text(json.dumps({'manifest':str(manifest_path),'manifest_hash':stable_hash(manifest),
        'student_generation_started':False,'source_content_review_started':False},indent=2)+'\n')
    print(json.dumps({'D4':d4,'C25_extension_proposed':extension,'demonstrations':[8,112,141]},indent=2))


if __name__=='__main__': main()
