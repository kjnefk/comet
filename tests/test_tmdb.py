import unittest

from comet.metadata.tmdb import _extract_tmdb_id, _extract_upcoming_release_date


class TmdbMetadataTests(unittest.TestCase):
    def test_tmdb_id_extractor_isolates_malformed_results(self):
        payload = {
            "movie_results": [None, {"id": True}, {"id": "12"}],
            "tv_results": [{}, {"id": 456}],
        }

        self.assertEqual(_extract_tmdb_id(payload), "456")
        self.assertIsNone(_extract_tmdb_id([]))

    def test_release_date_extractor_keeps_valid_current_entries(self):
        payload = {
            "results": [
                None,
                {"release_dates": "invalid"},
                {
                    "release_dates": [
                        {"type": 4, "release_date": ["invalid"]},
                        {"type": 3, "release_date": "2025-01-01"},
                        {"type": 5, "release_date": "invalid"},
                        {"type": 5, "release_date": "2026-07-22T00:00:00Z"},
                        {"type": 4, "release_date": "2026-06-01T00:00:00Z"},
                    ]
                },
            ]
        }

        self.assertEqual(_extract_upcoming_release_date(payload), "2026-06-01")
        self.assertIsNone(_extract_upcoming_release_date({"results": {}}))
