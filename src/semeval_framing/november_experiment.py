from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import time
import unicodedata
import warnings

import joblib
import numpy as np
import sklearn
from sklearn.metrics import precision_recall_fscore_support
from sklearn.model_selection import GroupKFold, GroupShuffleSplit

from .baseline_tfidf import (
    build_label_encoder,
    build_pipeline,
    official_style_metrics,
    write_predictions,
)
from .data import DataFormatError, NO_FRAME_MARKERS
from .development import PredictionInput, package_predictions, read_participants
from .labels import FRAME_LABELS


@dataclass(frozen=True)
class GoldParagraph:
    document_id: str
    begin: int
    end: int
    text: str
    labels: tuple[str, ...]

    @property
    def key(self):
        return self.document_id, self.begin, self.end


def normalise(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )


def read_gold(source):
    path = Path(source["annotations"])
    auxiliary = source.get("auxiliary_text_gold", False)
    if "participant" in path.name.lower() and not auxiliary:
        raise DataFormatError("Participant files are not training gold")
    with_paragraphs = source.get("with_paragraphs", False)
    article_root = Path(source["articles"]).resolve()
    docs = {}
    rows = []
    seen = set()
    removed = 0
    text_offset_mismatches = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split("\t")
        minimum = 4 if with_paragraphs else 3
        if len(fields) < minimum:
            raise DataFormatError(f"Invalid gold row at {path}:{number}")
        name = fields[0]
        if name.removesuffix(".txt") == "EN_M_TRAIN_4":
            removed += 1
            continue
        if Path(name).name != name or "/" in name or "\\" in name:
            raise DataFormatError(f"Invalid document ID at {path}:{number}")
        begin, end = int(fields[1]), int(fields[2])
        if name not in docs:
            doc = (article_root / name).resolve()
            if doc.parent != article_root:
                raise DataFormatError(f"Article escapes source directory: {name}")
            docs[name] = doc.read_bytes().decode("utf-8")
        if not 0 <= begin <= end <= len(docs[name]):
            raise DataFormatError(f"Invalid gold span at {path}:{number}")
        labels = fields[3:-1] if with_paragraphs else fields[3:]
        labels = {label.strip() for label in labels
                  if label.strip().casefold() not in NO_FRAME_MARKERS}
        unknown = labels.difference(FRAME_LABELS)
        if unknown:
            raise DataFormatError(f"Unknown labels at {path}:{number}: {unknown}")
        text = docs[name][begin:end]
        if with_paragraphs and normalise(fields[-1]) != normalise(text):
            if not source.get("use_provided_paragraph_text", False):
                raise DataFormatError(f"Paragraph and raw offsets disagree at {path}:{number}")
            text_offset_mismatches.append([name, begin, end])
        if with_paragraphs:
            text = fields[-1]
        row = GoldParagraph(name, begin, end, text,
                            tuple(label for label in FRAME_LABELS if label in labels))
        if row.key in seen:
            raise DataFormatError(f"Duplicate gold key: {row.key}")
        seen.add(row.key)
        rows.append(row)
    if not rows or not any(row.labels for row in rows):
        raise DataFormatError(f"Source has no positive gold labels: {path}")
    return rows, {"annotations": str(path), "sha256": sha256(path),
                  "rows": len(rows), "documents": len(docs),
                  "removed_EN_M_TRAIN_4_rows": removed,
                  "text_offset_mismatches": text_offset_mismatches,
                  "training_text": "provided paragraph column" if with_paragraphs else "raw article span",
                  "article_sha256": {name: sha256(article_root / name) for name in sorted(docs)}}


def document_groups(rows):
    parents = {row.document_id: row.document_id for row in rows}

    def root(doc):
        while parents[doc] != doc:
            parents[doc] = parents[parents[doc]]
            doc = parents[doc]
        return doc

    first_by_text = {}
    for row in rows:
        text = normalise(row.text)
        if not text:
            continue
        previous = first_by_text.setdefault(text, row.document_id)
        a, b = root(previous), root(row.document_id)
        parents[max(a, b)] = min(a, b)
    return {doc: root(doc) for doc in sorted(parents)}


def assert_disjoint(train, validation, groups):
    if {groups[r.document_id] for r in train} & {groups[r.document_id] for r in validation}:
        raise DataFormatError("Document/duplicate group leakage")
    a = {normalise(r.text) for r in train if normalise(r.text)}
    b = {normalise(r.text) for r in validation if normalise(r.text)}
    if a & b:
        raise DataFormatError("Identical paragraphs cross the split")


def fit(rows, balanced=False):
    encoder = build_label_encoder()
    y = encoder.transform([row.labels for row in rows])
    model = build_pipeline(random_state=42)
    if balanced:
        model.set_params(classifier__estimator__class_weight="balanced")
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r"Label .* is present in all training examples\.")
        model.fit([row.text for row in rows], y)
    return model


def decode(probabilities, threshold):
    return [tuple(label for label, p in zip(FRAME_LABELS, row) if p >= threshold)
            for row in probabilities]


