import asyncio
import unittest
from unittest.mock import patch

from comet.services.orchestration import TorrentManager, scraper_manager


class TorrentOrchestrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_scrape_waits_until_cache_updates_are_enqueued(self):
        manager = TorrentManager(
            media_type="movie",
            media_full_id="tt123",
            media_only_id="tt123",
            title="Title",
            year=2024,
            year_end=None,
            season=None,
            episode=None,
            aliases={},
            remove_adult_content=False,
        )
        cache_started = asyncio.Event()
        release_cache = asyncio.Event()

        async def no_scraper_results(request):
            del request
            if False:
                yield None

        async def cache_torrents():
            cache_started.set()
            await release_cache.wait()

        with (
            patch.object(scraper_manager, "scrape_all", new=no_scraper_results),
            patch.object(manager, "cache_torrents", new=cache_torrents),
        ):
            scrape = asyncio.create_task(manager.scrape_torrents())
            await cache_started.wait()
            await asyncio.sleep(0)
            self.assertFalse(scrape.done())
            release_cache.set()
            await scrape

    async def test_cache_media_id_reads_start_concurrently(self):
        manager = TorrentManager(
            media_type="movie",
            media_full_id="tt123",
            media_only_id="tt123",
            title="Title",
            year=2024,
            year_end=None,
            season=None,
            episode=None,
            aliases={},
            remove_adult_content=False,
        )
        manager.cache_media_ids = ["tt123", "kitsu:456"]
        primary_started = asyncio.Event()
        alternate_started = asyncio.Event()

        async def fetch_rows(media_id):
            if media_id == "tt123":
                primary_started.set()
                await alternate_started.wait()
            else:
                alternate_started.set()
                await primary_started.wait()
            return []

        with patch.object(manager, "_fetch_cached_rows", new=fetch_rows):
            await asyncio.wait_for(manager.get_cached_torrents(), timeout=1)

        self.assertTrue(primary_started.is_set())
        self.assertTrue(alternate_started.is_set())
