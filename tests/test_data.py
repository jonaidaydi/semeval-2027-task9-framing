from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from semeval_framing.data import DataFormatError, load_st1, read_st1_file


class Subtask1DataTests(unittest.TestCase):
    def test_normalises_no_frame_markers_and_preserves_identifiers(self) -> None:
        content = (
            "doc-1.txt\t0\t10\t-\tFirst paragraph.\n"
            "doc-1.txt\t12\t30\tNo framing\tSecond paragraph.\n"
            "doc-2.txt\t0\t15\tEconomic\tPolitical\tThird paragraph.\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "subtask-1-annotations-with-paragraphs.txt"
            path.write_text(content, encoding="utf-8")
            examples = read_st1_file(path)

        self.assertEqual(examples[0].key, ("doc-1.txt", 0, 10))
        self.assertEqual(examples[0].labels, ())
        self.assertEqual(examples[1].labels, ())
        self.assertEqual(examples[2].labels, ("Economic", "Political"))

    def test_loads_files_recursively(self) -> None:
        content = "doc.txt\t0\t10\tEconomic\tParagraph.\n"

        with tempfile.TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "EN"
                / "subtask-1-annotations-with-paragraphs.txt"
            )
            path.parent.mkdir()
            path.write_text(content, encoding="utf-8")
            examples = load_st1(directory)

        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0].document_id, "doc.txt")

    def test_rejects_unknown_labels(self) -> None:
        content = "doc.txt\t0\t10\tUnknown_frame\tParagraph.\n"

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "subtask-1-annotations-with-paragraphs.txt"
            path.write_text(content, encoding="utf-8")
            with self.assertRaises(DataFormatError):
                read_st1_file(path)

    def test_raw_quotes_do_not_merge_physical_rows(self) -> None:
        content = (
            'doc.txt\t0\t10\t-\tHe said "hello.\n'
            'doc.txt\t12\t20\tEconomic\tA second paragraph.\n'
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "subtask-1-annotations-with-paragraphs.txt"
            path.write_text(content, encoding="utf-8")
            examples = read_st1_file(path)

        self.assertEqual(len(examples), 2)
        self.assertEqual(examples[0].text, 'He said "hello.')
        self.assertEqual(examples[1].labels, ("Economic",))

    def test_rejects_duplicate_document_spans_across_files(self) -> None:
        content = "doc.txt\t0\t10\tEconomic\tParagraph.\n"

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for language in ("EN", "PT"):
                path = root / language / "subtask-1-annotations-with-paragraphs.txt"
                path.parent.mkdir()
                path.write_text(content, encoding="utf-8")

            with self.assertRaises(DataFormatError):
                load_st1(root)


if __name__ == "__main__":
    unittest.main()
