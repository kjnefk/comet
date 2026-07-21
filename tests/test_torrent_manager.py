import hashlib
import unittest

import bencodepy

from comet.services.torrent_manager import extract_torrent_metadata
from comet.utils.parsing import is_video


class TorrentMetadataTests(unittest.TestCase):
    def test_extracts_every_tracker_and_uppercase_video_file(self):
        info = {b"name": b"Movie.MKV", b"length": 1234}
        content = bencodepy.encode(
            {
                b"announce": b"udp://fallback.example",
                b"announce-list": [
                    [b"udp://one.example", b"udp://two.example"],
                    [b"udp://three.example", b"\xff"],
                    b"invalid-tier",
                ],
                b"info": info,
            }
        )

        actual = extract_torrent_metadata(content)

        self.assertEqual(
            actual["sources"],
            [
                "udp://one.example",
                "udp://two.example",
                "udp://three.example",
                "udp://fallback.example",
            ],
        )
        self.assertEqual(
            actual["info_hash"], hashlib.sha1(bencodepy.encode(info)).hexdigest()
        )
        self.assertEqual(
            actual["files"], [{"index": 0, "title": "Movie.MKV", "size": 1234}]
        )

    def test_video_extension_matching_is_case_insensitive(self):
        self.assertTrue(is_video("Movie.MKV"))
        self.assertTrue(is_video("Movie.mKv"))
        self.assertFalse(is_video("Movie.txt"))

    def test_skips_corrupt_file_entries_without_dropping_valid_files(self):
        info = {
            b"name": b"collection",
            b"files": [
                {b"path": [b"valid.mkv"], b"length": 100},
                {b"path": [b"invalid-\xff.mkv"], b"length": 200},
                {b"path": [], b"length": 300},
                {b"path": [b"missing-size.mp4"]},
                {b"path": [b"notes.txt"], b"length": 400},
                {b"path": [b"also-valid.MP4"], b"length": 500},
            ],
        }
        content = bencodepy.encode({b"info": info})

        actual = extract_torrent_metadata(content)

        self.assertEqual(
            actual["info_hash"], hashlib.sha1(bencodepy.encode(info)).hexdigest()
        )
        self.assertEqual(
            actual["files"],
            [
                {"index": 0, "title": "valid.mkv", "size": 100},
                {"index": 5, "title": "also-valid.MP4", "size": 500},
            ],
        )


if __name__ == "__main__":
    unittest.main()
