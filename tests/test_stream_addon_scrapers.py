import unittest

from comet.scrapers.aiostreams import AiostreamsScraper
from comet.scrapers.mediafusion import MediaFusionScraper
from comet.scrapers.models import ScrapeRequest


class _Response:
    def __init__(self, payload):
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def json(self):
        return self.payload


class _Session:
    def __init__(self, payload):
        self.payload = payload

    def get(self, url, **kwargs):
        return _Response(self.payload)


REQUEST = ScrapeRequest(
    media_type="movie",
    media_id="tt123",
    media_only_id="tt123",
    title="Movie",
)


class StreamAddonScraperTests(unittest.IsolatedAsyncioTestCase):
    async def test_mediafusion_isolates_malformed_stream(self):
        payload = {
            "streams": [
                {
                    "description": "📂 First.Movie/\n👤 12\n🔗 RARBG",
                    "infoHash": "A" * 40,
                    "behaviorHints": {"videoSize": 1_000},
                    "sources": [],
                },
                {"infoHash": "B" * 40},
                {
                    "description": "📂 Second.Movie/\n👤 3\n🔗 YTS",
                    "infoHash": "C" * 40,
                    "behaviorHints": {"videoSize": 2_000},
                    "sources": ["tracker:second"],
                },
            ]
        }
        scraper = MediaFusionScraper(None, _Session(payload), "https://mf.test")

        torrents = await scraper.scrape(REQUEST)

        self.assertEqual(
            [torrent["title"] for torrent in torrents], ["First.Movie", "Second.Movie"]
        )
        self.assertEqual([torrent["seeders"] for torrent in torrents], [12, 3])

    async def test_aiostreams_isolates_malformed_stream(self):
        payload = {
            "data": {
                "results": [
                    {
                        "filename": "First.Movie",
                        "infoHash": "a" * 40,
                        "size": 1_000,
                        "sources": [],
                    },
                    {"infoHash": "b" * 40, "size": 10},
                    {
                        "filename": "Second.Movie",
                        "infoHash": "c" * 40,
                        "size": 2_000,
                        "indexer": "Usenet",
                        "sources": ["tracker:second"],
                    },
                ]
            }
        }
        scraper = AiostreamsScraper(None, _Session(payload), "https://aio.test")

        torrents = await scraper.scrape(REQUEST)

        self.assertEqual(
            [torrent["title"] for torrent in torrents], ["First.Movie", "Second.Movie"]
        )
        self.assertEqual(
            [torrent["tracker"] for torrent in torrents],
            ["AIOStreams", "AIOStreams|Usenet"],
        )
