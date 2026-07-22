import unittest

from comet.metadata.trakt import _extract_aliases


class TraktAliasTests(unittest.TestCase):
    def test_aliases_are_deduplicated_in_provider_order(self):
        payload = [
            {"title": "First", "country": "us"},
            None,
            {"title": "Second", "country": "us"},
            {"title": "First", "country": "us"},
            {"title": "Fallback", "country": None},
            {"title": 123, "country": "gb"},
        ]

        self.assertEqual(
            _extract_aliases(payload),
            {"us": ["First", "Second"], "ez": ["Fallback"]},
        )

    def test_non_list_response_is_rejected(self):
        self.assertEqual(_extract_aliases({"error": "unauthorized"}), {})
