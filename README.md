# SemEval 2027 Task 9

Englische Absatzklassifikation für Subtask 1: TF-IDF und 14 logistische
Klassifikatoren. Ein Absatz kann mehrere Frames oder keinen Frame erhalten.

## Installieren und einrichten

Voraussetzungen: **Git und Python 3.13** (Referenz: **3.13.13**).
Eine CPU reicht aus. Die Installation benötigt Internetzugang für die Python-Pakete.

### 1. Repository holen

In PowerShell (Windows) oder Terminal (macOS) jeden Befehl einzeln ausführen:

```bash
git clone --branch eval/november-development https://github.com/jonaidaydi/semeval-2027-task9-framing.git
cd semeval-2027-task9-framing
```

Bereits geklont? Im vorhandenen Projektordner aktualisieren:

```bash
git fetch origin
git switch eval/november-development
git pull --ff-only
```

**Alle folgenden Befehle im Ordner `semeval-2027-task9-framing` ausführen.**
Darin liegen `projekt.py`, `pyproject.toml` und `data`.
Der übergeordnete Ordner (etwa `SemEval2027`) und `src/semeval_framing`
sind nicht der richtige Startordner.

### 2. Zwei Downloads in data ablegen

Aus dem [Files-Bereich der englischen Competition](https://artist.math.unipd.it/competitions/4/)
**full-data_2026_11_16** und **starting-kit-v2** herunterladen.
Beide ZIP-Dateien vollständig in den vorhandenen Ordner `data` kopieren:

```text
semeval-2027-task9-framing/
  projekt.py
  pyproject.toml
  data/
    data-fourth-batch-russian-2026_11_1.zip
    starter-kit-v2.zip
```

Die tatsächlichen Dateinamen dürfen abweichen, etwa durch einen Zusatz `(1)`.
Der Inhalt wird automatisch erkannt. Der Name mit `russian` enthält auch die
englischen Daten. **Kein manuelles Entpacken, Verschieben einzelner Dateien oder
Ändern von Pfaden nötig.** Falls der Browser die ZIPs schon entpackt hat, stattdessen
die vollständigen entpackten Ordner in `data` ablegen. Zusätzliche Unterordner sind erlaubt.

### 3. Windows (PowerShell)

```powershell
py.exe -3.13 projekt.py einrichten
```

Nach erfolgreicher Einrichtung Training und lokale Auswertung starten:

```powershell
py.exe -3.13 projekt.py trainieren
```

Nach erfolgreichem Training die Visualisierung öffnen:

```powershell
py.exe -3.13 projekt.py anzeigen
```

Alternativ auf **[Visualisierung-starten.cmd](Visualisierung-starten.cmd)** doppelklicken.

### 3. macOS (Terminal)

```bash
python3.13 projekt.py einrichten
```

Nach erfolgreicher Einrichtung Training und lokale Auswertung starten:

```bash
python3.13 projekt.py trainieren
```

Nach erfolgreichem Training die Visualisierung öffnen:

```bash
python3.13 projekt.py anzeigen
```

Alternativ auf **[Visualisierung-starten.command](Visualisierung-starten.command)**
doppelklicken. Die Datei verwendet automatisch die eingerichtete Projektumgebung.
Bei einem Git-Clone ist sie bereits ausführbar. Falls beim Download als ZIP die
Ausführungsrechte fehlen, einmal im Projektordner ausführen:

```bash
chmod +x Visualisierung-starten.command
```

Bei einer bereits aktivierten Conda-Umgebung mit Python 3.13 kann in diesen
Befehlen `python` statt `python3.13` verwendet werden. Mit `python --version`
prüfen. Das Projekt richtet trotzdem seine eigene `.venv` ein und verwendet sie automatisch.
Die `.cmd`-Datei ist nur für Windows. Die erzeugte `visualisierung/index.html`
lässt sich auf beiden Systemen auch per Doppelklick im Browser öffnen.

## Was automatisch passiert

`einrichten` erkennt die beiden Downloads, prüft die Vollständigkeit der englischen
Texte und Annotationen sowie die Version des offiziellen Scorers. Die benötigten
Dateien werden in die erwartete Struktur kopiert. Die Originaldownloads bleiben
unverändert. Danach werden `.venv` und die festgelegten Pakete eingerichtet und
alle Tests ausgeführt. Vorhandene identische Daten werden wiederverwendet;
abweichende Versionen werden gemeldet und nicht überschrieben.

`trainieren` prüft die Daten erneut, trainiert die Baseline, wertet lokal aus und
erstellt die Visualisierung. Erwartet werden **12/12 übereinstimmende Referenzdateien**
und für die abgestimmte Variante **Micro-F1 0,3410 / Macro-F1 0,2632**.
Beim JSON-Vergleich werden Windows- und macOS-Zeilenenden vereinheitlicht.
Alle übrigen Inhalte sowie TSV-/TXT-Vorhersagen werden weiterhin bytegenau geprüft.

`anzeigen` erzeugt die HTML-Seite aus dem letzten erfolgreichen Lauf neu und
öffnet sie im Browser. Damit werden auch Änderungen am Layout übernommen.
Die Seite funktioniert anschließend offline, mit Hell-/Dunkelmodus,
vier Beispielen, Wortbeiträgen und einer Micro-/Macro-F1-Tabelle.
Die Transformer-Ansicht ist ein Schema; ein Transformer wurde noch nicht trainiert.

Tests später ohne erneute Installation ausführen:

| Windows | macOS |
|---|---|
| `py.exe -3.13 projekt.py testen` | `python3.13 projekt.py testen` |

Die Tests selbst benötigen keine Wettbewerbsdaten. Änderungen am Modell oder
an den Daten werden erst beim Trainingslauf gegen die Referenz geprüft.

## Ergebnisse und Development-Datei

Jeder Trainingslauf erhält einen eigenen Ordner unter `outputs/run-…/`.
Darin liegen `Ergebnisse.md`, `report.json`, `per_label.json`, `split.json`,
das Modell und **`submission_EN_dev.zip`** für eine manuelle Development-Einreichung.
`outputs/latest-run.txt` nennt den letzten erfolgreichen Lauf.
**Kein Befehl lädt Daten oder Ergebnisse zu Codabench hoch.**

Die automatisch vorbereiteten Eingaben liegen unter
`data/raw/release-2026-11-16/data`; der Scorer unter
`third_party/official-starter-kit/v2/scorer-subtask-1.py`.
Downloads, vorbereitete Daten, Modelle und Ergebnisse werden von Git ignoriert.

## Häufige Probleme

| Meldung | Lösung |
|---|---|
| `can't open file ... projekt.py` oder `pyproject.toml` fehlt | In den Projektordner mit `projekt.py` wechseln, danach den Befehl erneut ausführen. |
| Python 3.13 fehlt / Befehl nicht gefunden | Python 3.13 installieren oder eine vorhandene Python-3.13-Umgebung aktivieren. |
| Codabench-Dateien fehlen | Beide vollständigen Downloads in `data` ablegen und `einrichten` wiederholen. |
| Unterschiedliche Versionen | Die genannten Dateien prüfen; nur die zusammengehörigen November-Daten und das Starter-Kit v2 verwenden. |
| Noch kein erfolgreich geprüfter Trainingslauf vorhanden | Erst `trainieren`, dann `anzeigen` ausführen. Bei einem Referenzfehler die Fehlermeldung prüfen. |
| Referenzfehler nur bei JSON-Dateien mit einem älteren Repository-Stand | `git pull --ff-only` im November-Branch ausführen und das Training erneut starten. Die Prüfung berücksichtigt jetzt unterschiedliche Zeilenenden. |
| `No module named semeval_framing` bei manuellen Befehlen | `projekt.py einrichten` ausführen; danach die oben beschriebenen Startbefehle verwenden. |

Bei einem Fehler den vollständigen Befehl und die vollständige Fehlermeldung teilen.

## Eigene Experimente

Für absichtlich geänderte Daten eine separate Kopie von
[configs/november-2026-en.json](configs/november-2026-en.json) anlegen und die
Pfade dort eintragen. Relative Eingabepfade beziehen sich auf den Projektordner.

Windows:

```powershell
.\.venv\Scripts\python.exe scripts\reproduce_november.py --config pfad/zur/config.json --new-experiment
```

macOS:

```bash
.venv/bin/python scripts/reproduce_november.py --config pfad/zur/config.json --new-experiment
```

Dabei entfallen der Referenzvergleich, die automatische November-Dateneinrichtung
und die auf die vier November-Beispiele zugeschnittene Visualisierung.

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

- `projekt.py`: gemeinsame Startbefehle für Windows und macOS.
- `src/semeval_framing/november_experiment.py`: Goldlabels, Dokumentgruppen, Training, Auswertung.
- `src/semeval_framing/baseline_tfidf.py`: TF-IDF, Klassifikatoren, F1, TSV-Ausgabe.
- `src/semeval_framing/development.py`: ungelabelte Eingaben und Ausgabeprüfung.
- `scripts/`: automatische Dateneinrichtung, Trainingsstart und HTML-Export.
- `visualisierung/framing-netz.template.html`: Oberfläche und Graph.
- `tests/`: Daten-, Modell- und Browserprüfungen.

Der zusätzliche Browsertest benötigt Node.js und Playwright mit Chromium.
Nach lokalem `npm install --no-save --package-lock=false playwright@1.62.1` und
`npx playwright install chromium`: `node tests/visualization-smoke.cjs`.
Daten, Starter-Kit, Modelle, Ausgaben und die HTML-Seite mit Artikeltexten bleiben lokal.
