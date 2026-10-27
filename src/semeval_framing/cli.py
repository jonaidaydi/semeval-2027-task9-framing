"""Command-line validation and summary for Subtask 1 data."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from .data import ParagraphExample, load_st1
from .labels import FRAME_LABELS


def _group_name(example: ParagraphExample) -> str:
    return example.source_file.parent.name


def build_summary(examples: list[ParagraphExample]) -> dict[str, object]:
    """Build a JSON-serialisable corpus summary."""

    label_counts: Counter[str] = Counter()
    documents: set[str] = set()
    group_rows: dict[str, int] = defaultdict(int)
    group_documents: dict[str, set[str]] = defaultdict(set)
    no_frame_count = 0
    multilabel_count = 0

    for example in examples:
        documents.add(example.document_id)
        label_counts.update(example.labels)
        group = _group_name(example)
        group_rows[group] += 1
        group_documents[group].add(example.document_id)
        if not example.labels:
            no_frame_count += 1
        if len(example.labels) > 1:
            multilabel_count += 1

    return {
        "documents": len(documents),
        "paragraphs": len(examples),
        "no_frame_paragraphs": no_frame_count,
        "multilabel_paragraphs": multilabel_count,
        "average_labels_per_paragraph": (
            round(sum(label_counts.values()) / len(examples), 4) if examples else 0.0
        ),
        "groups": {
            group: {
                "documents": len(group_documents[group]),
                "paragraphs": group_rows[group],
            }
            for group in sorted(group_rows)
        },
        "labels": {label: label_counts[label] for label in FRAME_LABELS},
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and summarise SemEval Task 9 Subtask 1 data."
    )
    parser.add_argument(
        "data_dir",
        type=Path,
        help="Directory searched recursively for paragraph annotation files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of a compact text summary.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    examples = load_st1(args.data_dir)
    summary = build_summary(examples)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    print(f"Documents:             {summary['documents']}")
    print(f"Paragraphs:            {summary['paragraphs']}")
    print(f"No-frame paragraphs:   {summary['no_frame_paragraphs']}")
    print(f"Multilabel paragraphs: {summary['multilabel_paragraphs']}")
    print(f"Average labels/row:    {summary['average_labels_per_paragraph']}")
    print("\nGroups:")
    for group, values in summary["groups"].items():
        print(
            f"  {group}: {values['documents']} documents, "
            f"{values['paragraphs']} paragraphs"
        )
    print("\nLabels:")
    for label, count in summary["labels"].items():
        print(f"  {label}: {count}")


if __name__ == "__main__":
    main()

