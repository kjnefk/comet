import asyncio
import unittest
from unittest.mock import patch

from comet.services.anime import AnimeMapper


class AnimeMapperTests(unittest.IsolatedAsyncioTestCase):
    async def test_corrupt_cached_entry_degrades_to_no_aliases(self):
        mapper = AnimeMapper()
        mapper.loaded = True

        with patch(
            "comet.services.anime.database.fetch_one",
            return_value={"data_json": "not-json"},
        ):
            aliases = await mapper.get_aliases("tt123")

        self.assertEqual(aliases, {})

    async def test_aliases_keep_only_ordered_unique_current_strings(self):
        mapper = AnimeMapper()
        mapper.loaded = True
        payload = b'{"title":"Main","synonyms":["Alt",null,"Main",42,"Alt"]}'

        with patch(
            "comet.services.anime.database.fetch_one",
            return_value={"data_json": payload},
        ):
            aliases = await mapper.get_aliases("tt123")

        self.assertEqual(aliases, {"ez": ["Main", "Alt"]})

    def test_malformed_kitsu_identifier_is_rejected(self):
        self.assertEqual(AnimeMapper._parse_media_id("kitsu"), (None, None))
        self.assertEqual(AnimeMapper._parse_media_id("kitsu:"), (None, None))

    async def test_stop_cancels_and_drains_background_refresh(self):
        mapper = AnimeMapper()
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def refresh():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        mapper._refresh_task = asyncio.create_task(refresh())
        mapper._refresh_task.add_done_callback(mapper._handle_refresh_task_done)
        await started.wait()

        await mapper.stop()

        self.assertTrue(cancelled.is_set())
        self.assertIsNone(mapper._refresh_task)

    async def test_refresh_completion_observes_unexpected_error(self):
        mapper = AnimeMapper()

        async def refresh():
            raise RuntimeError("unexpected refresh failure")

        with patch("comet.services.anime.logger.warning") as warning:
            mapper._refresh_task = asyncio.create_task(refresh())
            mapper._refresh_task.add_done_callback(mapper._handle_refresh_task_done)
            await asyncio.sleep(0)
            await asyncio.sleep(0)

        self.assertIsNone(mapper._refresh_task)
        warning.assert_called_once_with(
            "Anime mapping refresh task failed: unexpected refresh failure"
        )
