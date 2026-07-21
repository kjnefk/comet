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


if __name__ == "__main__":
    unittest.main()
