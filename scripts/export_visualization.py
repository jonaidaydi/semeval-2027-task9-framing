import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from semeval_framing.november_experiment import read_gold, fit, decode
from semeval_framing.labels import FRAME_LABELS


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_labels(path):
    rows = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        fields = line.split("\t")
        rows[(fields[0], int(fields[1]), int(fields[2]))] = set(fields[3:]) - {""}
    return rows


def build_graph_data(reference):
    config = json.loads((reference / "config.json").read_text(encoding="utf-8"))
    report = json.loads((reference / "report.json").read_text(encoding="utf-8"))
    split = json.loads((reference / "split.json").read_text(encoding="utf-8"))

    by_key = {}
    for source in [config["main"], *config["auxiliary"]]:
        rows, _ = read_gold(source)
        for row in rows:
            if row.key in by_key and by_key[row.key] != row:
                raise ValueError(f"Conflicting input: {row.key}")
            by_key[row.key] = row
    training_docs = set(split["training_documents"])
    validation_docs = set(split["validation_documents"])
    assert not training_docs & validation_docs
    training = sorted([r for r in by_key.values() if r.document_id in training_docs], key=lambda r: r.key)
    validation = sorted([r for r in by_key.values() if r.document_id in validation_docs], key=lambda r: r.key)
    assert len(training) == 1038 and len(validation) == 222
    choice = report["inner_selection"]
    model = fit(training, balanced=choice["balanced"])
    probabilities = model.predict_proba([r.text for r in validation])
    predicted = decode(probabilities, choice["threshold"])
    reference_predictions = read_labels(reference / "tfidf_tuned_validation.tsv")
    assert set(reference_predictions) == {r.key for r in validation}
    assert all(set(pred) == reference_predictions[row.key] for row, pred in zip(validation, predicted))
    tfidf = model.named_steps["tfidf"]
    classifier = model.named_steps["classifier"]
    vocabulary = tfidf.get_feature_names_out()
    case_data = []
    cases = [("2", "EN_M_TRAIN_1.txt", 1799, 2093),
             ("0", "EN_M_TRAIN_47.txt", 3452, 3600),
             ("1", "EN_M_TRAIN_1.txt", 2295, 2571),
             ("3", "EN_M_TRAIN_47.txt", 3604, 3715)]
    for index, document, begin, end in cases:
        key = document, begin, end
        row = by_key[key]
        assert row.document_id in validation_docs
        vector = tfidf.transform([row.text])
        indices = vector.indices
        values = vector.data
        p = model.predict_proba([row.text])[0]
        details = []
        for column, (label, estimator) in enumerate(zip(FRAME_LABELS, classifier.estimators_)):
            if not hasattr(estimator, "coef_"):
                raise ValueError(f"Constant estimator requires a separate visualization: {label}")
            weights = estimator.coef_[0, indices]
            contributions = values * weights
            bias = float(estimator.intercept_[0])
            logit = bias + float(contributions.sum())
            score = float(1 / (1 + np.exp(-logit)))
            assert abs(score - p[column]) < 1e-12
            terms = [dict(word=str(vocabulary[i]), tfidf=float(x), weight=float(w), contribution=float(c))
                     for i, x, w, c in zip(indices, values, weights, contributions)]
            details.append(dict(label=label, probability=score, bias=bias, logit=logit, terms=terms))
        case_data.append(dict(id=str(index), document=row.document_id,
                              begin=row.begin, end=row.end, text=row.text,
                              gold=list(row.labels), predicted=list(decode(p.reshape(1, -1), choice["threshold"])[0]),
                              frames=details))
    data = dict(threshold=choice["threshold"], labels=list(FRAME_LABELS), cases=case_data,
                provenance=dict(training_paragraphs=len(training), validation_paragraphs=len(validation),
                                matched_holdout_predictions=len(validation), reference=str(reference.relative_to(ROOT)),
                                split_sha256=hashlib.sha256((reference / "split.json").read_bytes()).hexdigest(),
                                meaning="TF-IDF value times logistic-regression coefficient contributes to the logit, not directly to probability.",
                                transformer="Schematic only. No transformer weights or attention values were used."))
    return data