def tune(rows, groups, folds=3):
    group_ids = [groups[row.document_id] for row in rows]
    n_folds = min(folds, len(set(group_ids)))
    if n_folds < 2:
        raise DataFormatError("Not enough independent training groups")
    splits = list(GroupKFold(n_splits=n_folds).split(rows, groups=group_ids))
    grid = []
    fold_manifest = []
    thresholds = [round(x / 100, 2) for x in range(10, 56, 5)]
    for balanced in (False, True):
        probabilities = np.zeros((len(rows), len(FRAME_LABELS)))
        for fold, (tr, va) in enumerate(splits):
            training, validation = [rows[i] for i in tr], [rows[i] for i in va]
            assert_disjoint(training, validation, groups)
            model = fit(training, balanced)
            probabilities[va] = model.predict_proba([row.text for row in validation])
            if not balanced:
                fold_manifest.append({
                    "fold": fold,
                    "training_documents": sorted({r.document_id for r in training}),
                    "validation_documents": sorted({r.document_id for r in validation}),
                })
        for threshold in thresholds:
            metrics = official_style_metrics([r.labels for r in rows], decode(probabilities, threshold))
            grid.append({"balanced": balanced, "threshold": threshold, **metrics})

    selected = max(grid, key=lambda x: (x["micro_f1"], x["macro_f1"], x["threshold"]))
    return {"selected": selected, "grid": grid, "folds": fold_manifest}


def statistics(rows):
    labels = Counter(label for row in rows for label in row.labels)
    return {"documents": len({r.document_id for r in rows}), "paragraphs": len(rows),
            "no_frame": sum(not r.labels for r in rows),
            "empty_text": sum(not r.text.strip() for r in rows),
            "label_counts": {label: labels[label] for label in FRAME_LABELS}}


