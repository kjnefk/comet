import unittest
from unittest.mock import AsyncMock, patch

from comet.api.endpoints.playback import (
    _cache_download_link_safely,
    _decode_sources,
)


class PlaybackCacheTests(unittest.IsolatedAsyncioTestCase):
    def test_sources_require_current_string_list_schema(self):
        self.assertEqual(
            _decode_sources(b'["tracker:first", null, "", 42, "tracker:second"]'),
            ["tracker:first", "tracker:second"],
        )
        self.assertEqual(_decode_sources(b"not-json"), [])
        self.assertEqual(_decode_sources(b'{"tracker": "first"}'), [])

    async def test_cache_write_failure_does_not_discard_generated_link(self):
        with patch(
            "comet.api.endpoints.playback.cache_download_link",
            new=AsyncMock(side_effect=RuntimeError("database unavailable")),
        ) as cache:
            await _cache_download_link_safely(
                debrid_service="realdebrid",
                account_key_hash="account",
                info_hash="a" * 40,
                season=None,
                episode=None,
                download_url="https://download.test/video",
            )

        cache.assert_awaited_once()
