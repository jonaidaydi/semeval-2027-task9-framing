# Experiment vom 16./17. November 2026

## Daten

| Quelle | Artikel | Absätze |
|---|---:|---:|
| Revidierte englische Hauptdaten | 96 | 1.036 |
| Erlaubte Text-Goldlabels aus Subtask 2b | 20 | 224 |
| Zusammen mit Goldlabels | 116 | 1.260 |
| Development ohne sichtbare Goldlabels | 55 | 558 |

Von 1.260 Absätzen haben 324 kein Label, 936 mindestens eines.
Mehrfachlabels ergeben insgesamt 1.504 positive Frame-Zuweisungen.
Die 14 offiziellen Klassen stehen in
[labels.py](../src/semeval_framing/labels.py). `None` bezeichnet bei der
Auswertung eine leere Labelmenge, keinen zusätzlich trainierten Klassifikator.

Die Nachrichten behandeln unter anderem Migration, internationale Konflikte,
Politik, Gesundheit und wirtschaftliche Folgen. Dies ist eine qualitative
Sichtung ausgewählter Texte, keine vollständige Themen- oder Quellenstatistik.

`EN_M_TRAIN_4` wird gemäß Veranstalterhinweis ausgeschlossen.
Bei vier Abweichungen zwischen Rohtext-Offsets und annotierter Textspalte
wird die offizielle Textspalte verwendet; der Report nennt diese Fälle.
Die fünf Trial-Artikel (113 Absätze) sind im aktuellen Datenstand enthalten.
Die Daten- und Splitentscheidung für weitere Teamversuche ist noch abzustimmen.

## Modell und Split

TF-IDF verwendet kleingeschriebene Wort-Unigramme, höchstens 30.000 Merkmale
und L2-Normalisierung. Pro Frame wird eine logistische Regression trainiert
(C=1, maximal 1.000 Iterationen, Seed 42).

Der äußere Split hält 20 Artikel mit 222 Absätzen zurück.
Im Training bleiben 1.038 Absätze aus 96 Artikeln, einschließlich Zusatzdaten.
Artikel mit identischen nichtleeren Absätzen werden nach NFKC-, Kleinschreibungs-
und Leerraumnormalisierung zu gemeinsamen Gruppen verbunden.

Drei innere, dokumentweise getrennte Folds wählen Klassengewichtung und
eine gemeinsame Entscheidungsschwelle. TF-IDF wird in jedem Fold neu gelernt.
Geprüft werden ungewichtet/ausgeglichen sowie Schwellen von 0,10 bis 0,55
in 0,05-Schritten. Auswahl: höchster Micro-F1, dann Macro-F1, dann höhere
Schwelle. Gewählt wurden ausgeglichene Klassen und **0,45**.

Für jeden Frame gilt: Modellwert mindestens 0,45 ergibt ein ausgegebenes Label.
Die Werte sind keine geprüften, kalibrierten Wahrscheinlichkeiten.

## Auswertung und Fehler

Alle fünf Varianten nutzen denselben äußeren Holdout. Der lokale Nachbau
der F1-Berechnung wird gegen den offiziellen Scorer v2 geprüft. Micro-F1
fasst alle Labelentscheidungen zusammen. Macro-F1 mittelt die 14 Frames
und `None` gleichgewichtet. Die Scorer-Konvention bei undefiniertem F1
wird unverändert übernommen.

Die abgestimmte Variante mit Zusatzdaten erreicht **Micro-F1 0,3410**
und **Macro-F1 0,2632**. Die ungewichteten Varianten mit Schwelle 0,50
geben für sämtliche Holdout-Absätze kein Frame aus.

Beispiel: `EN_M_TRAIN_1.txt`, Zeichen 1799 bis 2093, Gold `Public_opinion`.
Der Modellwert 0,2816 bleibt unter 0,45; die vorhergesagte Labelmenge ist leer.
Dadurch wird Public opinion übersehen und None fälschlich ausgegeben.
Insgesamt hat None im Holdout 59 Goldfälle und 72 Vorhersagen:
29 richtig, 43 zusätzlich, 30 übersehen. Das ist kein Scorerfehler.

Die Visualisierung rekonstruiert ausschließlich das Holdout-Modell aus den
Trainingsdokumenten und vergleicht alle 222 Vorhersagen. Eine Kante entspricht
TF-IDF-Wert × Regressionsgewicht. Beiträge plus Basiswert ergeben den linearen
Wert; erst die Sigmoid-Funktion ergibt den Modellwert.

## Grenzen und nächster Schritt

- Der Holdout ist klein. Der Zugewinn durch Zusatzdaten beweist keine robuste Überlegenheit.
- Beinahe identische Artikel wurden nicht systematisch untersucht.
- Drei Development-Absätze stimmen nach Normalisierung mit mindestens 80 Zeichen langen Trainingsabsätzen überein.
- Development besitzt keine sichtbaren Goldlabels. Es gibt dafür keinen lokalen F1 und keine Einreichung.
- Das abschließende Development-Modell wird auf allen 1.260 Goldabsätzen trainiert. Es ist kein Modell für eine erneute Holdout-Bewertung.
- Transformer-Merkmale und Fine-Tuning sind als nächster Vergleich geplant, noch ohne Messwerte.

Für den Transformer-Vergleich zuerst Datenumfang und Split mit der Gruppe
festlegen. Dann dieselben Eingaben und denselben Scorer für feste
Transformer-Merkmale und anschließend Fine-Tuning verwenden.

## Reproduzierbarkeit

[reference.json](../results/reference.json) enthält aggregierte Werte,
Paketversionen und SHA-256-Prüfsummen von zwölf Ergebnisdateien.
Der Startbefehl benötigt keinen bestehenden Ergebnisordner.
Zeitstempel, Laufzeit, Pfade und serialisierte Modell-/ZIP-Bytes werden
nicht auf Bytegleichheit geprüft. Eingabedateien, Code und Versionen werden
in jedem lokalen Report protokolliert.

Geprüft wurde eine frische Installation unter Windows mit Python 3.13.13.
Bytegleichheit auf anderen Betriebssystemen wurde nicht geprüft.

Die Teambeiträge sind über die Git-Historie zuzuordnen. Datensatz und
Scorer stammen von den Veranstaltern. Frühere Arbeitsblätter beschreiben
Planungen und sind kein Nachweis, wer den heutigen Modellcode implementiert hat.
