#!/usr/bin/env python3
"""Compose generated role cues with accepted base banks; does not approve them."""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import accepted_bank, latest_bank, stable_hash, utc_now
from anlp_project.storage import atomic_write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True)
    p.add_argument('--roles',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--split',default='D2')
    a=p.parse_args()
    if a.output.exists():
        raise ValueError('Use a new output file; never overwrite an experiment')
    base=json.loads(a.base.read_text()); roles=json.loads(a.roles.read_text())
    out=copy.deepcopy(base)
    for index in base['partitions'][a.split]:
        base_key,bank=accepted_bank(base,index,'convert_p2')
        role_key,role=latest_bank(roles,index,'convert_role_p1')
        assert len(role['output']['clues'])==1
        cue=copy.deepcopy(role['output']['clues'][0]); cue['id']='role'
        output={'status':'OK','clues':copy.deepcopy(bank['output']['clues'])+[cue],
                'role_cue_id':'role','withheld':'Original defining conditions and exact target remain partial; requires joint audit.'}
        digest=stable_hash(output)
        out['banks'][f'{index}:role_augmented:{digest}']={
            'source_index':index,'prompt':'role_augmented','prompt_hash':digest,
            'model':'mechanical_composition','output':output,
            'composition':{'base_bank_key':base_key,'role_bank_key':role_key,'role_artifact':str(a.roles),
                           'preserve_original_clue_order':True},'created_at':utc_now()}
    out['metadata']['role_composition']={'base':str(a.base),'roles':str(a.roles),'split':a.split,'requires_joint_audit':True}
    atomic_write_json(a.output,out)
    print(f'Composed {len(base["partitions"][a.split])} unapproved role banks')


if __name__=='__main__':main()
