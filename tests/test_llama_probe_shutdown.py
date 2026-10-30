"""A completed training result must advance the pipeline even if Python teardown hangs."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

spec=importlib.util.spec_from_file_location('llama_probes',
    Path(__file__).resolve().parents[1]/'phase2/llama_transfer/probes.py')
probes=importlib.util.module_from_spec(spec);spec.loader.exec_module(probes)


class ProbeShutdownTests(unittest.TestCase):
    def test_completed_result_allows_bounded_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            result=Path(directory)/'result.json'
            script=('import json,sys,time; from pathlib import Path; '
                    'Path(sys.argv[1]).write_text(json.dumps({"ok":True,"steps_done":8})); time.sleep(60)')
            start=time.monotonic()
            probes.run_training([sys.executable,'-c',script,str(result)],result,
                                shutdown_timeout=.1,poll_interval=.01)
            self.assertLess(time.monotonic()-start,5)
            self.assertEqual(json.loads(result.read_text())['steps_done'],8)

    def test_exit_without_result_is_not_treated_as_success(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError,'without a completed result'):
                probes.run_training([sys.executable,'-c','pass'],Path(directory)/'missing.json',
                                    shutdown_timeout=.1,poll_interval=.01)


if __name__=='__main__':unittest.main()
