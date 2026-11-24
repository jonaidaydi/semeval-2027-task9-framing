import hashlib
import importlib.util
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_data import BASE, DEV, MAIN, SCORER, SetupError, prepare

spec = importlib.util.spec_from_file_location("projekt", ROOT / "projekt.py")
projekt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projekt)


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(redirect_stdout(StringIO()))
        self.temp = tempfile.TemporaryDirectory(prefix="task9 setup ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        (self.root / "results").mkdir()
        self.scorer = b"official scorer fixture\n"
        (self.root / "results/reference.json").write_text(json.dumps({
            "scorer_sha256": hashlib.sha256(self.scorer).hexdigest()
        }), encoding="utf-8")
        self.files = {
            f"data/{MAIN}/EN/subtask-1-annotations-with-paragraphs.txt": b"EN_1.txt\t0\t3\ttext\nEN_M_TRAIN_4.txt\t0\t1\tx\n",
            f"data/{MAIN}/EN/raw-documents/EN_1.txt": b"\xef\xbb\xbfA\r\nB\n",
            f"data/{DEV}/EN/subtask-1-annotations-for-subtask-2b-participant.txt": b"EN_2.txt\t0\t3\tPolitical\n",
            f"data/{DEV}/EN/subtask-1-participant.txt": b"EN_3.txt\t0\t3\n",
            f"data/{DEV}/EN/raw-documents/EN_2.txt": b"two",
            f"data/{DEV}/EN/raw-documents/EN_3.txt": b"three",
            "starter-kit-v2/subtask1/scorer-subtask-1.py": self.scorer,
        }

    def archive(self, name="download (1).zip", files=None):
        path = self.root / "data" / name
        with ZipFile(path, "w") as archive:
            for member, content in (self.files if files is None else files).items():
                archive.writestr("wrapper/" + member, content)
        return path

    def test_zip_renaming_byte_preservation_and_idempotence(self):
        archive = self.archive()
        first = prepare(self.root)
        self.assertEqual(first["copied"], 7)
        self.assertEqual((self.root / BASE / MAIN / "EN/raw-documents/EN_1.txt").read_bytes(), b"\xef\xbb\xbfA\r\nB\n")
        self.assertEqual(prepare(self.root)["copied"], 0)
        archive.unlink()
        self.assertEqual(prepare(self.root)["copied"], 0)

    def test_unpacked_downloads_and_macos_metadata(self):
        for name, content in self.files.items():
            path = self.root / "data" / "download folder" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        metadata = self.root / "data/__MACOSX/scorer-subtask-1.py"
        metadata.parent.mkdir()
        metadata.write_bytes(b"resource fork")
        self.assertEqual(prepare(self.root)["copied"], 7)

    def test_missing_article_stops_before_writing(self):
        del self.files[f"data/{DEV}/EN/raw-documents/EN_3.txt"]
        self.archive()
        with self.assertRaisesRegex(SetupError, "Artikel fehlt: EN_3.txt"):
            prepare(self.root)
        self.assertFalse((self.root / "data/raw").exists())

    def test_missing_starter_kit_has_actionable_message(self):
        del self.files["starter-kit-v2/subtask1/scorer-subtask-1.py"]
        self.archive()
        with self.assertRaisesRegex(SetupError, "starting-kit-v2"):
            prepare(self.root)

    def test_conflicting_downloads_and_existing_data_are_preserved(self):
        self.archive()
        prepare(self.root)
        path = self.root / BASE / MAIN / "EN/raw-documents/EN_1.txt"
        path.write_bytes(b"local change")
        with self.assertRaisesRegex(SetupError, "Unterschiedliche Versionen"):
            prepare(self.root)
        self.assertEqual(path.read_bytes(), b"local change")

    def test_identical_duplicate_archives_are_allowed(self):
        self.archive()
        self.archive("second.zip")
        self.assertEqual(prepare(self.root)["files"], 7)

    def test_wrong_scorer_is_rejected(self):
        self.files["starter-kit-v2/subtask1/scorer-subtask-1.py"] = b"wrong version"
        self.archive()
        with self.assertRaisesRegex(SetupError, "Scorer entspricht nicht"):
            prepare(self.root)
        self.assertFalse((self.root / "third_party").exists())

    def test_archive_paths_cannot_escape_project(self):
        self.archive(files={"../../scorer-subtask-1.py": self.scorer})
        with self.assertRaisesRegex(SetupError, "Unzulaessiger Archivpfad"):
            prepare(self.root)
        self.assertFalse((self.root / "third_party").exists())

    def test_platform_specific_environment_paths(self):
        self.assertEqual(projekt.environment_python(self.root, windows=True), self.root / ".venv/Scripts/python.exe")
        self.assertEqual(projekt.environment_python(self.root, windows=False), self.root / ".venv/bin/python")


if __name__ == "__main__":
    unittest.main()
