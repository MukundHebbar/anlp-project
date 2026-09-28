import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('batch', Path(__file__).resolve().parents[1] / 'scripts/run_reconstruct_batch.py')
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


class BatchRetryTests(unittest.TestCase):
    def test_audit_retry_preserves_rejects_and_excludes_exhausted_or_other_prompts(self):
        bank = {'status':'OK','clues':[]}
        def key(i, prompt='p'):
            return f'{i}:{batch.r.stable_hash(bank)}:{prompt}:m:low'
        run = {'banks':{str(i):{'source_index':i,'prompt':'convert','output':bank}
                        for i in range(5)},
               'failures':[{'stage':'audit','key':key(i)} for i in [0,1,1,2]]
                           + [{'stage':'audit','key':key(3,'other')}],
               'audits':{key(2):{'output':{'status':'REJECT'}}}}
        self.assertEqual(batch.retryable_audit_jobs(
            run,[(None,i) for i in range(5)],'convert','p','m','low'),[(None,0)])

    def test_retry_only_once_never_rescore_success_or_unrelated_configuration(self):
        run = {'failures': [
            {'stage':'evaluate','key':'once:p:m:low'},
            {'stage':'evaluate','key':'twice:p:m:low'},
            {'stage':'evaluate','key':'twice:p:m:low'},
            {'stage':'evaluate','key':'recovered:p:m:low'},
            {'stage':'evaluate','key':'other:q:m:low'},
        ], 'evaluations': {'recovered:p:m:low': {'output': {'score': 0}}}}
        jobs = [(name, i) for i,name in enumerate(['once','twice','recovered','other','new'])]
        self.assertEqual(batch.retryable_evaluation_jobs(run,jobs,'p','m','low'), [('once',0)])
