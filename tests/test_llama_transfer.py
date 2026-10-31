import json
import math
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from anlp_project.gemma_judging import GemmaJudge, read_probabilities
from anlp_project.student_models import family, stop_tokens

ROOT = Path(__file__).resolve().parents[1]


class StudentCompatibility(unittest.TestCase):
    def test_llama_uses_native_end_of_turn_and_all_configured_stops(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            (p/'config.json').write_text(json.dumps({'model_type': 'llama'}))
            (p/'generation_config.json').write_text(json.dumps({'eos_token_id': [128001,128008,128009]}))
            tok = SimpleNamespace(get_vocab=lambda: {'<|eot_id|>':128009}, eos_token_id=128001)
            self.assertEqual(stop_tokens(tok, folder), ({128001,128008,128009},128009))
            tok.get_vocab = lambda: {}
            with self.assertRaises(ValueError): stop_tokens(tok, folder)

    def test_qwen_retains_original_stop_handling(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'config.json').write_text(json.dumps({'model_type':'qwen3_5'}))
            tok = SimpleNamespace(convert_tokens_to_ids={'<|im_end|>':11,'<|endoftext|>':12}.__getitem__)
            self.assertEqual(stop_tokens(tok, folder), ({11,12},11))

    def test_frozen_configs_preserve_historical_optimizer_and_task_settings(self):
        for task in ('solve','judge','reconstruct'):
            current = json.loads((ROOT/f'phase2/llama_transfer/configs/{task}.json').read_text())
            original = json.loads((ROOT/f'docs/reports/latex/configs/{"solve_new" if task=="solve" else task}.json').read_text())
            for key in ('optimizer','prompts_per_step','samples_per_prompt','rollout','rollout_max_tokens',
                        'importance_sampling_cap','norm_tokens','drop_truncated','kl_anchor_beta'):
                self.assertEqual(current[key],original[key],(task,key))
            self.assertEqual(current['lora']['r'],64)
            self.assertEqual(current['lora']['alpha'],64)
            self.assertEqual(current['seed'],0)


class GemmaTransport(unittest.TestCase):
    def test_explicit_probabilities_include_low_mass_and_multiple_spellings(self):
        top = {'token_id:1':math.log(.01),'token_id:2':math.log(.02),'token_id:3':math.log(.07)}
        probs, mass = read_probabilities(top,['Yes','No'],{'yes':[1,2],'no':[3]})
        self.assertAlmostEqual(probs[0],.3)
        self.assertAlmostEqual(mass,.1)
        del top['token_id:2']
        with self.assertRaises(ValueError):
            read_probabilities(top,['Yes','No'],{'yes':[1,2],'no':[3]})

    def test_http_contract_and_typed_answers_without_forcing_tokens(self):
        judge = GemmaJudge.__new__(GemmaJudge)
        judge.name='reward-judge';judge.url='http://localhost:8102/v1/completions';judge.tokens=0
        judge.label_ids={'0':[10],'1':[11],'yes':[12],'no':[13],'a':[14],'b':[15]}
        judge.prompt=lambda text:text
        judge.tok=SimpleNamespace(encode=lambda text,add_special_tokens: [100,101] if not add_special_tokens else [])
        questions={'score':{'type':'score','instructions':'grade','criteria':['bad','good']},
                   'noul':{'type':'noul','instructions':'check','criteria':{'true':'yes','false':'no'}},
                   'choice':{'type':'choice','instructions':'pick','criteria':{'first':'x','second':'y'}}}
        choices=[]
        for index, ids in enumerate([(10,11),(12,13),(14,15)]):
            choices.append({'index':index,'logprobs':{'top_logprobs':[
                {f'token_id:{i}':math.log(p) for i,p in zip(ids,[.2,.6])}]}})
        payload={'choices':list(reversed(choices)),'usage':{'prompt_tokens':123}}
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self): return json.dumps(payload).encode()
        with patch('urllib.request.urlopen',return_value=Response()) as request:
            result=judge.call({},questions)
        body=json.loads(request.call_args.args[0].data)
        self.assertEqual(body['logprob_token_ids'],[10,11,12,13,14,15])
        self.assertNotIn('allowed_token_ids',body)
        self.assertEqual(body['max_tokens'],1)
        self.assertEqual(body['prompt'],[[100,101]]*3)
        self.assertAlmostEqual(result['answers']['score']['score'],.75)
        self.assertAlmostEqual(result['answers']['noul']['noul'],.25)
        self.assertEqual(result['answers']['choice']['choice'],'second')
        self.assertEqual(judge.tokens,123)


if __name__=='__main__': unittest.main()
