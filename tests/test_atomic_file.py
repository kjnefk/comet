import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from comet.utils.atomic_file import write_text_atomic


class AtomicFileTests(unittest.IsolatedAsyncioTestCase):
    async def test_replace_failure_preserves_previous_file_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("previous")

            with (
                patch(
                    "comet.utils.atomic_file.os.replace", side_effect=OSError("fail")
                ),
                self.assertRaisesRegex(OSError, "fail"),
            ):
                await write_text_atomic(path, "replacement")

            self.assertEqual(path.read_text(), "previous")
            self.assertEqual(list(Path(directory).glob(".*.tmp")), [])

    async def test_success_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("previous")

            await write_text_atomic(path, "replacement")

            self.assertEqual(path.read_text(), "replacement")
            self.assertEqual(list(Path(directory).glob(".*.tmp")), [])
