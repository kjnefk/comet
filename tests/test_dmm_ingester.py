import tempfile
import unittest
import zipfile
from pathlib import Path

from comet.services.dmm_ingester import extract_zip_sync


class DmmArchiveTests(unittest.TestCase):
    def test_extract_rejects_path_traversal_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "dmm.zip"
            target = root / "target"
            with zipfile.ZipFile(archive, "w") as zip_file:
                zip_file.writestr("valid/data.html", "valid")
                zip_file.writestr("../escaped.html", "escaped")

            with self.assertRaisesRegex(ValueError, "Unsafe DMM archive member"):
                extract_zip_sync(archive, target)

            self.assertFalse(target.exists())
            self.assertFalse((root / "escaped.html").exists())

    def test_extract_rejects_symlink_members(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "dmm.zip"
            target = root / "target"
            link = zipfile.ZipInfo("link")
            link.create_system = 3
            link.external_attr = 0o120777 << 16
            with zipfile.ZipFile(archive, "w") as zip_file:
                zip_file.writestr(link, "../outside")

            with self.assertRaisesRegex(ValueError, "Unsafe DMM archive member"):
                extract_zip_sync(archive, target)

            self.assertFalse(target.exists())

    def test_extract_accepts_current_nested_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "dmm.zip"
            target = root / "target"
            with zipfile.ZipFile(archive, "w") as zip_file:
                zip_file.writestr("hashlists/data.html", "valid")

            extract_zip_sync(archive, target)

            self.assertEqual((target / "hashlists" / "data.html").read_text(), "valid")
