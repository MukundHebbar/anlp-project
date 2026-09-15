import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepositoryHygieneTests(unittest.TestCase):
    def test_local_only_paths_are_ignored(self):
        paths = (".env", ".venv", "wheelhouse", "data/datasets", "local/archive", "logs/")
        for relative in paths:
            with self.subTest(path=relative):
                result = subprocess.run(
                    ["git", "check-ignore", "-q", "--no-index", relative],
                    cwd=ROOT,
                    check=False,
                )
                self.assertEqual(result.returncode, 0)

    def test_colab_notebook_and_scaffold_are_not_in_repository_tree(self):
        self.assertFalse((ROOT / "main.py").exists())
        self.assertFalse((ROOT / "notebooks" / "qwen_explain_colab.ipynb").exists())

    def test_current_solve_evidence_includes_deepseek_and_qwen(self):
        summary = ROOT / "artifacts" / "solve-evaluation-summary.md"
        self.assertTrue(summary.is_file())
        contents = summary.read_text(encoding="utf-8")
        for relative in (
            "deepseek-v4-flash/solve/146/results.json",
            "deepseek-v4-flash/solve/146/report.txt",
            "qwen3-4b/solve/113/results.json",
            "qwen3-4b/solve/113/report.txt",
        ):
            with self.subTest(path=relative):
                self.assertTrue((ROOT / "artifacts" / relative).is_file())
                self.assertIn(relative, contents)

    def test_package_is_importable(self):
        import anlp_project
        from anlp_project.paths import PROJECT_ROOT

        self.assertEqual(PROJECT_ROOT, ROOT)
        self.assertEqual(anlp_project.__version__, "0.1.0")


if __name__ == "__main__":
    unittest.main()
