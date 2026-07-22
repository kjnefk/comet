import unittest
from unittest.mock import patch

from comet.core.models import settings
from comet.scrapers.helpers.aiostreams import AIOStreamsConfig
from comet.scrapers.helpers.mediafusion import MediaFusionConfig


class ScraperHelperConfigTests(unittest.TestCase):
    def test_aiostreams_headers_are_isolated_and_refresh_atomically(self):
        with (
            patch.object(settings, "AIOSTREAMS_URL", ["https://one"]),
            patch.object(settings, "AIOSTREAMS_USER_UUID_AND_PASSWORD", ["first"]),
        ):
            config = AIOStreamsConfig()

        first = config.get_headers_for_credential("first")
        first["Authorization"] = "poisoned"
        self.assertNotEqual(
            config.get_headers_for_credential("first")["Authorization"], "poisoned"
        )
        self.assertEqual(config.get_headers_for_credential(None), {})

        with (
            patch.object(settings, "AIOSTREAMS_URL", ["https://two"]),
            patch.object(settings, "AIOSTREAMS_USER_UUID_AND_PASSWORD", ["second"]),
        ):
            config.precompute_headers()

        with self.assertRaisesRegex(KeyError, "unknown AIOStreams credential"):
            config.get_headers_for_credential("first")
        self.assertIn("Authorization", config.get_headers_for_credential("second"))

        with (
            patch.object(settings, "AIOSTREAMS_URL", ["https://bad"]),
            patch.object(settings, "AIOSTREAMS_USER_UUID_AND_PASSWORD", [1]),
            self.assertRaises(TypeError),
        ):
            config.precompute_headers()
        self.assertIn("Authorization", config.get_headers_for_credential("second"))

    def test_aiostreams_rejects_invalid_or_unknown_credentials(self):
        with self.assertRaisesRegex(TypeError, "non-empty string"):
            AIOStreamsConfig.encode_auth_header("")
        config = AIOStreamsConfig()
        for credential in ("", False, 1, []):
            with self.subTest(credential=credential), self.assertRaises(TypeError):
                config.get_headers_for_credential(credential)
        with self.assertRaises(KeyError):
            config.get_headers_for_credential("unknown")

    def test_mediafusion_headers_are_isolated_and_refresh_atomically(self):
        with (
            patch.object(settings, "MEDIAFUSION_URL", ["https://one"]),
            patch.object(settings, "MEDIAFUSION_API_PASSWORD", ["first"]),
        ):
            config = MediaFusionConfig()

        default_headers = config.get_headers_for_password(None)
        default_headers["encoded_user_data"] = "poisoned"
        self.assertNotEqual(
            config.get_headers_for_password(None)["encoded_user_data"], "poisoned"
        )
        self.assertIn("encoded_user_data", config.get_headers_for_password("first"))

        with (
            patch.object(settings, "MEDIAFUSION_URL", ["https://two"]),
            patch.object(settings, "MEDIAFUSION_API_PASSWORD", ["second"]),
        ):
            config.precompute_encodings()

        with self.assertRaisesRegex(KeyError, "unknown MediaFusion password"):
            config.get_headers_for_password("first")
        self.assertIn("encoded_user_data", config.get_headers_for_password("second"))

        with (
            patch.object(settings, "MEDIAFUSION_URL", ["https://bad"]),
            patch.object(settings, "MEDIAFUSION_API_PASSWORD", [1]),
            self.assertRaises(TypeError),
        ):
            config.precompute_encodings()
        self.assertIn("encoded_user_data", config.get_headers_for_password("second"))

    def test_mediafusion_rejects_invalid_or_unknown_passwords(self):
        with self.assertRaisesRegex(TypeError, "must be a string"):
            MediaFusionConfig.encode_api_password(None)
        config = MediaFusionConfig()
        for password in ("", False, 1, []):
            with self.subTest(password=password), self.assertRaises(TypeError):
                config.get_headers_for_password(password)
        with self.assertRaises(KeyError):
            config.get_headers_for_password("unknown")


if __name__ == "__main__":
    unittest.main()