def validate(data):
    if data.get("threshold") != 0.45 or len(data.get("labels", [])) != 14:
        raise ValueError("This November visualization expects 14 labels and threshold 0.45")
    if data.get("provenance", {}).get("matched_holdout_predictions") != 222:
        raise ValueError("The reconstruction must match all 222 holdout predictions")
    if len(data.get("cases", [])) != 4 or {c["id"] for c in data["cases"]} != {"0", "1", "2", "3"}:
        raise ValueError("All four documented teaching examples are required")
    for case in data["cases"]:
        if [frame["label"] for frame in case["frames"]] != data["labels"]:
            raise ValueError("Frame order does not match the label mapping")
        if any(not 0 <= frame["probability"] <= 1 for frame in case["frames"]):
            raise ValueError("Invalid model probability")
        decoded = [frame["label"] for frame in case["frames"] if frame["probability"] >= data["threshold"]]
        if decoded != case["predicted"]:
            raise ValueError("Saved predictions disagree with probabilities and threshold")


def add_evaluation(data):
    reference = ROOT / data["provenance"]["reference"]
    report_path = reference / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if sha256(reference / "split.json") != data["provenance"]["split_sha256"]:
        raise ValueError("Graph and evaluation must use the same holdout split")
    validation = report["statistics"]["outer_validation"]
    if validation["paragraphs"] != data["provenance"]["matched_holdout_predictions"]:
        raise ValueError("Evaluation and graph holdout sizes disagree")
    variants = [
        ("no_frame", "Immer kein Frame", []),
        ("tfidf_core_050", "TF-IDF", ["Hauptdaten", "Schwelle 0,50"]),
        ("tfidf_all_050", "TF-IDF", ["mit Zusatzdaten", "Schwelle 0,50"]),
        ("tfidf_core_tuned", "TF-IDF", ["Hauptdaten", "gewichtet und abgestimmt"]),
        ("tfidf_tuned", "TF-IDF", ["mit Zusatzdaten", "gewichtet und abgestimmt"]),
    ]
    rows = []
    for key, name, details in variants:
        scores = report["metrics"][key]
        if any(not 0 <= scores[metric] <= 1 for metric in ("micro_f1", "macro_f1")):
            raise ValueError(f"Invalid evaluation scores: {key}")
        rows.append(dict(id=key, name=name, details=details, micro_f1=scores["micro_f1"], macro_f1=scores["macro_f1"]))
    data["evaluation"] = dict(rows=rows, paragraphs=validation["paragraphs"],
                              documents=validation["documents"], active_model="tfidf_tuned",
                              report_sha256=sha256(report_path), scorer_sha256=report["scorer_sha256"])

def export_visualization(reference):
    reference = Path(reference).resolve()
    data = build_graph_data(reference)
    validate(data)
    add_evaluation(data)
    template_path = ROOT / "visualisierung/framing-netz.template.html"
    template = template_path.read_text(encoding="utf-8")
    if template.count("__GRAPH_DATA__") != 1:
        raise ValueError("Template must have exactly one data placeholder")
    safe_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
    destination = ROOT / "visualisierung/index.html"
    destination.write_text(template.replace("__GRAPH_DATA__", safe_json), encoding="utf-8")
    print(f"Visualisierung: {destination}")
    return destination


def main():
    parser = argparse.ArgumentParser(description="Offline-Visualisierung aus einem lokalen November-Lauf erzeugen.")
    parser.add_argument("--run", type=Path)
    args = parser.parse_args()
    os.chdir(ROOT)
    reference = args.run
    if reference is None:
        pointer = ROOT / "outputs/latest-run.txt"
        if not pointer.is_file():
            parser.error("Zuerst scripts/reproduce_november.py ausführen. Siehe README.md.")
        reference = Path(pointer.read_text(encoding="utf-8").strip())
    export_visualization(reference)


if __name__ == "__main__":
    main()
