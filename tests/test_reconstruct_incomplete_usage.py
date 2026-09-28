import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from anlp_project.reconstruct import ChatClient, IncompleteCompletionError, failure, actual_cost


class IncompleteUsageTests(unittest.TestCase):
    def test_empty_visible_completion_preserves_budget_and_finish_reason(self):
        client = ChatClient.__new__(ChatClient)
        client.client = Mock()
        client.client.chat.completions.create.return_value = SimpleNamespace(
            usage=SimpleNamespace(model_dump=lambda: {'estimated_cost': .01, 'completion_tokens': 8192}),
            choices=[SimpleNamespace(finish_reason='length', message=SimpleNamespace(content='', reasoning_content='test reasoning'))])
        run = {'failures': []}
        try:
            client.complete(model='test',prompt='test',max_tokens=8192,temperature=0)
        except IncompleteCompletionError as error:
            failure(run,'evaluate',1,'key',error)
        else:
            self.fail('Empty visible output must remain a failure')
        self.assertEqual(run['failures'][0]['raw']['finish_reason'],'length')
        self.assertEqual(run['failures'][0]['raw']['usage']['completion_tokens'],8192)
        self.assertAlmostEqual(actual_cost(run),.01)
