import unittest

from comet.services.filtering import filter_worker, quick_alias_match


class AliasFilteringTests(unittest.TestCase):
    def test_empty_alias_does_not_match_every_title(self):
        self.assertFalse(quick_alias_match("unrelated title", [""]))

    def test_empty_alias_cannot_bypass_worker_title_matching(self):
        torrents = [
            {
                "title": "Completely.Different.2024.1080p.WEB-DL.x264",
                "infoHash": "1" * 40,
            }
        ]

        actual = filter_worker(
            torrents,
            "The Matrix",
            1999,
            0,
            "movie",
            {"ez": [""]},
            False,
        )

        self.assertEqual(actual, [])


if __name__ == "__main__":
    unittest.main()
