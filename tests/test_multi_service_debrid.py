import asyncio
import unittest
from unittest.mock import patch

from comet.api.endpoints.stream import get_and_cache_multi_service_availability


class _DebridService:
    def __init__(self, service, api_key, ip):
        self.service = service

    async def get_and_cache_availability(self, *args, **kwargs):
        info_hash = "a" * 40
        if self.service == "first":
            await asyncio.sleep(0.01)
            title = "First.mkv"
        else:
            title = "Second.mkv"
        return {info_hash}, {info_hash: {"title": title}}


class MultiServiceDebridTests(unittest.IsolatedAsyncioTestCase):
    async def test_enrichment_uses_configured_order_not_completion_order(self):
        info_hash = "a" * 40
        torrents = {
            info_hash: {
                "title": "Original.mkv",
                "seeders": 1,
                "tracker": "tracker",
                "sources": [],
            }
        }
        entries = [
            {"service": "first", "apiKey": "one"},
            {"service": "second", "apiKey": "two"},
        ]

        with patch(
            "comet.api.endpoints.stream.DebridService",
            new=_DebridService,
        ):
            status, errors = await get_and_cache_multi_service_availability(
                None,
                entries,
                torrents,
                "tt123",
                "tt123",
                None,
                None,
                "",
            )

        self.assertFalse(errors)
        self.assertEqual(torrents[info_hash]["title"], "First.mkv")
        self.assertTrue(status[info_hash]["first"])
        self.assertTrue(status[info_hash]["second"])
