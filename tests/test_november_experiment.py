import tempfile
import unittest
from pathlib import Path

from semeval_framing.data import DataFormatError
from semeval_framing.november_experiment import (
    GoldParagraph,
    assert_disjoint,
    document_groups,
    read_gold,
)


class NovemberDataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "article.txt").write_bytes("\ufeffTitle\r\n\r\nBody".encode("utf-8"))
        self.path = self.root / "gold.txt"
        self.path.write_text("article.txt\t0\t6\tPolitical\narticle.txt\t10\t14\t\n", encoding="utf-8")

    def source(self, **kwargs):
        return {"annotations": str(self.path), "articles": str(self.root), **kwargs}

    def test_gold_uses_original_character_offsets_and_retains_no_frame(self):
        rows, metadata = read_gold(self.source())
        self.assertEqual(rows[1].text, "Body")
        self.assertEqual(rows[1].labels, ())
        self.assertEqual(metadata["rows"], 2)

    def test_participant_gold_requires_explicit_auxiliary_role_and_labels(self):
        self.path = self.root / "subtask-1-participant.txt"
        self.path.write_text("article.txt\t0\t6\tPolitical\n", encoding="utf-8")
        with self.assertRaises(DataFormatError):
            read_gold(self.source())
        self.assertEqual(len(read_gold(self.source(auxiliary_text_gold=True))[0]), 1)
        self.path.write_text("article.txt\t0\t6\n", encoding="utf-8")
        with self.assertRaises(DataFormatError):
            read_gold(self.source(auxiliary_text_gold=True))

    def test_organizer_removed_document_is_not_read_or_used(self):
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write("EN_M_TRAIN_4.txt\t0\t6\tEconomic\n")
        rows, metadata = read_gold(self.source())
        self.assertEqual(len(rows), 2)
        self.assertEqual(metadata["removed_EN_M_TRAIN_4_rows"], 1)

    def test_text_offset_disagreement_is_explicitly_audited(self):
        self.path.write_text("article.txt\t0\t6\tPolitical\tCorrected title\n", encoding="utf-8")
        with self.assertRaises(DataFormatError):
            read_gold(self.source(with_paragraphs=True))
        rows, metadata = read_gold(self.source(with_paragraphs=True, use_provided_paragraph_text=True))
        self.assertEqual(rows[0].text, "Corrected title")
        self.assertEqual(metadata["text_offset_mismatches"], [["article.txt", 0, 6]])

    def test_duplicate_document_groups_are_transitive_and_cannot_cross_split(self):
        rows = [
            GoldParagraph("a", 0, 5, "Alpha", ()),
            GoldParagraph("b", 0, 5, "  ALPHA ", ()),
            GoldParagraph("b", 6, 10, "Beta", ()),
            GoldParagraph("c", 0, 4, "Beta", ()),
            GoldParagraph("d", 0, 0, "", ()),
            GoldParagraph("e", 0, 0, "", ()),
        ]
        groups = document_groups(rows)
        self.assertEqual(groups["a"], groups["c"])
        self.assertNotEqual(groups["d"], groups["e"])
        with self.assertRaises(DataFormatError):
            assert_disjoint([rows[0]], [rows[3]], groups)
        assert_disjoint(rows[:4], rows[4:], groups)


if __name__ == "__main__":
    unittest.main()
