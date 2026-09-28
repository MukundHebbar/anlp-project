#!/usr/bin/env python3
"""Create unchanged, order-preserving prefixes with explicit inherited support."""
import argparse
import copy
import json
from pathlib import Path
from anlp_project.reconstruct import choose_clues, stable_hash, utc_now
from anlp_project.storage import atomic_write_json


def materialize(base, parent_path, seed=20260920):
    out = copy.deepcopy(base)
    inventory = []
    for index in base['metadata']['eligible_sources']:
        banks = [(key,row) for key,row in base['banks'].items()
                 if row['source_index']==index and row['prompt']=='convert_p2' and row['output']['status']=='OK']
        if not banks:
            inventory.append({'source_index':index,'status':'missing_bank'})
            continue
        base_key, bank = banks[-1]
        supports = [(key,row) for key,row in base['audits'].items()
                    if row['bank_key']==base_key and row['prompt']=='audit_support_p1']
        if not supports or supports[-1][1]['output']['status']!='ACCEPT':
            inventory.append({'source_index':index,'status':'support_not_accepted'})
            continue
        support_key, support = supports[-1]
        ordered = choose_clues(bank['output'],len(bank['output']['clues']),seed)
        for count in [1,2,3]:
            if count > len(ordered):
                inventory.append({'source_index':index,'clue_count':count,'status':'insufficient_honest_clues'})
                continue
            clues = copy.deepcopy(ordered[:count])
            ids = [c['id'] for c in clues]
            output = {'status':'OK','clues':clues,'fixed_order_ids':ids,'fixed_order_seed':seed}
            name = f'nested_k{count}'
            digest = stable_hash(output)
            key = f'{index}:{name}:{digest}'
            out['banks'][key] = {'source_index':index,'prompt':name,'prompt_hash':digest,
                'model':'mechanical_composition','output':output,'created_at':utc_now(),
                'composition':{'base_bank_key':base_key,'parent_artifact':str(parent_path),
                               'selection_seed':seed,'selected_clue_ids':ids,'unchanged_sentences':True}}
            checks = [copy.deepcopy(c) for c in support['output']['checks'] if c['id'] in ids]
            assert len(checks)==count and all(c['supported'] and c['self_contained'] for c in checks)
            assert sorted(c['id'] for c in checks)==sorted(ids)
            out['audits'][f'{key}:inherited-support'] = {
                'source_index':index,'bank_key':key,'prompt':'audit_support_inherited_p1',
                'model':'mechanical_composition','output':{'status':'ACCEPT','scope':'source_support',
                    'checks':checks,'distinct_observations':True,
                    'reason':'Unchanged selected assertions inherit accepted source support; not a new teacher judgment.'},
                'provenance':{'parent_audit_key':support_key,'parent_artifact':str(parent_path)}}
            out['metadata']['required_bank_audits'][name] = ['audit_support_inherited_p1','audit_role_p3']
            assert choose_clues(output,count,seed)==ordered[:count]
            inventory.append({'source_index':index,'clue_count':count,'status':'awaiting_public_audit',
                              'bank_key':key,'selected_clue_ids':ids})
    out['metadata']['prefix_materialization'] = {'registered_amendment':'J','parent':str(parent_path),
        'parent_content_sha256':stable_hash(base),'seed':seed,'inventory':inventory}
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('Never overwrite a materialized experiment')
    result = materialize(json.loads(a.base.read_text()),a.base)
    atomic_write_json(a.output,result)
    print(json.dumps(result['metadata']['prefix_materialization']['inventory'],indent=2))


if __name__=='__main__':
    main()
