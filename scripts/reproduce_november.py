import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import sys
import tomllib
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from semeval_framing.november_experiment import run, save_json
from export_visualization import export_visualization
from prepare_data import prepare, SetupError


def show_inputs(config):
    sources = [("Hauptdaten", config["main"])]
    sources += [("Zusatzdaten", source) for source in config.get("auxiliary", [])]
    sources += [("Development", config["development"])]
    missing = []
    for name, source in sources:
        print(name + ":")
        for key in ("annotations", "participants", "articles"):
            if key not in source:
                continue
            path = Path(source[key])
            print(f"  {key}: {path}")
            if not path.exists():
                missing.append(str(path))
    print("Scorer:", config["scorer"])
    if not Path(config["scorer"]).is_file():
        missing.append(config["scorer"])
    return missing


def check_reference(output, report):
    reference = json.loads((ROOT / "results/reference.json").read_text(encoding="utf-8"))
    files = {}
    for name, expected in reference["files_sha256"].items():
        content = (output / name).read_bytes()
        if Path(name).suffix == ".json":
            content = content.replace(b"\r\n", b"\n")
        files[name] = hashlib.sha256(content).hexdigest() == expected
    fields = {key: report[key] == reference[key]
              for key in ("statistics", "metrics", "scorer_sha256")}
    return {"passed": all(files.values()) and all(fields.values()),
            "files": files, "report_fields": fields,
            "comparison": "JSON: LF-normalisierte Zeilenenden; TSV/TXT: bytegenau",
            "python": platform.python_version(), "reference_python": reference["versions"]["python"]}


def write_summary(output, report, check):
    rows = ["# Ergebnisse", "", f"Lauf: `{output.relative_to(ROOT).as_posix()}`", "",
            "| Variante | Micro-F1 | Macro-F1 |", "|---|---:|---:|"]
    for name, scores in report["metrics"].items():
        rows.append(f"| {name} | {scores['micro_f1']:.4f} | {scores['macro_f1']:.4f} |")
    stats = report["statistics"]["outer_validation"]
    rows += ["", f"Lokaler Holdout: {stats['paragraphs']} Absätze aus {stats['documents']} Artikeln.",
             "Micro-F1 bündelt alle Labelentscheidungen. Macro-F1 mittelt 14 Frames und None gleichgewichtet.",
             "F1 liegt zwischen 0 und 1. Es ist keine Accuracy.", "",
             "Die Development-Eingaben haben keine Goldlabels; dafür wurde kein F1 berechnet.",
             "Es wurde nichts bei Codabench eingereicht.", "",
             f"Referenzprüfung: {'bestanden' if check and check['passed'] else 'nicht durchgeführt'}.",
             "Details: report.json, per_label.json, split.json und reproduction-check.json."]
    (output / "Ergebnisse.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Trainieren, lokal auswerten und Visualisierung erzeugen.")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/november-2026-en.json")
    parser.add_argument("--show-inputs", action="store_true")
    parser.add_argument("--new-experiment", action="store_true",
                        help="Für geänderte Daten: ohne Vergleich mit der November-Referenz.")
    args = parser.parse_args()
    config_path = args.config.resolve()
    os.chdir(ROOT)
    if config_path == (ROOT / "configs/november-2026-en.json").resolve():
        try:
            prepare(ROOT)
        except (SetupError, OSError, UnicodeError) as error:
            parser.error(str(error))
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    missing = show_inputs(config)
    if missing:
        parser.error("Lokale Daten fehlen. Siehe README.md. Fehlend: " + ", ".join(missing))
    if args.show_inputs:
        return
    requirements = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
    for requirement in requirements:
        name, expected = requirement.split("==")
        if metadata.version(name) != expected:
            parser.error(f"Paketversion abweichend: {requirement}. Bitte das Projekt neu installieren.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "outputs" / f"run-{stamp}-{uuid.uuid4().hex[:8]}"
    output.mkdir(parents=True)
    config["output"] = output.relative_to(ROOT).as_posix()
    temporary = ROOT / "outputs" / f"config-{output.name}.json"
    save_json(temporary, config)
    try:
        report = run(temporary)
    finally:
        temporary.unlink()
    check = None if args.new_experiment else check_reference(output, report)
    save_json(output / "reproduction-check.json", check or {"status": "new_experiment"})
    if check and not check["passed"]:
        raise SystemExit(f"Referenzvergleich fehlgeschlagen. Details: {output / 'reproduction-check.json'}")
    write_summary(output, report, check)
    if not args.new_experiment:
        export_visualization(output)
    (ROOT / "outputs/latest-run.txt").write_text(output.relative_to(ROOT).as_posix(), encoding="utf-8")
    print(f"\nErgebnisblatt: {output / 'Ergebnisse.md'}")
    print("Referenzvergleich: " + ("12/12 Dateien stimmen ueberein (JSON-Zeilenenden normalisiert)" if check else "neues Experiment"))
    if not args.new_experiment:
        print("Visualisierung: projekt.py anzeigen mit Python 3.13 ausfuehren")


if __name__ == "__main__":
    main()
