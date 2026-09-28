import unittest

from anlp_project.reconstruct_partial_credit import aggregate, relaxed_rating, balanced_rating, balanced_rating_v4


def records(p=4, t=4, e=4, m=4, shortcut=False):
    return ({'status': 'scored', 'premise_fidelity': {'score': p},
             'target_fidelity': {'score': t}},
            {'status': 'scored', 'evidence_integration': {'score': e},
             'mathematical_validity': {'score': m}, 'shortcut': {'present': shortcut}})


class PartialCreditTests(unittest.TestCase):
    def test_v4_changes_only_lower_threes(self):
        self.assertIsNone(balanced_rating_v4(None))
        for score in [0, 18.74, 18.75, 37.49, 37.5, 43.74, 43.75, 50, 56.25, 75, 100]:
            expected = 2 if 37.5 <= score < 43.75 else balanced_rating(score)
            with self.subTest(score=score):
                self.assertEqual(balanced_rating_v4(score), expected)

    def test_v4_rejects_invalid_scores(self):
        for score in [True, -1, 101, float('nan'), float('inf'), '75']:
            with self.subTest(score=score), self.assertRaises(ValueError):
                balanced_rating_v4(score)

    def test_balanced_rating_boundaries_and_missingness(self):
        for score, expected in [(None, None), (0, 1), (18.74, 1), (18.75, 2), (37.49, 2), (37.5, 3), (50, 3), (56.24, 3), (56.25, 4), (74.99, 4), (75, 5), (100, 5)]:
            with self.subTest(score=score):
                self.assertEqual(balanced_rating(score), expected)

    def test_balanced_rating_rejects_invalid_scores(self):
        for score in [True, -1, 101, float('nan'), float('inf'), '75']:
            with self.subTest(score=score), self.assertRaises(ValueError):
                balanced_rating(score)

    def test_relaxed_rating_boundaries_and_missingness(self):
        for score, expected in [(None, None), (0, 1), (19.99, 1), (20, 2), (40, 3), (49.99, 3), (50, 4), (69.99, 4), (70, 5), (100, 5)]:
            with self.subTest(score=score):
                self.assertEqual(relaxed_rating(score), expected)

    def test_relaxed_rating_rejects_invalid_scores(self):
        for score in [True, -1, 101, float('nan'), float('inf'), '75']:
            with self.subTest(score=score), self.assertRaises(ValueError):
                relaxed_rating(score)

    def test_underspecified_question_keeps_partial_credit(self):
        out = aggregate(*records(2, 4, 2, 1))
        self.assertEqual(out['score_100'], 56.25)
        self.assertEqual(out['rating_1_to_5'], 3)

    def test_shortcut_is_zero_but_raw_dimensions_preserved(self):
        out = aggregate(*records(shortcut=True))
        self.assertEqual(out['raw_dimension_total'], 100)
        self.assertEqual(out['score_100'], 0)

    def test_missing_judge_does_not_become_failure_score(self):
        fidelity, validity = records()
        out = aggregate(None, validity)
        self.assertIsNone(out['score_100'])
        self.assertEqual(out['score_bounds'], [50, 100])
        out = aggregate(fidelity, None)
        self.assertIsNone(out['score_100'])
        self.assertEqual(out['score_bounds'], [0, 100])

    def test_needs_review_does_not_silently_become_scored(self):
        f, v = records()
        f['status'] = 'needs_review'
        self.assertIsNone(aggregate(f, v)['score_100'])

    def test_boolean_is_not_a_dimension_score(self):
        with self.assertRaises(ValueError):
            aggregate(*records(p=True))

    def test_top_band_is_not_six(self):
        self.assertEqual(aggregate(*records())['rating_1_to_5'], 5)
