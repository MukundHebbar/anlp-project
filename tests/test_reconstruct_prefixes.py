import copy
import importlib.util
import unittest
from pathlib import Path
from anlp_project.reconstruct import choose_clues, accepted_bank

spec = importlib.util.spec_from_file_location('prefixes', Path(__file__).resolve().parents[1] / 'scripts/materialize_reconstruct_prefixes.py')
prefixes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prefixes)


class PrefixTests(unittest.TestCase):
    def test_parent_disclosure_rejection_does_not_bypass_exact_prefix_audit(self):
        clues = [{'id':f'c{i}','sentence':f'Fact {i}','fragment':f'Fact {i}','hidden_support':'support'} for i in range(1,4)]
        run = {'metadata': {'eligible_sources':[1], 'required_bank_audits':{}},
            'banks': {'b': {'source_index':1,'prompt':'convert_p2','output':{'status':'OK','clues':clues}}},
            'audits': {'s': {'source_index':1,'bank_key':'b','prompt':'audit_support_p1','output':{
                'status':'ACCEPT','checks':[{'id':c['id'],'supported':True,'self_contained':True} for c in clues]}},
                'p': {'source_index':1,'bank_key':'b','prompt':'audit_role_p3','output':{'status':'REJECT'}}}}
        original = copy.deepcopy(run)
        out = prefixes.materialize(run,'parent.json',7)
        self.assertEqual(run,original)
        key,bank = next((k,v) for k,v in out['banks'].items() if v['prompt']=='nested_k2')
        self.assertEqual(choose_clues(bank['output'],2,7),choose_clues(run['banks']['b']['output'],2,7))
        with self.assertRaises(ValueError):
            accepted_bank(out,1,'nested_k2')
        out['audits']['new-public'] = {'source_index':1,'bank_key':key,'prompt':'audit_role_p3','output':{'status':'ACCEPT'}}
        self.assertEqual(accepted_bank(out,1,'nested_k2')[0],key)
        run['audits']['s']['output']['status']='REJECT'
        rejected = prefixes.materialize(run,'parent.json',7)
        self.assertFalse(any(v['prompt']=='nested_k2' for v in rejected['banks'].values()))
