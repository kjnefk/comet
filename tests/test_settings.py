import unittest

from pydantic import ValidationError

from comet.core.models import AppSettings


class AppSettingsTests(unittest.TestCase):
    def test_scraper_modes_normalize_documented_values(self):
        settings = AppSettings(
            _env_file=None,
            SCRAPE_NYAA="live",
            SCRAPE_TORBOX="both",
            SCRAPE_DMM="false",
        )

        self.assertEqual(settings.SCRAPE_NYAA, "live")
        self.assertIs(settings.SCRAPE_TORBOX, True)
        self.assertIs(settings.SCRAPE_DMM, False)

    def test_invalid_scraper_mode_fails_configuration(self):
        with self.assertRaisesRegex(
            ValidationError,
            "scraper mode must be false, true, both, live, or background",
        ):
            AppSettings(_env_file=None, SCRAPE_NYAA="lvie")
