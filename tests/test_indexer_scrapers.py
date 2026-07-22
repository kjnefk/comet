import unittest
from unittest.mock import AsyncMock, patch

from comet.scrapers.jackett import JackettScraper
from comet.scrapers.models import ScrapeRequest
from comet.scrapers.prowlarr import ProwlarrScraper


REQUEST = ScrapeRequest(
    media_type="movie",
    media_id="tt123",
    media_only_id="tt123",
    title="Movie",
)


def _torrent(info_hash):
    return {
        "title": info_hash,
        "infoHash": info_hash,
        "fileIndex": None,
        "seeders": None,
        "size": None,
        "tracker": "indexer",
        "sources": [],
    }


class IndexerScraperTests(unittest.IsolatedAsyncioTestCase):
    async def test_jackett_isolates_malformed_and_failed_results(self):
        results = [
            {"Details": "first", "token": "first"},
            None,
            {"token": "missing-details"},
            {"Details": "failed", "token": "failed"},
            {"Details": "second", "token": "second"},
        ]

        async def process(result, media_id, season):
            del media_id, season
            if result["token"] == "failed":
                raise RuntimeError("bad torrent payload")
            return [None, _torrent(result["token"])]

        scraper = JackettScraper(None, None, "https://jackett.test")
        scraper.fetch_jackett_results = AsyncMock(return_value=results)
        scraper.process_torrent = AsyncMock(side_effect=process)
        with patch("comet.scrapers.jackett.settings.JACKETT_INDEXERS", ["indexer"]):
            torrents = await scraper.scrape(REQUEST)

        self.assertEqual(
            [torrent["infoHash"] for torrent in torrents], ["first", "second"]
        )

    async def test_prowlarr_isolates_malformed_search_results(self):
        results = [
            {"infoUrl": "first", "token": "first"},
            None,
            {"token": "missing-info-url"},
            {"infoUrl": "second", "token": "second"},
        ]

        async def process(result, media_id, season):
            del media_id, season
            return [None, _torrent(result["token"])]

        scraper = ProwlarrScraper(None, None, "https://prowlarr.test")
        scraper._fetch_search_results = AsyncMock(return_value=results)
        scraper.process_torrent = AsyncMock(side_effect=process)
        with patch("comet.scrapers.prowlarr.settings.PROWLARR_INDEXERS", ["1"]):
            torrents = await scraper.scrape(REQUEST)

        self.assertEqual(
            [torrent["infoHash"] for torrent in torrents], ["first", "second"]
        )
