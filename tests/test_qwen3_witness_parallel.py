import json
import tempfile
import unittest
from pathlib import Path

from anlp_project.qwen3_witness_parallel import merge_witness_results, shard_witness_input


class Qwen3WitnessParallelTests(unittest.TestCase):
    def test_sharding_is_deterministic_and_balanced(self):
        with tempfile.TemporaryDirectory() as directory_name:
            root = Path(directory_name)
            source = root / "input.json"
            source.write_text(json.dumps({"items": [{"source_index": i} for i in range(11)]}), encoding="utf-8")
            indices = shard_witness_input(source, root / "shards", 4)
            self.assertEqual(indices, list(range(11)))
            self.assertEqual(
                [len(json.loads((root / "shards" / f"shard-{i:02d}.json").read_text())["items"]) for i in range(4)],
                [3, 3, 3, 2],
            )

    def test_merge_rejects_missing_or_duplicate_indices(self):
        with tempfile.TemporaryDirectory() as directory_name:
            root = Path(directory_name)
            source = root / "input.json"
            source.write_text(json.dumps({"items": [{"source_index": 1}, {"source_index": 2}]}), encoding="utf-8")
            results = root / "results"
            results.mkdir()
            (results / "shard-0-results.json").write_text(json.dumps({"results": [{"source_index": 1}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                merge_witness_results(source, results, root / "artifact")
            (results / "shard-1-results.json").write_text(json.dumps({"results": [{"source_index": 1}, {"source_index": 2}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                merge_witness_results(source, results, root / "artifact")

    def test_merge_writes_report_and_preserves_order(self):
        with tempfile.TemporaryDirectory() as directory_name:
            root = Path(directory_name)
            source = root / "input.json"
            source.write_text(json.dumps({"items": [{"source_index": 2}, {"source_index": 5}]}), encoding="utf-8")
            results = root / "results"
            results.mkdir()
            (results / "shard-0-results.json").write_text(json.dumps({"results": [{"source_index": 5, "status": "completed", "format_valid": True}]}), encoding="utf-8")
            (results / "shard-1-results.json").write_text(json.dumps({"results": [{"source_index": 2, "status": "completed", "format_valid": False}]}), encoding="utf-8")
            merged = merge_witness_results(source, results, root / "artifact")
            self.assertEqual([item["source_index"] for item in merged["results"]], [2, 5])
            self.assertEqual(merged["metadata"]["batch_size"], 5)
            self.assertFalse(merged["metadata"]["enable_thinking"])
            self.assertTrue((root / "artifact" / "results.json").exists())
            self.assertIn("Format-valid responses: 1/2", (root / "artifact" / "report.txt").read_text())


if __name__ == "__main__":
    unittest.main()
