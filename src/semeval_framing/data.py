"""Readers for the official Subtask 1 paragraph annotation format."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .labels import FRAME_LABELS

ST1_FILENAME = "subtask-1-annotations-with-paragraphs.txt"
NO_FRAME_MARKERS = frozenset({"", "-", "no framing", "none"})


class DataFormatError(ValueError):
    """Raised when a task data row violates the expected format."""


@dataclass(frozen=True, slots=True)
class ParagraphExample:
    """One paragraph-level multi-label example."""

    document_id: str
    begin: int
    end: int
    labels: tuple[str, ...]
    text: str
    source_file: Path
    line_number: int

    @property
    def key(self) -> tuple[str, int, int]:
        """Return the identity used by the official scorer."""

        return (self.document_id, self.begin, self.end)


def find_st1_files(root: Path | str) -> list[Path]:
    """Find all paragraph-enriched Subtask 1 annotation files below *root*."""

    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(f"Data directory does not exist: {root}")

    files = sorted(root.rglob(ST1_FILENAME))
    if not files:
        raise FileNotFoundError(
            f"No {ST1_FILENAME!r} files found recursively below: {root}"
        )
    return files


def _normalise_labels(
    raw_labels: list[str],
    *,
    path: Path,
    line_number: int,
    strict_labels: bool,
) -> tuple[str, ...]:
    labels: list[str] = []
    known_labels = set(FRAME_LABELS)

    for raw_label in raw_labels:
        label = raw_label.strip()
        if label.casefold() in NO_FRAME_MARKERS:
            continue
        if strict_labels and label not in known_labels:
            raise DataFormatError(
                f"Unknown label {label!r} in {path} at line {line_number}"
            )
        if label not in labels:
            labels.append(label)

    return tuple(labels)


def read_st1_file(
    path: Path | str,
    *,
    strict_labels: bool = True,
) -> list[ParagraphExample]:
    """Read one paragraph-enriched Subtask 1 annotation file.

    Expected columns are document ID, begin offset, end offset, zero or more
    frame labels, and the paragraph text as the final column.
    """

    path = Path(path)
    examples: list[ParagraphExample] = []

    with path.open("r", encoding="utf-8-sig", errors="strict", newline="") as handle:
        # The official files are TSV-like, but article text contains raw,
        # unescaped quote characters. csv.reader would interpret those quotes
        # and can accidentally merge multiple physical lines into one record.
        for line_number, line in enumerate(handle, start=1):
            row = line.rstrip("\r\n").split("\t")
            if not row or all(not cell.strip() for cell in row):
                continue
            if len(row) < 4:
                raise DataFormatError(
                    f"Expected at least 4 columns in {path} at line "
                    f"{line_number}, found {len(row)}"
                )

            document_id = row[0].strip()
            if not document_id:
                raise DataFormatError(
                    f"Missing document ID in {path} at line {line_number}"
                )

            try:
                begin = int(row[1])
                end = int(row[2])
            except ValueError as error:
                raise DataFormatError(
                    f"Invalid offsets in {path} at line {line_number}: "
                    f"{row[1:3]!r}"
                ) from error

            if begin < 0 or end < begin:
                raise DataFormatError(
                    f"Invalid span ({begin}, {end}) in {path} at line {line_number}"
                )

            text = row[-1].strip()
            if not text:
                raise DataFormatError(
                    f"Missing paragraph text in {path} at line {line_number}"
                )

            labels = _normalise_labels(
                row[3:-1],
                path=path,
                line_number=line_number,
                strict_labels=strict_labels,
            )
            examples.append(
                ParagraphExample(
                    document_id=document_id,
                    begin=begin,
                    end=end,
                    labels=labels,
                    text=text,
                    source_file=path,
                    line_number=line_number,
                )
            )

    return examples


def load_st1(
    root: Path | str,
    *,
    strict_labels: bool = True,
) -> list[ParagraphExample]:
    """Load every Subtask 1 annotation file found recursively below *root*."""

    examples: list[ParagraphExample] = []
    seen_keys: dict[tuple[str, int, int], Path] = {}

    for path in find_st1_files(root):
        for example in read_st1_file(path, strict_labels=strict_labels):
            previous_path = seen_keys.get(example.key)
            if previous_path is not None:
                raise DataFormatError(
                    f"Duplicate example {example.key!r} in {previous_path} and "
                    f"{example.source_file}"
                )
            seen_keys[example.key] = example.source_file
            examples.append(example)

    return examples
