# SemEval 2027 Task 9 - Multimodal Framing

Team-Repository für **SemEval 2027 Task 9: Analysis of Multimodal Framing in
the News**. Wir beginnen mit **Subtask 1 (Framing in Text), Englisch** und
halten die Struktur offen für weitere Sprachen sowie Subtask 2.

## Was gehört ins Repository?

| Versionieren | Nur lokal speichern |
| --- | --- |
| Quellcode und Tests | Originale Trainings-/Development-/Testdaten |
| Konfigurationen | Offizielles Starter-Kit aus Codabench |
| Dokumentation | Modellgewichte und Checkpoints |
| Kleine, aggregierte Ergebnisdateien | Vollständige Vorhersagen und Logs |

Die offiziellen Daten können Zugangs- oder Lizenzbedingungen unterliegen.
Deshalb werden weder Daten noch das vollständige Starter-Kit in Git
eingecheckt. Alle Teammitglieder laden sie über ihren autorisierten Zugang
herunter.

## Lokale Einrichtung

```powershell
git clone https://github.com/jonaidaydi/semeval-2027-task9-framing.git
cd semeval-2027-task9-framing

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Für Training und Evaluation zusätzlich:

```powershell
python -m pip install -e ".[train]"
```

## Datenstruktur

Beide offiziellen Trainings-Releases werden verwendet, aber nur lokal unter
`data/raw/` abgelegt:

```text
data/
└── raw/
    ├── initial-training-data/
    └── training-second-batch-oct/
```

Das erste Paket enthält teilweise ältere SemEval-2023-Daten. Diese gelten als
optionale Zusatzdaten und sollten in Experimenten getrennt von den eigentlichen
SemEval-2027-Daten ausgewiesen werden.

Das offizielle Starter-Kit wird lokal hier abgelegt:

```text
third_party/
└── official-starter-kit/
    ├── subtask1/
    └── subtask2a_2b/
```

Weitere Hinweise stehen in [data/README.md](data/README.md) und
[third_party/README.md](third_party/README.md).

## Daten prüfen

Der mitgelieferte Loader verarbeitet die speziellen Markierungen `-`,
`No framing`, `None` und leere Labelfelder korrekt als **kein Frame**. Er
bewahrt Dokument-ID und Zeichen-Offsets für spätere Submissions auf.

```powershell
semeval-st1-summary data/raw
```

Alternativ ohne Installation:

```powershell
$env:PYTHONPATH = "src"
python -m semeval_framing.cli data/raw
```

## Tests

```powershell
python -m pytest
```

Oder nur mit der Python-Standardbibliothek:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

## Nächste technische Schritte

- [ ] Offizielle Daten lokal in die beschriebene Struktur kopieren
- [ ] Datenstatistik für jede Sprache erzeugen und gemeinsam prüfen
- [ ] Dokumentweisen Train-/Validation-Split implementieren
- [ ] XLM-RoBERTa-Baseline auf Subtask 1 / Englisch reproduzieren
- [ ] Submission-Writer und offiziellen Scorer integrieren
- [ ] Ersten reproduzierbaren Experimentbericht anlegen

Arbeitsregeln und Branch-Konventionen stehen in
[docs/WORKFLOW.md](docs/WORKFLOW.md).

