import argparse
from pathlib import Path
import os
import subprocess
import sys
import webbrowser

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_data import prepare, SetupError


def environment_python(root=ROOT, windows=None):
    windows = os.name == "nt" if windows is None else windows
    return root / ".venv" / ("Scripts/python.exe" if windows else "bin/python")


def execute(command):
    subprocess.run([str(item) for item in command], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description="Projekt einrichten, testen, trainieren oder anzeigen.")
    parser.add_argument("aktion", choices=["einrichten", "testen", "trainieren", "anzeigen"])
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 13):
        parser.exit(1, "Python 3.13 erforderlich. Windows: py.exe -3.13 projekt.py " + args.aktion
                    + " | macOS: python3.13 projekt.py " + args.aktion + "\n")
    python = environment_python()
    print(f"Projektordner: {ROOT}", flush=True)
    try:
        if args.aktion == "einrichten":
            prepare()
            if not python.is_file():
                execute([sys.executable, "-m", "venv", ROOT / ".venv"])
        elif not python.is_file():
            raise SetupError("Python-Umgebung fehlt. Zuerst projekt.py einrichten ausfuehren.")

        version = subprocess.check_output([str(python), "-c", "import sys; print('%s.%s' % sys.version_info[:2])"],
                                          cwd=ROOT, text=True).strip()
        if version != "3.13":
            raise SetupError("Die vorhandene .venv verwendet Python " + version
                             + ". Den Ordner .venv umbenennen und mit Python 3.13 erneut einrichten.")

        if args.aktion == "einrichten":
            execute([python, "-m", "pip", "install", "-e", ROOT])
        if args.aktion in {"einrichten", "testen"}:
            execute([python, "-m", "unittest", "discover", "-s", ROOT / "tests", "-v"])
            print("Tests bestanden. Naechster Schritt: projekt.py trainieren", flush=True)
        elif args.aktion == "trainieren":
            execute([python, ROOT / "scripts/reproduce_november.py"])
        elif args.aktion == "anzeigen":
            if not (ROOT / "outputs/latest-run.txt").is_file():
                raise SetupError("Noch kein erfolgreich gepruefter Trainingslauf vorhanden. "
                                 "Zuerst projekt.py trainieren ausfuehren; bei einem Referenzfehler dessen Meldung pruefen.")
            execute([python, ROOT / "scripts/export_visualization.py"])
            page = ROOT / "visualisierung/index.html"
            if not webbrowser.open(page.as_uri()):
                print(f"Bitte diese Datei im Browser oeffnen: {page}")
    except subprocess.CalledProcessError as error:
        parser.exit(error.returncode or 1, "Schritt fehlgeschlagen. Bitte die vollstaendige Fehlermeldung oben beachten.\n")
    except (SetupError, OSError, UnicodeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
