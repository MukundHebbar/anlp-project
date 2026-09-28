import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r

class BoundsTest(unittest.TestCase):
    def test_mismatched_registered_bound_fails_before_provider_client(self):
        args=SimpleNamespace(convert_prompt='test_prompt',max_bank_clues=4)
        run={'metadata':{'conversion_clue_bounds':{'test_prompt':[3,5]}}}
        with patch.object(r,'deepinfra_client') as client:
            with self.assertRaisesRegex(ValueError,'before provider calls'):
                r.convert_sources(args,run,[5])
            client.assert_not_called()
