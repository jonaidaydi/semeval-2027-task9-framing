# SemEval 2027 Task 9

Englische Absatzklassifikation für Subtask 1: TF-IDF und 14 logistische
Klassifikatoren. Ein Absatz kann mehrere Frames oder keinen Frame erhalten.

## Installieren und testen

### 1. Repository holen und Branch auswählen

In PowerShell im gewünschten übergeordneten Ordner ausführen:

```powershell
git clone --branch eval/november-development https://github.com/jonaidaydi/semeval-2027-task9-framing.git
cd semeval-2027-task9-framing
```

Falls das Repository bereits geklont wurde, stattdessen im Projektordner:

```powershell
git fetch origin
git switch eval/november-development
```

Mit `git branch --show-current` prüfen: Die Ausgabe muss
`eval/november-development` sein.

### 2. Python-Umgebung installieren und testen

Python **3.13** (Referenz: **3.13.13**), CPU ausreichend.
Im Projektordner jeden Befehl einzeln eingeben und mit Enter ausführen:

```powershell
py.exe -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Die Paketversionen sind in [pyproject.toml](pyproject.toml) festgelegt.
Die Tests benötigen keine Wettbewerbsdaten.

## Daten einrichten

Aus dem [Files-Bereich der englischen Competition](https://artist.math.unipd.it/competitions/4/)
einmal `full-data_2026_11_16` und `starting-kit-v2` herunterladen.
Der Daten-Download hieß lokal `data-fourth-batch-russian-2026_11_1.zip`;
verarbeitet wird ausschließlich Englisch.

Das Archiv so entpacken, dass folgende Pfade existieren:

```text
data/raw/release-2026-11-16/data/
  2_training-second-batch-oct-revised/EN/
    raw-documents/
    subtask-1-annotations-with-paragraphs.txt
  3_dev-set-nov-release/EN/
    raw-documents/
    subtask-1-annotations-for-subtask-2b-participant.txt
    subtask-1-participant.txt
third_party/official-starter-kit/v2/scorer-subtask-1.py
```

Den Scorer aus dem Starter-Kit am angegebenen Ort ablegen.
Andere Speicherorte lassen sich in [configs/november-2026-en.json](configs/november-2026-en.json)
eintragen. Relative Eingabepfade beziehen sich auf den Projektordner.

## Ausführen

```powershell
.\.venv\Scripts\python.exe scripts\reproduce_november.py --show-inputs
.\.venv\Scripts\python.exe scripts\reproduce_november.py
```

Der zweite Befehl trainiert neu, prüft zwölf Ergebnisdateien gegen gespeicherte
Referenzprüfsummen und erstellt die Visualisierung. Jeder Lauf erhält einen
eigenen Ordner unter `outputs/run-…/`. Dort liegen `Ergebnisse.md`,
`report.json`, `per_label.json`, `split.json`, Modell und lokale Vorhersagen.
Es erfolgen keine Wettbewerbsabgaben.

Danach **[Visualisierung-starten.cmd](Visualisierung-starten.cmd) doppelklicken**.
Alternativ `visualisierung/index.html` direkt im Browser öffnen.
Die fertige Seite funktioniert offline, mit Hell-/Dunkelmodus, vier Beispielen,
Wortbeiträgen und einer Micro-/Macro-F1-Tabelle. Die Transformer-Ansicht ist
ausdrücklich ein Schema; ein Transformer wurde noch nicht trainiert.

Für absichtlich geänderte Daten `--config pfad/zur/config.json --new-experiment`
verwenden. Dabei entfallen der Referenzvergleich und die auf die vier
November-Beispiele zugeschnittene Visualisierung.

## Ergebnis

Lokaler Holdout: **222 Absätze aus 20 Artikeln**.

| Modell | Micro-F1 | Macro-F1 |
|---|---:|---:|
| Immer kein Frame | 0,2153 | 0,0280 |
| TF-IDF, Hauptdaten, Schwelle 0,50 | 0,2153 | 0,0280 |
| TF-IDF, mit Zusatzdaten, Schwelle 0,50 | 0,2153 | 0,0280 |
| TF-IDF, Hauptdaten, gewichtet und abgestimmt | 0,3303 | 0,2409 |
| TF-IDF, mit Zusatzdaten, gewichtet und abgestimmt | **0,3410** | **0,2632** |

- [Daten, Auswertung und Grenzen](docs/experiment.md)
- [Referenzwerte und Prüfsummen](results/reference.json)
- [Team-Workflow](docs/WORKFLOW.md)

## Code

- `src/semeval_framing/november_experiment.py`: Goldlabels, Dokumentgruppen, Training, Auswertung.
- `src/semeval_framing/baseline_tfidf.py`: TF-IDF, Klassifikatoren, F1, TSV-Ausgabe.
- `src/semeval_framing/development.py`: ungelabelte Eingaben und Ausgabeprüfung.
- `scripts/`: Trainingsstart und HTML-Export.
- `visualisierung/framing-netz.template.html`: Oberfläche und Graph.
- `tests/`: Daten-, Modell- und Browserprüfungen.

Der zusätzliche Browsertest benötigt Node.js und Playwright mit Chromium.
Nach lokalem `npm install --no-save --package-lock=false playwright@1.62.1` und
`npx playwright install chromium`: `node tests/visualization-smoke.cjs`.
Daten, Starter-Kit, Modelle, Ausgaben und die HTML-Seite mit Artikeltexten bleiben lokal.
