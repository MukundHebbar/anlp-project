import importlib.util
import unittest
from pathlib import Path

from anlp_project.reconstruct import load_prompt, render_template

spec = importlib.util.spec_from_file_location('probe', Path(__file__).resolve().parents[1] / 'scripts/probe_reconstruct_teacher.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class TeacherProbeTests(unittest.TestCase):
    def test_probe_prompt_contains_only_registered_public_input(self):
        run = {'sources': {'11': {'question': 'PRIVATE QUESTION', 'checked_solution': 'PRIVATE SOLUTION'}},
               'banks': {'b': {'prompt': 'role_sparse_2', 'output': {'hidden_support': 'PRIVATE SUPPORT'}}},
               'responses': {}}
        for i in [11,22,30,49]:
            run['responses'][str(i)] = {'source_index': i, 'prompt': 'student_p1',
                'sampling': {'seed': 0}, 'bank_key': 'b',
                'output': {'question': 'OTHER MODEL ANSWER'},
                'public_evidence': {'final_answer': '4', 'rendered_clues': '- PUBLIC CLUE'}}
        inputs = probe.public_probe_inputs(run)
        self.assertEqual(sorted(inputs), [11,22,30,49])
        for evidence in inputs.values():
            prompt = render_template(load_prompt('student_p1'), {
                'FINAL_ANSWER': evidence['final_answer'], 'RENDERED_CLUES': evidence['rendered_clues']})
            self.assertIn('PUBLIC CLUE', prompt)
            self.assertNotIn('PRIVATE', prompt)
            self.assertNotIn('OTHER MODEL ANSWER', prompt)
        del run['responses']['49']
        with self.assertRaises(ValueError):
            probe.public_probe_inputs(run)
