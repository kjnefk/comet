import unittest
from unittest.mock import AsyncMock, patch

from comet.debrid.exceptions import DebridLinkGenerationError
from comet.debrid.stremthru import (
    StremThru,
    _prepare_cached_torrents,
)


class StremThruAvailabilityTests(unittest.TestCase):
    def test_malformed_torrents_and_files_are_isolated_once(self):
        responses = [
            None,
            {"data": {"items": "invalid"}},
            {
                "data": {
                    "items": [
                        {"status": "cached", "files": []},
                        {
                            "status": "cached",
                            "hash": "a" * 40,
                            "files": [
                                None,
                                {"name": "Sample.mkv", "index": 0, "size": 10},
                                {
                                    "name": "folder/First.S01E01.mkv",
                                    "index": 1,
                                    "size": 20,
                                },
                                {"name": 42},
                                {"name": "Second.S01E02.MP4", "index": 2, "size": 30},
                            ],
                        },
                        {"status": "downloading", "hash": "b" * 40, "files": []},
                    ]
                }
            },
        ]

        torrents, filenames = _prepare_cached_torrents(
            responses,
            is_offcloud=False,
        )

        self.assertEqual(filenames, ["First.S01E01.mkv", "Second.S01E02.MP4"])
        self.assertEqual([torrent["info_hash"] for torrent in torrents], ["a" * 40])
        self.assertEqual(
            [filename for _, filename in torrents[0]["files"]],
            filenames,
        )


class StremThruResponseTests(unittest.IsolatedAsyncioTestCase):
    async def test_unexpected_link_error_is_typed_and_visible(self):
        client = StremThru(None, None, None, "realdebrid:token", "")
        with patch.object(
            client,
            "_post_store_json",
            new=AsyncMock(side_effect=RuntimeError("transport failed")),
        ):
            with self.assertRaises(DebridLinkGenerationError) as raised:
                await client.generate_download_link(
                    "a" * 40,
                    "0",
                    "Movie.mkv",
                    "Movie",
                    None,
                    None,
                )

        self.assertEqual(raised.exception.payload["error_type"], "RuntimeError")
        self.assertIsInstance(raised.exception.__cause__, RuntimeError)
