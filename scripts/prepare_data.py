import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
MAIN = "2_training-second-batch-oct-revised"
DEV = "3_dev-set-nov-release"
BASE = "data/raw/release-2026-11-16/data"
SCORER = "third_party/official-starter-kit/v2/scorer-subtask-1.py"
ANNOTATIONS = {
    MAIN: ("subtask-1-annotations-with-paragraphs.txt",),
    DEV: ("subtask-1-annotations-for-subtask-2b-participant.txt", "subtask-1-participant.txt"),
}
MAX_FILE_SIZE = 16 * 1024 * 1024


class SetupError(ValueError):
    pass


def destination(name):
    path = PurePosixPath(name.replace("\\", "/"))
    parts = path.parts
    if path.is_absolute() or any(p == ".." or ":" in p for p in parts):
        raise SetupError(f"Unzulaessiger Archivpfad: {name}")
    if "__MACOSX" in parts or any(p.startswith("._") for p in parts):
        return None
    if path.name == "scorer-subtask-1.py":
        return SCORER
    for stage, annotations in ANNOTATIONS.items():
        if stage not in parts:
            continue
        tail = parts[parts.index(stage):]
        if len(tail) == 3 and tail[1] == "EN" and tail[2] in annotations:
            return f"{BASE}/{'/'.join(tail)}"
        if len(tail) == 4 and tail[1:3] == ("EN", "raw-documents") and tail[3].endswith(".txt"):
            return f"{BASE}/{'/'.join(tail)}"
    return None


def input_files(data):
    for directory, folders, files in os.walk(data, followlinks=False):
        folders[:] = sorted(name for name in folders
                            if not name.startswith(".") and name != "__MACOSX"
                            and not (Path(directory) / name).is_symlink()
                            and not (Path(directory) == data and name == "raw"))
        for name in sorted(files):
            path = Path(directory) / name
            if not path.is_symlink() and not name.startswith("."):
                yield path


def prepare(root=ROOT):
    root = Path(root).resolve()
    data = root / "data"
    data.mkdir(exist_ok=True)
    contents, origins = {}, {}

    def add(target, content, origin):
        if len(content) > MAX_FILE_SIZE:
            raise SetupError(f"Datei zu gross: {origin}")
        if target in contents and contents[target] != content:
            raise SetupError(f"Unterschiedliche Versionen fuer {target}: {origins[target]} und {origin}. "
                             "Bitte nur die zusammengehoerigen November-Daten und starting-kit-v2 verwenden.")
        contents[target] = content
        origins[target] = str(origin)

    for path in input_files(data):
        if path.suffix.lower() == ".zip":
            try:
                with ZipFile(path) as archive:
                    for entry in archive.infolist():
                        if entry.is_dir():
                            continue
                        target = destination(entry.filename)
                        if target:
                            if entry.file_size > MAX_FILE_SIZE:
                                raise SetupError(f"Datei zu gross: {path.name}/{entry.filename}")
                            add(target, archive.read(entry), f"{path.name}/{entry.filename}")
            except BadZipFile as error:
                raise SetupError(f"ZIP nicht lesbar: {path.name}. Bitte erneut herunterladen.") from error
        else:
            target = destination(path.relative_to(data).as_posix())
            if target:
                if path.stat().st_size > MAX_FILE_SIZE:
                    raise SetupError(f"Datei zu gross: {path}")
                add(target, path.read_bytes(), path)

    required = [SCORER] + [f"{BASE}/{stage}/EN/{name}"
                          for stage, names in ANNOTATIONS.items() for name in names]
    existing = [root / name for name in required]
    for stage in ANNOTATIONS:
        existing.extend((root / BASE / stage / "EN/raw-documents").glob("*.txt"))
    for path in existing:
        if path.is_file():
            add(path.relative_to(root).as_posix(), path.read_bytes(), path)

    missing = [name for name in required if name not in contents]
    if missing:
        raise SetupError("Codabench-Dateien fehlen. Die beiden Downloads full-data_2026_11_16 "
                         "und starting-kit-v2 als ZIP oder entpackte Ordner direkt in "
                         f"{data} ablegen. Fehlend: " + ", ".join(Path(name).name for name in missing))

    reference = json.loads((root / "results/reference.json").read_text(encoding="utf-8"))
    if hashlib.sha256(contents[SCORER]).hexdigest() != reference["scorer_sha256"]:
        raise SetupError("Der Scorer entspricht nicht der November-Referenz. Bitte starting-kit-v2 verwenden.")

    document_counts = {}
    for stage, names in ANNOTATIONS.items():
        for name in names:
            annotation = f"{BASE}/{stage}/EN/{name}"
            documents = set()
            for line in contents[annotation].decode("utf-8-sig").splitlines():
                if not line.strip():
                    continue
                document = line.split("\t")[0]
                if document.removesuffix(".txt") == "EN_M_TRAIN_4":
                    continue
                if not document or "/" in document or "\\" in document or ":" in document or document in {".", ".."}:
                    raise SetupError(f"Ungueltiger Dokumentname in {name}: {document}")
                target = f"{BASE}/{stage}/EN/raw-documents/{document}"
                if target not in contents:
                    raise SetupError(f"Artikel fehlt: {document}. Bitte den vollstaendigen Full-Data-Download in data ablegen.")
                documents.add(document)
            if not documents:
                raise SetupError(f"Annotationsdatei ist leer: {name}")
            document_counts[name] = len(documents)

    copied = 0
    for target, content in contents.items():
        path = root / target
        if not path.resolve().is_relative_to(root):
            raise SetupError(f"Ziel liegt ausserhalb des Projekts: {path}")
        if path.exists():
            if path.read_bytes() != content:
                raise SetupError(f"Vorhandene Datei weicht ab: {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(content)
        copied += 1
    print(f"Daten bereit: {len(contents)} Dateien geprueft, {copied} neu eingerichtet.", flush=True)
    for name, count in document_counts.items():
        print(f"  {name}: {count} Artikel", flush=True)
    return {"files": len(contents), "copied": copied, "documents": document_counts}


def main():
    parser = argparse.ArgumentParser(description="Codabench-Downloads aus data automatisch einrichten.")
    parser.parse_args()
    try:
        prepare()
    except (SetupError, OSError, UnicodeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
