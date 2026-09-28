import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TerminalGuardTest(unittest.TestCase):
    def test_inflight_final_request_cannot_start_paid_judging(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state = {'metadata': {'jobs': ['1:a:0'], 'attempted_jobs': ['1:a:0']},
                     'responses': {}, 'failures': []}
            (root / 'student.json').write_text(json.dumps(state))
            for script in ['run_reconstruct_richer_judges.py', 'verify_reconstruct_response_math.py']:
                with self.subTest(script=script):
                    result = subprocess.run([sys.executable, 'scripts/' + script,
                                             '--study-root', str(root)], capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('Student requests still in flight', result.stderr)
                    self.assertEqual(json.loads((root / 'student.json').read_text()), state)
            self.assertFalse((root / 'math-verification.json').exists())


if __name__ == '__main__':
    unittest.main()
