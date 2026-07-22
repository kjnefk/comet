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

    def test_non_positive_concurrency_fails_configuration(self):
        for field in (
            "NYAA_MAX_CONCURRENT_PAGES",
            "ANIMETOSHO_MAX_CONCURRENT_PAGES",
            "DMM_INGEST_CONCURRENT_WORKERS",
            "DMM_INGEST_BATCH_SIZE",
            "BITMAGNET_MAX_CONCURRENT_PAGES",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                    ValidationError, "work count must be a positive integer"
                ):
                    AppSettings(_env_file=None, **{field: 0})
