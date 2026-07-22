import unittest

from comet.scrapers.aiostreams import AiostreamsScraper
from comet.scrapers.comet import CometScraper
from comet.scrapers.mediafusion import MediaFusionScraper
from comet.scrapers.models import ScrapeRequest
from comet.scrapers.peerflix import PeerflixScraper
from comet.scrapers.torrentsdb import TorrentsDBScraper


class _Response:
    def __init__(self, payload):
        self.payload = payload
        self.status = 200

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

    async def test_torrentsdb_isolates_malformed_stream(self):
        payload = {
            "streams": [
                {
                    "title": "First.Movie\n👤 12 💾 1 GB ⚙️ RARBG",
                    "infoHash": "A" * 40,
                    "sources": [],
                },
                None,
                {"title": "Broken.Movie"},
                {
                    "title": "Second.Movie\n💾 2 GB",
                    "infoHash": "C" * 40,
                    "sources": ["tracker:second"],
                },
            ]
        }
        scraper = TorrentsDBScraper(None, _Session(payload))

        torrents = await scraper.scrape(REQUEST)

        self.assertEqual(
            [torrent["title"] for torrent in torrents], ["First.Movie", "Second.Movie"]
        )
        self.assertEqual([torrent["seeders"] for torrent in torrents], [12, None])

    async def test_peerflix_isolates_malformed_stream(self):
        payload = {
            "streams": [
                {
                    "description": "First.Movie\n🌐RARBG",
                    "infoHash": "A" * 40,
                    "fileIdx": 1,
                    "sources": [],
                },
                {"description": "Broken.Movie", "infoHash": "B" * 40},
                {
                    "description": "Second.Movie",
                    "infoHash": "C" * 40,
                    "fileIdx": 2,
                    "sources": ["tracker:second"],
                },
            ]
        }
        scraper = PeerflixScraper(None, _Session(payload))

        torrents = await scraper.scrape(REQUEST)

        self.assertEqual(
            [torrent["title"] for torrent in torrents], ["First.Movie", "Second.Movie"]
        )
        self.assertEqual([torrent["fileIndex"] for torrent in torrents], [1, 2])

    async def test_comet_isolates_malformed_stream(self):
        payload = {
            "streams": [
                {
                    "description": "📄 First.Movie\n👤 12 seeders\n🔎 RARBG",
                    "infoHash": "A" * 40,
                    "behaviorHints": {"videoSize": 1_000},
                    "sources": [],
                },
                {
                    "description": "📄 Broken.Movie\n👤 unknown seeders",
                    "infoHash": "B" * 40,
                    "behaviorHints": {},
                },
                {
                    "description": "📄 Second.Movie",
                    "infoHash": "C" * 40,
                    "behaviorHints": {"videoSize": 2_000},
                    "sources": ["tracker:second"],
                },
            ]
        }
        scraper = CometScraper(None, _Session(payload), "https://comet.test")

        torrents = await scraper.scrape(REQUEST)

        self.assertEqual(
            [torrent["title"] for torrent in torrents], ["First.Movie", "Second.Movie"]
        )
        self.assertEqual([torrent["seeders"] for torrent in torrents], [12, None])
