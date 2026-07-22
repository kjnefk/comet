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
