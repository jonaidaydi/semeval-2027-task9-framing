# Datenablage

In Git werden **keine offiziellen Task-Daten** gespeichert. Lade die Daten über
den für das Team freigegebenen Codabench-Zugang herunter und entpacke sie lokal
unter `data/raw/`.

## Benötigte Trainingsdaten

Für die erste Subtask-1-Baseline verwenden wir:

1. den ersten offiziellen Trainings-Release;
2. den zweiten Trainings-Batch vom Oktober;
3. zunächst nur die englischen SemEval-2027-Beispiele;
4. ältere SemEval-2023-Beispiele erst in einem getrennten
   Auxiliary-Data-Experiment.

Empfohlene lokale Struktur:

```text
data/raw/
├── initial-training-data/
└── training-second-batch-oct/
    ├── BG/
    ├── EN/
    └── PT/
```

Für Subtask 1 wird jeweils die Datei
`subtask-1-annotations-with-paragraphs.txt` eingelesen. Die dazugehörigen
Rohdokumente bleiben daneben in der vom Veranstalter vorgegebenen Struktur.

## Kein-Frame-Markierungen

Die Releases verwenden nicht überall dieselbe Darstellung für negative
Beispiele. Der Projekt-Loader normalisiert folgende Varianten auf eine leere
Labelmenge:

- leeres Labelfeld;
- `-`;
- `No framing`;
- `None`.

Diese Beispiele dürfen nicht verworfen werden, weil die offizielle Auswertung
„kein Frame“ als relevante Klasse berücksichtigt.

## Verboten im Repository

- Artikeltexte und Bilder;
- Gold-Annotationen;
- Development- und Testdaten;
- ZIP-Archive der Veranstalter;
- lokale Datenkopien in beliebigen Unterordnern.

Die `.gitignore` schützt die vorgesehenen Verzeichnisse. Vor jedem Push trotzdem
immer `git status` kontrollieren.

