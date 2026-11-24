import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reproduce_november as runner


class ReproductionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / "run"
        self.output.mkdir()
        (self.root / "results").mkdir()
        self.content = {
            "split.json": b'{\n  "training_documents": ["EN_1.txt"],\n  "threshold": 0.45\n}\n',
            "prediction.txt": b'EN_2.txt\t0\t10\tPolitical\n',
        }
        for name, content in self.content.items():
            (self.output / name).write_bytes(content)
        self.report = {"statistics": {"paragraphs": 1}, "metrics": {"f1": 0.5}, "scorer_sha256": "scorer"}
        reference = {**self.report, "versions": {"python": "3.13.13"},
                     "files_sha256": {name: hashlib.sha256(content).hexdigest()
                                      for name, content in self.content.items()}}
        (self.root / "results/reference.json").write_text(json.dumps(reference), encoding="utf-8")
        self.enterContext(patch.object(runner, "ROOT", self.root))

    def test_windows_and_macos_json_endings_match(self):
        for ending in (b"\n", b"\r\n"):
            with self.subTest(ending=ending), patch.object(runner.platform, "python_version", return_value="3.13.9"):
                (self.output / "split.json").write_bytes(self.content["split.json"].replace(b"\n", ending))
                result = runner.check_reference(self.output, self.report)
                self.assertTrue(result["passed"])
                self.assertEqual(result["python"], "3.13.9")

    def test_changed_split_or_threshold_still_fails(self):
        for old, new in ((b"EN_1.txt", b"EN_3.txt"), (b"0.45", b"0.4500001")):
            with self.subTest(change=new):
                (self.output / "split.json").write_bytes(self.content["split.json"].replace(old, new))
                result = runner.check_reference(self.output, self.report)
                self.assertFalse(result["passed"])
                self.assertFalse(result["files"]["split.json"])

    def test_prediction_files_remain_byte_exact(self):
        original = self.content["prediction.txt"]
        for changed in (original.replace(b"Political", b"Public_opinion"), original.replace(b"\n", b"\r\n")):
            with self.subTest(content=changed):
                (self.output / "prediction.txt").write_bytes(changed)
                self.assertFalse(runner.check_reference(self.output, self.report)["passed"])

    def test_changed_metrics_still_fail(self):
        changed = {**self.report, "metrics": {"f1": 0.500001}}
        result = runner.check_reference(self.output, changed)
        self.assertFalse(result["passed"])
        self.assertFalse(result["report_fields"]["metrics"])

    def test_json_writer_uses_lf_without_changing_string_values(self):
        path = self.output / "written.json"
        expected = {"text": "first\r\nsecond", "threshold": 0.45}
        runner.save_json(path, expected)
        raw = path.read_bytes()
        self.assertNotIn(b"\r\n", raw)
        self.assertEqual(json.loads(raw), expected)


if __name__ == "__main__":
    unittest.main()
