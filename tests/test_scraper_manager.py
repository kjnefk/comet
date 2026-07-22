import asyncio
import unittest
from unittest.mock import patch

from comet.scrapers.manager import ScraperManager, network_manager, settings
from comet.scrapers.models import ScrapeRequest


class ScraperManagerTaskTests(unittest.IsolatedAsyncioTestCase):
    async def test_closing_results_cancels_unfinished_scrapers(self):
        slow_started = asyncio.Event()
        slow_cancelled = asyncio.Event()

        class FastScraper:
            impersonate = None

            def __init__(self, manager, client, url=None):
                del manager, client, url

            async def scrape(self, request):
                del request
                await slow_started.wait()
                return []

        class SlowScraper:
            impersonate = None

            def __init__(self, manager, client, url=None):
                del manager, client, url

            async def scrape(self, request):
                del request
                slow_started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    slow_cancelled.set()

        manager = ScraperManager.__new__(ScraperManager)
        manager.scrapers = {
            "NyaaScraper": FastScraper,
            "ZileanScraper": SlowScraper,
        }
        request = ScrapeRequest(
            media_type="movie",
            media_id="tt123",
            media_only_id="tt123",
            title="Title",
            year=2024,
            year_end=None,
            season=None,
            episode=None,
            context="live",
        )

        with (
            patch.object(settings, "SCRAPE_NYAA", True),
            patch.object(settings, "NYAA_ANIME_ONLY", False),
            patch.object(settings, "SCRAPE_ZILEAN", True),
            patch.object(network_manager, "get_client", return_value=object()),
        ):
            results = manager.scrape_all(request)
            await anext(results)
            await results.aclose()

        self.assertTrue(slow_cancelled.is_set())
