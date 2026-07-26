import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from comet.api.endpoints.stream import stream


def _make_request():
    request = MagicMock()
    request.url.scheme = "http"
    request.url.netloc = "localhost:3000"
    request.headers = {}
    return request


DEFAULT_CONFIG = {
    "_debridEntries": [{"service": "torbox", "apiKey": "test-key"}],
    "_enableTorrent": False,
    "deduplicateStreams": False,
    "cachedOnly": False,
    "maxResultsPerResolution": 0,
    "scrapeDebridAccountTorrents": False,
    "resultFormat": "",
    "debridStreamProxyPassword": "",
}


def _make_search_result(
    service_cache_status=None,
    ranked_info_hashes=None,
    torrents=None,
    show_account_sync_trigger=False,
):
    from comet.services.media_search import MediaSearchStatus

    result = MagicMock()
    result.status = MediaSearchStatus.OK
    result.cache_state = "fresh"
    result.metadata = {"title": "Test Movie"}
    result.media_only_id = "tmdb:123"
    result.search_season = None
    result.search_episode = None
    result.service_cache_status = service_cache_status or {}
    result.debrid_errors = {}
    result.sort_mixed = False
    result.torrents = torrents or {}
    result.ranked_info_hashes = ranked_info_hashes or []
    result.show_account_sync_trigger = show_account_sync_trigger
    return result


def _make_torrent(title="Test Torrent", seeders=50, info_hash="a" * 40):
    parsed = MagicMock()
    parsed.resolution = "1080p"
    parsed.raw_title = title
    return {
        "parsed": parsed,
        "title": title,
        "seeders": seeders,
        "size": 1000000000,
        "tracker": "test-tracker",
        "sources": ["http://tracker1.example.com/announce"],
        "fileIndex": 0,
    }


class TorboxProactiveCacheTests(unittest.IsolatedAsyncioTestCase):
    async def _run_stream(self, search_result, bg_tasks, kodi=False):
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        mock_session.post.return_value = mock_response

        request = _make_request()

        with (
            patch("comet.api.endpoints.stream.config_check", return_value=DEFAULT_CONFIG),
            patch("comet.api.endpoints.stream.metrics"),
            patch("comet.api.endpoints.stream.http_client_manager") as mock_http,
            patch("comet.api.endpoints.stream.search_media", new_callable=AsyncMock, return_value=search_result),
        ):
            mock_http.get_session = AsyncMock(return_value=mock_session)
            return await stream(request, "movie", "tt1234567", bg_tasks, kodi=kodi)

    async def test_torbox_proactive_cache_triggered_for_uncached_high_seeder_torrent(self):
        info_hash = "a" * 40
        torrent = _make_torrent(seeders=50)
        search_result = _make_search_result(
            torrents={info_hash: torrent},
            ranked_info_hashes=[info_hash],
        )
        bg_tasks = MagicMock()

        await self._run_stream(search_result, bg_tasks)

        bg_tasks.add_task.assert_called()
        fn = bg_tasks.add_task.call_args[0][0]
        self.assertEqual(fn.__name__, "_cache_to_torbox")

    async def test_torbox_proactive_cache_not_triggered_when_already_cached(self):
        info_hash = "a" * 40
        torrent = _make_torrent(seeders=50)
        search_result = _make_search_result(
            service_cache_status={info_hash: {"torbox": True}},
            torrents={info_hash: torrent},
            ranked_info_hashes=[info_hash],
        )
        bg_tasks = MagicMock()

        await self._run_stream(search_result, bg_tasks)

        for call in bg_tasks.add_task.call_args_list:
            fn = call[0][0]
            if hasattr(fn, "__name__") and fn.__name__ == "_cache_to_torbox":
                self.fail("torbox proactive cache should not be triggered for cached torrents")

    async def test_torbox_proactive_cache_not_triggered_for_low_seeders(self):
        info_hash = "a" * 40
        torrent = _make_torrent(seeders=10)
        search_result = _make_search_result(
            torrents={info_hash: torrent},
            ranked_info_hashes=[info_hash],
        )
        bg_tasks = MagicMock()

        await self._run_stream(search_result, bg_tasks)

        for call in bg_tasks.add_task.call_args_list:
            fn = call[0][0]
            if hasattr(fn, "__name__") and fn.__name__ == "_cache_to_torbox":
                self.fail("torbox proactive cache should not be triggered for low seeders")

    async def test_comet_sync_streams_not_in_results(self):
        info_hash = "a" * 40
        torrent = _make_torrent(seeders=50)
        search_result = _make_search_result(
            service_cache_status={info_hash: {"torbox": True}},
            torrents={info_hash: torrent},
            ranked_info_hashes=[info_hash],
            show_account_sync_trigger=True,
        )
        bg_tasks = MagicMock()

        response = await self._run_stream(search_result, bg_tasks)

        import json
        if hasattr(response, "body"):
            content = response.body
        else:
            content = json.dumps(response).encode()
        self.assertNotIn(b"Comet Sync", content)
        self.assertNotIn(b"Sync debrid account library", content)

    async def test_torbox_cache_magnet_includes_tracker_sources(self):
        info_hash = "b" * 40
        torrent = _make_torrent(seeders=50, info_hash=info_hash)
        torrent["sources"] = [
            "http://tracker1.example.com/announce",
            "udp://tracker2.example.com:6969/announce",
        ]
        search_result = _make_search_result(
            torrents={info_hash: torrent},
            ranked_info_hashes=[info_hash],
        )
        bg_tasks = MagicMock()

        with (
            patch("comet.api.endpoints.stream.config_check", return_value=DEFAULT_CONFIG),
            patch("comet.api.endpoints.stream.metrics"),
            patch("comet.api.endpoints.stream.http_client_manager") as mock_http,
            patch("comet.api.endpoints.stream.search_media", new_callable=AsyncMock, return_value=search_result),
        ):
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=False)
            mock_session.post.return_value = mock_response
            mock_http.get_session = AsyncMock(return_value=mock_session)

            request = _make_request()
            await stream(request, "movie", "tt1234567", bg_tasks)

        bg_tasks.add_task.assert_called()
        fn = bg_tasks.add_task.call_args[0][0]
        self.assertEqual(fn.__name__, "_cache_to_torbox")

        await fn()

        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        self.assertEqual(
            call_args[0][0],
            "https://api.torbox.app/v1/api/torrents/createtorrent",
        )
        self.assertIn("magnet", call_args[1]["data"])
        magnet = call_args[1]["data"]["magnet"]
        self.assertIn("urn:btih:" + info_hash, magnet)
        self.assertIn("tracker1.example.com", magnet)
        self.assertIn("tracker2.example.com", magnet)


if __name__ == "__main__":
    unittest.main()
