import csv
from pathlib import Path
from typing import Protocol, Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MultiLabelBinarizer

from .labels import FRAME_LABELS

NONE_LABEL = "None"


class ParagraphSpan(Protocol):
    document_id: str
    begin: int
    end: int


def build_label_encoder() -> MultiLabelBinarizer:

    encoder = MultiLabelBinarizer(classes=FRAME_LABELS)
    encoder.fit([FRAME_LABELS])
    return encoder


def build_pipeline(*, random_state: int = 42) -> Pipeline:

    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=(1, 1),
                    min_df=1,
                    max_features=30_000,
                ),
            ),
            (
                "classifier",
                OneVsRestClassifier(
                    LogisticRegression(
                        C=1.0,
                        max_iter=1_000,
                        random_state=random_state,
                    )
                ),
            ),
        ]
    )


def official_style_metrics(
    gold: Sequence[tuple[str, ...]],
    predicted: Sequence[tuple[str, ...]],
) -> dict[str, float]:

    if len(gold) != len(predicted):
        raise ValueError("Gold and prediction lengths differ")

    def with_none(rows: Sequence[tuple[str, ...]]) -> list[tuple[str, ...]]:
        return [row if row else (NONE_LABEL,) for row in rows]

    encoder = MultiLabelBinarizer(classes=(*FRAME_LABELS, NONE_LABEL))
    encoder.fit([(*FRAME_LABELS, NONE_LABEL)])
    gold_matrix = encoder.transform(with_none(gold))
    predicted_matrix = encoder.transform(with_none(predicted))
    return {
        "micro_f1": float(
            f1_score(
                gold_matrix,
                predicted_matrix,
                average="micro",
                zero_division=1,
            )
        ),
        "macro_f1": float(
            f1_score(
                gold_matrix,
                predicted_matrix,
                average="macro",
                zero_division=1,
            )
        ),
    }


def write_predictions(
    path: Path | str,
    examples: Sequence[ParagraphSpan],
    predicted: Sequence[tuple[str, ...]],
) -> None:

    if len(examples) != len(predicted):
        raise ValueError("Example and prediction lengths differ")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        for example, labels in zip(examples, predicted, strict=True):
            unknown = set(labels).difference(FRAME_LABELS)
            if unknown:
                raise ValueError(f"Cannot export unknown labels: {sorted(unknown)}")
            writer.writerow(
                [example.document_id, example.begin, example.end, *labels]
            )
