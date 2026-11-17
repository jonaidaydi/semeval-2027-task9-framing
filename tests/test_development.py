import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from semeval_framing.data import DataFormatError
from semeval_framing.development import (
    package_predictions,
    read_participants,
    validate_predictions,
)


class DevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.article = self.root / "article.txt"
        self.article.write_bytes("Überschrift\r\n\r\nSecond paragraph.\r\n".encode("utf-8"))
        self.inputs = self.root / "subtask-1-participant.txt"
        self.inputs.write_text("article.txt\t15\t32\narticle.txt\t32\t32\n", encoding="utf-8")

    def test_character_offsets_and_empty_paragraph_preserved_without_gold(self):
        rows = read_participants(self.inputs, self.root)
        self.assertEqual(rows[0].text, "Second paragraph.")
        self.assertEqual(rows[0].key, ("article.txt", 15, 32))
        self.assertEqual(rows[1].text, "")
        self.assertFalse(hasattr(rows[0], "labels"))

    def test_duplicate_or_out_of_bounds_input_is_rejected(self):
        for content in (
            "article.txt\t0\t1\narticle.txt\t0\t1\n",
            "article.txt\t0\t99999\n",
            "../article.txt\t0\t1\n",
            "article.txt\t0\t1\tEconomic\n",
        ):
            with self.subTest(content=content):
                self.inputs.write_text(content, encoding="utf-8")
                with self.assertRaises(DataFormatError):
                    read_participants(self.inputs, self.root)

    def test_article_bom_counts_as_an_original_character(self):
        self.article.write_bytes("\ufeffTitle\r\n\r\nBody".encode("utf-8"))
        self.inputs.write_text("article.txt\t10\t14\n", encoding="utf-8")
        self.assertEqual(read_participants(self.inputs, self.root)[0].text, "Body")

    def test_submission_coverage_and_root_layout(self):
        rows = read_participants(self.inputs, self.root)
        predictions = self.root / "predictions.tsv"
        predictions.write_text(
            "article.txt\t15\t32\tEconomic\narticle.txt\t32\t32\n", encoding="utf-8"
        )
        archive = self.root / "submission.zip"
        report = package_predictions(predictions, rows, archive)
        self.assertEqual(report["rows"], 2)
        self.assertEqual(report["no_frame_rows"], 1)
        with ZipFile(archive) as handle:
            self.assertEqual(handle.namelist(), ["subtask_1_best_prediction.txt"])
            self.assertEqual(handle.read(handle.namelist()[0]), predictions.read_bytes())
        with self.assertRaises(FileExistsError):
            package_predictions(predictions, rows, archive)
        for content in (
            "article.txt\t15\t32\tEconomic\n",
            "article.txt\t15\t32\tUnknown\narticle.txt\t32\t32\n",
            "article.txt\t15\t32\narticle.txt\t15\t32\n",
        ):
            predictions.write_text(content, encoding="utf-8")
            with self.assertRaises(DataFormatError):
                validate_predictions(predictions, rows)


if __name__ == "__main__":
    unittest.main()