def load_scorer(path):
    spec = importlib.util.spec_from_file_location("official_task9_scorer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def official_check(scorer, predictions, gold=None):
    pred = scorer._read_csv_input_file(str(predictions))
    target = scorer._read_csv_input_file(str(gold)) if gold else None
    if not scorer.correct_format(pred, target, list(FRAME_LABELS)):
        raise DataFormatError(f"Official scorer rejected {predictions}")
    if target is not None:
        macro, micro = scorer.evaluate(pred, target, list(FRAME_LABELS))
        return {"micro_f1": float(micro), "macro_f1": float(macro)}
    return {"format_valid": True, "gold_available": False}


def run(config_path):
    started = time.monotonic()
    config = json.loads(Path(config_path).read_text(encoding="utf-8-sig"))
    output = Path(config["output"])
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    main, main_meta = read_gold(config["main"])
    auxiliary, aux_meta = [], []
    for source in config.get("auxiliary", []):
        rows, meta = read_gold(source)
        auxiliary.extend(rows)
        aux_meta.append(meta)
    all_by_key = {row.key: row for row in main}
    duplicated_aux = 0
    unique_aux = []
    for row in auxiliary:
        previous = all_by_key.get(row.key)
        if previous is not None:
            if previous != row:
                raise DataFormatError(f"Conflicting auxiliary duplicate {row.key}")
            duplicated_aux += 1
        else:
            unique_aux.append(row)
            all_by_key[row.key] = row
    auxiliary = unique_aux
    all_rows = sorted(all_by_key.values(), key=lambda r: r.key)
    groups = document_groups(all_rows)
    main_docs = sorted({r.document_id for r in main})
    train_ix, val_ix = next(GroupShuffleSplit(
        n_splits=1, test_size=0.2, random_state=42
    ).split(main_docs, groups=[groups[doc] for doc in main_docs]))
    val_docs = {main_docs[i] for i in val_ix}
    val_groups = {groups[doc] for doc in val_docs}
    validation = sorted([r for r in main if r.document_id in val_docs], key=lambda r: r.key)
    core_train = [r for r in main if r.document_id not in val_docs]
    training = sorted([r for r in all_rows if groups[r.document_id] not in val_groups], key=lambda r: r.key)
    assert_disjoint(training, validation, groups)
    save_json(output / "config.json", config)
    save_json(output / "split.json", {
        "seed": 42, "outer_validation_fraction": 0.2,
        "grouping": "documents joined by identical NFKC/casefold/whitespace-normalized nonempty paragraphs",
        "near_duplicate_detection": "not performed",
        "training_documents": sorted({r.document_id for r in training}),
        "validation_documents": sorted(val_docs), "document_groups": groups,
    })
    print("Data loaded:", statistics(training), flush=True)
    scorer = load_scorer(config["scorer"])
    gold_path = output / "validation_gold.tsv"
    write_predictions(gold_path, validation, [row.labels for row in validation])
    metrics = {}

    def evaluate(name, predictions, parameters):
        path = output / f"{name}_validation.tsv"
        write_predictions(path, validation, predictions)
        local = official_style_metrics([r.labels for r in validation], predictions)
        official = official_check(scorer, path, gold_path)
        if any(abs(local[k] - official[k]) > 1e-12 for k in local):
            raise RuntimeError("Local and official scorer disagree")
        metrics[name] = {**official, "parameters": parameters,
                         "no_frame_predictions": sum(not p for p in predictions)}
        print(name, metrics[name], flush=True)
        return predictions

    evaluate("no_frame", [() for _ in validation], {"rule": "always no frame"})
    core_model = fit(core_train)
    evaluate("tfidf_core_050", decode(core_model.predict_proba([r.text for r in validation]), 0.5),
             {"balanced": False, "threshold": 0.5, "training": "main only"})
    model = fit(training)
    evaluate("tfidf_all_050", decode(model.predict_proba([r.text for r in validation]), 0.5),
             {"balanced": False, "threshold": 0.5, "training": "main plus auxiliary"})
    print("Core-only nested tuning started", flush=True)
    core_tuning = tune(core_train, groups)
    save_json(output / "core_inner_tuning.json", core_tuning)
    core_choice = core_tuning["selected"]
    core_tuned_model = fit(core_train, core_choice["balanced"])
    evaluate("tfidf_core_tuned", decode(core_tuned_model.predict_proba([r.text for r in validation]), core_choice["threshold"]),
             {"balanced": core_choice["balanced"], "threshold": core_choice["threshold"],
              "training": "main only", "selection": "3-fold OOF on outer training only"})
    print("Training-only nested tuning started", flush=True)
    tuning = tune(training, groups)
    save_json(output / "inner_tuning.json", tuning)
    selected = tuning["selected"]
    model = fit(training, selected["balanced"])
    tuned = evaluate("tfidf_tuned", decode(model.predict_proba([r.text for r in validation]), selected["threshold"]),
                     {"balanced": selected["balanced"], "threshold": selected["threshold"],
                      "training": "main plus auxiliary", "selection": "3-fold OOF on outer training only"})
    encoder = build_label_encoder()
    precision, recall, f1, support = precision_recall_fscore_support(
        encoder.transform([r.labels for r in validation]), encoder.transform(tuned),
        average=None, zero_division=0)
    per_label = {label: {"precision": float(p), "recall": float(r), "f1": float(f), "support": int(s)}
                 for label, p, r, f, s in zip(FRAME_LABELS, precision, recall, f1, support)}
    save_json(output / "per_label.json", per_label)
    dev = read_participants(config["development"]["participants"], config["development"]["articles"])
    if {r.document_id for r in all_rows} & {r.document_id for r in dev}:
        raise DataFormatError("Training and development document IDs overlap")
    print("Full-training OOF tuning for development predictions started", flush=True)
    final_tuning = tune(all_rows, groups)
    save_json(output / "full_training_tuning.json", final_tuning)
    final_choice = final_tuning["selected"]
    final_model = fit(all_rows, final_choice["balanced"])
    joblib.dump({"model": final_model, "threshold": final_choice["threshold"],
                 "labels": FRAME_LABELS}, output / "model.joblib")
    predictions = decode(final_model.predict_proba([r.text for r in dev]), final_choice["threshold"])
    dev_path = output / "subtask_1_best_prediction.txt"
    write_predictions(dev_path, dev, predictions)
    dev_format = official_check(scorer, dev_path)
    package = package_predictions(dev_path, dev, output / "submission_EN_dev.zip")
    train_texts = {normalise(r.text) for r in all_rows if len(normalise(r.text)) >= 80}
    report = {
        "status": "local_completed_not_submitted", "release": config["release"],
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.monotonic() - started,
        "sources": {"main": main_meta, "auxiliary": aux_meta},
        "statistics": {"main": statistics(main), "auxiliary": statistics(auxiliary),
                       "core_training": statistics(core_train),
                       "outer_training": statistics(training), "outer_validation": statistics(validation)},
        "duplicate_auxiliary_keys_skipped": duplicated_aux,
        "auxiliary_rows_excluded_for_holdout": len(all_rows)-len(training)-len(validation),
        "metrics": metrics, "core_inner_selection": core_choice,
        "inner_selection": selected, "final_selection": final_choice,
        "model": {"features": len(final_model.named_steps["tfidf"].vocabulary_),
                  "ngram_range": [1, 1], "C": 1.0, "min_df": 1,
                  "max_features": 30000, "max_iter": 1000,
                  "model_sha256": sha256(output / "model.joblib")},
        "development": {"documents": len({r.document_id for r in dev}), "paragraphs": len(dev),
                        "empty_text": sum(not r.text.strip() for r in dev),
                        "gold_available": False, "score": None, "submitted": False,
                        "paragraphs_matching_training_at_least_80_chars": sum(normalise(r.text) in train_texts for r in dev),
                        "input_sha256": sha256(config["development"]["participants"]),
                        "article_sha256": {name: sha256(Path(config["development"]["articles"])/name)
                                           for name in sorted({r.document_id for r in dev})},
                        "predictions_sha256": sha256(dev_path), "zip_sha256": sha256(output / "submission_EN_dev.zip"),
                        **dev_format, **package},
        "scorer_sha256": sha256(config["scorer"]),
        "code_sha256": {name: sha256(Path(__file__).with_name(name)) for name in
                        ("november_experiment.py", "development.py", "baseline_tfidf.py", "labels.py")},
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "scikit_learn": sklearn.__version__},
    }
    save_json(output / "report.json", report)
    print("Completed locally:", output, flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
