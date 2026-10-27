# Offizielles Starter-Kit

Das vollständige Starter-Kit wird nicht in Git kopiert. Jedes Teammitglied lädt
die aktuelle Version über Codabench herunter und legt sie lokal unter
`third_party/official-starter-kit/` ab.

```text
third_party/official-starter-kit/
├── subtask1/
└── subtask2a_2b/
```

Gründe:

- mögliche Zugangs- und Weitergabebedingungen der Veranstalter;
- enthaltene Modellartefakte sind groß und nicht für Git geeignet;
- das Kit kann aktualisiert werden;
- eigene Änderungen sollen nachvollziehbar in `src/` und `tests/` entstehen.

Offizielle Scorer werden von dieser lokalen Kopie ausgeführt. Falls die
Veranstalter später ausdrücklich eine Weiterverteilung erlauben, können
bestimmte, unveränderte Skripte mit Herkunfts- und Lizenzhinweis aufgenommen
werden.

