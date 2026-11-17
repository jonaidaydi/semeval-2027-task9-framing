from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from zipfile import ZIP_DEFLATED, ZipFile

from .data import DataFormatError
from .labels import FRAME_LABELS


@dataclass(frozen=True, slots=True)
class PredictionInput:

    document_id: str
    begin: int
    end: int
    text: str

    @property
    def key(self) -> tuple[str, int, int]:
        return self.document_id, self.begin, self.end


def read_participants(
    path: Path | str, articles: Path | str
) -> list[PredictionInput]:
    path, articles = Path(path), Path(articles).resolve()
    documents: dict[str, str] = {}
    rows: list[PredictionInput] = []
    seen: set[tuple[str, int, int]] = set()
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), 1
    ):
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) != 3:
            raise DataFormatError(
                f"Expected exactly 3 participant columns at {path}:{line_number}"
            )
        name = fields[0]

        if not name or Path(name).name != name or "/" in name or "\\" in name:
            raise DataFormatError(f"Invalid article filename: {name!r}")
        try:
            begin, end = int(fields[1]), int(fields[2])
        except ValueError as error:
            raise DataFormatError(f"Invalid offsets at {path}:{line_number}") from error
        if name not in documents:
            document = (articles / name).resolve()
            if document.parent != articles:
                raise DataFormatError(f"Article escapes input directory: {name!r}")


            documents[name] = document.read_bytes().decode("utf-8")
        text = documents[name]
        if not 0 <= begin <= end <= len(text):
            raise DataFormatError(
                f"Span {(begin, end)} outside {name} ({len(text)} characters)"
            )
        row = PredictionInput(name, begin, end, text[begin:end])
        if row.key in seen:
            raise DataFormatError(f"Duplicate participant key: {row.key}")
        seen.add(row.key)
        rows.append(row)
    if not rows:
        raise DataFormatError(f"No participant rows in {path}")
    return rows


def validate_predictions(
    path: Path | str, expected: Sequence[PredictionInput]
) -> dict[str, int]:
    expected_keys = {row.key for row in expected}
    if len(expected_keys) != len(expected):
        raise DataFormatError("Duplicate expected keys")
    seen: set[tuple[str, int, int]] = set()
    no_frame = 0
    positive_labels = 0
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8-sig").splitlines(), 1
    ):
        fields = line.split("\t")
        if len(fields) < 3:
            raise DataFormatError(f"Invalid prediction row {line_number}")
        try:
            key = fields[0], int(fields[1]), int(fields[2])
        except ValueError as error:
            raise DataFormatError(f"Invalid prediction offsets: {line_number}") from error
        labels = fields[3:]

        if labels == [""]:
            labels = []
        if len(set(labels)) != len(labels) or set(labels).difference(FRAME_LABELS):
            raise DataFormatError(f"Invalid prediction labels: {line_number}")
        if key in seen:
            raise DataFormatError(f"Duplicate prediction key: {key}")
        seen.add(key)
        no_frame += not labels
        positive_labels += len(labels)
    if seen != expected_keys:
        raise DataFormatError(
            f"Prediction coverage differs: missing={len(expected_keys-seen)}, "
            f"extra={len(seen-expected_keys)}"
        )
    return {"rows": len(seen), "no_frame_rows": no_frame,
            "positive_label_assignments": positive_labels}


def package_predictions(
    path: Path | str, expected: Sequence[PredictionInput], archive: Path | str
) -> dict[str, int]:
    path, archive = Path(path), Path(archive)
    report = validate_predictions(path, expected)
    if archive.exists():
        raise FileExistsError(f"Preserving existing archive: {archive}")
    with ZipFile(archive, "x", compression=ZIP_DEFLATED) as handle:
        handle.write(path, arcname="subtask_1_best_prediction.txt")
    with ZipFile(archive) as handle:
        if handle.testzip() is not None or handle.namelist() != [
            "subtask_1_best_prediction.txt"
        ]:
            raise DataFormatError("Submission ZIP validation failed")
    return report
