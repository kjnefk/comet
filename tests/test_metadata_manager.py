import asyncio
import unittest

from comet.metadata.manager import MetadataScraper


class _SharedMetadataState:
    def __init__(self):
        self.cached = None
        self.initial_checks = 0
        self.both_checked = asyncio.Event()
        self.metadata_calls = 0
        self.alias_calls = 0
        self.cache_calls = 0


class _MetadataScraper(MetadataScraper):
    def __init__(self, state):
        super().__init__(session=None)
        self.state = state
        self.first_check = True

    async def get_cached(self, media_id, season, episode):
        if self.first_check:
            self.first_check = False
            self.state.initial_checks += 1
            if self.state.initial_checks == 2:
                self.state.both_checked.set()

        if self.state.cached is None:
            return None

        metadata, aliases = self.state.cached
        return {**metadata, "season": season, "episode": episode}, aliases

    async def get_metadata(self, id, season, episode, is_kitsu, media_type):
        await self.state.both_checked.wait()
        self.state.metadata_calls += 1
        return {
            "title": "Shared Movie",
            "year": 2026,
            "year_end": None,
            "season": season,
            "episode": episode,
        }

    async def get_aliases(self, media_type, media_id, provider=None):
        self.state.alias_calls += 1
        return {"en": ["Shared Movie"]}

    async def cache_metadata(
        self,
        media_id,
        metadata,
        aliases,
        preserve_existing_metadata=False,
    ):
        self.state.cache_calls += 1
        self.state.cached = (
            {key: metadata[key] for key in ("title", "year", "year_end")},
            aliases,
        )
        return aliases


class MetadataRefreshTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_cache_misses_share_one_refresh(self):
        state = _SharedMetadataState()
        first = _MetadataScraper(state)
        second = _MetadataScraper(state)

        first_result, second_result = await asyncio.gather(
            first.fetch_metadata_and_aliases(
                "series", "tt123:1:1", "tt123", season=1, episode=1
            ),
            second.fetch_metadata_and_aliases(
                "series", "tt123:1:2", "tt123", season=1, episode=2
            ),
        )

        self.assertEqual(state.metadata_calls, 1)
        self.assertEqual(state.alias_calls, 1)
        self.assertEqual(state.cache_calls, 1)
        self.assertEqual(first_result[0]["episode"], 1)
        self.assertEqual(second_result[0]["episode"], 2)
