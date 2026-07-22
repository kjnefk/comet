import unittest

from comet.scrapers.base import deduplicate_torrents
from comet.scrapers.models import ScrapeRequest
from comet.utils.languages import select_indexer_titles


class IndexerTitleTests(unittest.TestCase):
    def test_torrents_are_deduplicated_by_hash_and_file(self):
        torrents = [
            {"infoHash": "A" * 40, "fileIndex": 1, "title": "Canonical"},
            {"infoHash": "a" * 40, "fileIndex": 1, "title": "Localized"},
            {"infoHash": "a" * 40, "fileIndex": 2, "title": "Second file"},
        ]

        self.assertEqual(
            deduplicate_torrents(torrents),
            [torrents[0], torrents[2]],
        )

    def test_titles_follow_language_order_and_ignore_unconfigured_aliases(self):
        aliases = {
            "us": ["The Life Ahead"],
            "lang:fr": ["La Vie devant soi", "la vie devant soi"],
            "lang:it": ["La vita davanti a sé"],
            "br": ["Rosa e Momo"],
            "ez": ["Unattributed title"],
        }

        self.assertEqual(
            select_indexer_titles("The Life Ahead", aliases, ["it", "fr"]),
            (
                "The Life Ahead",
                "La vita davanti a sé",
                "La Vie devant soi",
            ),
        )

    def test_no_languages_preserves_the_single_canonical_query(self):
        self.assertEqual(
            select_indexer_titles("  The   Life Ahead  ", {"it": ["Alt"]}, []),
            ("The Life Ahead",),
        )

    def test_episode_variants_are_generated_for_every_title(self):
        request = ScrapeRequest(
            media_type="series",
            media_id="tt123:2:3",
            media_only_id="tt123",
            title="English",
            season=2,
            episode=3,
            search_titles=("English", "Localized"),
        )

        self.assertEqual(
            request.title_queries(include_episode_variants=True),
            (
                "English",
                "English S02",
                "English S02E03",
                "Localized",
                "Localized S02",
                "Localized S02E03",
            ),
        )
