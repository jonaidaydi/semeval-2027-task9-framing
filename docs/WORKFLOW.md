# Team-Workflow

## Branches

- `main` bleibt ausführbar und enthält nur geprüfte Änderungen.
- Für jede Aufgabe wird ein kurzer Branch erstellt, zum Beispiel
  `data/loader-none-labels`, `model/xlmr-baseline` oder
  `eval/document-split`.
- Änderungen kommen über einen Pull Request nach `main`.

## Pull Requests

Ein Pull Request beschreibt mindestens:

1. Ziel der Änderung;
2. verwendete Datenversion und Sprache;
3. ausgeführten Test- oder Trainingsbefehl;
4. relevante Metriken;
5. bekannte Einschränkungen.

Mindestens ein anderes Teammitglied prüft den Pull Request. Große Daten,
Checkpoints und Zugangsdaten dürfen nicht Teil eines Commits sein.

## Experimente

Für jedes Ergebnis müssen folgende Angaben festgehalten werden:

- Commit-Hash;
- Subtask und Sprache;
- genaue Datenquellen;
- Split-Methode und Seed;
- Modell und Hyperparameter;
- Entscheidungsschwelle;
- Micro-F1 und Macro-F1;
- kurze Fehleranalyse.

Validierungsdaten werden dokumentweise getrennt. Absätze desselben Artikels
dürfen nicht gleichzeitig im Training und in der Validation vorkommen.

## Empfohlene Aufgabenverteilung

- **Koordination & Modellierung:** Zeitplan, Baseline und Modellarchitektur
- **Daten & Literatur:** Datenprüfung, Statistiken und Related Work
- **Evaluation & Experimente:** Splits, Scorer, Metriken und Fehleranalyse
- **Technik & Redaktion:** Git, Reproduzierbarkeit, Dokumentation und Bericht

