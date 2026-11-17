from pathlib import Path
import tempfile
import unittest

import numpy as np

from semeval_framing.baseline_tfidf import official_style_metrics, write_predictions
from semeval_framing.development import PredictionInput, validate_predictions
from semeval_framing.labels import FRAME_LABELS
from semeval_framing.november_experiment import decode


class BaselineTests(unittest.TestCase):
    def test_missed_frame_also_creates_false_positive_none(self):
        scores = official_style_metrics([("Public_opinion",), ()], [(), ()])
        self.assertAlmostEqual(scores["micro_f1"], 0.5)
        self.assertAlmostEqual(scores["macro_f1"], (13 + 2 / 3) / 15)

    def test_one_global_threshold_allows_empty_and_multiple_labels(self):
        scores = np.zeros((3, len(FRAME_LABELS)))
        scores[1, :2] = [0.45, 0.46]
        scores[2, 0] = 0.449999
        self.assertEqual(decode(scores, 0.45), [(), FRAME_LABELS[:2], ()])

    def test_prediction_export_preserves_empty_rows_and_rejects_unknown_labels(self):
        rows = [PredictionInput("a.txt", 0, 0, ""), PredictionInput("a.txt", 1, 2, "x")]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "predictions.tsv"
            write_predictions(path, rows, [(), ("Political",)])
            self.assertEqual(validate_predictions(path, rows)["no_frame_rows"], 1)
            self.assertEqual(path.read_bytes(), b"a.txt\t0\t0\na.txt\t1\t2\tPolitical\n")
            with self.assertRaises(ValueError):
                write_predictions(path, rows, [(), ("Unknown",)])
            with self.assertRaises(ValueError):
                write_predictions(path, rows, [()])


if __name__ == "__main__":
    unittest.main()
