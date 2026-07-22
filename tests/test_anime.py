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
