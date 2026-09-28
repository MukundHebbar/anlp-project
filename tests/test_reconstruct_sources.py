import unittest
from anlp_project.reconstruct_sources import normalize_option_answer


class SourceNormalizationTests(unittest.TestCase):
    def test_explicit_choice_mapping_preserves_original(self):
        source = {'question':'How many?\nA. 87429\nB. 89415\nC. 89326\nD. 89504', 'final_answer':'A'}
        result = normalize_option_answer(source)
        self.assertEqual(result['final_answer'],'87429')
        self.assertEqual(result['answer_normalization']['original_answer'],'A')
        self.assertEqual(source['final_answer'],'A')
        self.assertEqual(result['question'],source['question'])

    def test_no_guess_for_symbolic_answer(self):
        source = {'question':'Express the area in terms of A.', 'final_answer':'A'}
        self.assertEqual(normalize_option_answer(source),source)

    def test_ambiguous_or_missing_label_requires_review(self):
        for question in ['A. 1\nA. 2','B. 1\nC. 2','A. first line\ncontinued answer\nB. other']:
            with self.assertRaises(ValueError):
                normalize_option_answer({'question':question,'final_answer':'A'})
