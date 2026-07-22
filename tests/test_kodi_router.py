import importlib
import sys
import types
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).parents[1] / "kodi" / "plugin.video.comet"


def _load_router():
    xbmc = types.ModuleType("xbmc")
    xbmc.LOGINFO = 1
    xbmc.LOGERROR = 2

    xbmcaddon = types.ModuleType("xbmcaddon")

    class Addon:
        def getAddonInfo(self, key):
            return "plugin.video.comet" if key == "id" else ""

        def getSetting(self, key):
            del key
            return ""

    xbmcaddon.Addon = Addon

    xbmcgui = types.ModuleType("xbmcgui")
    xbmcgui.NOTIFICATION_ERROR = 1
    xbmcplugin = types.ModuleType("xbmcplugin")
    requests = types.ModuleType("requests")

    class Session:
        pass

    requests.Session = Session
    requests.RequestException = Exception

    sys.modules.update(
        {
            "requests": requests,
            "xbmc": xbmc,
            "xbmcaddon": xbmcaddon,
            "xbmcgui": xbmcgui,
            "xbmcplugin": xbmcplugin,
        }
    )
    sys.path.insert(0, str(PLUGIN_ROOT))
    original_argv = sys.argv
    sys.argv = ["plugin://plugin.video.comet", "1", ""]
    try:
        return importlib.import_module("lib.router")
    finally:
        sys.argv = original_argv
        sys.path.remove(str(PLUGIN_ROOT))


router = _load_router()


class KodiRouterTests(unittest.TestCase):
    def test_catalog_specs_isolate_malformed_current_records(self):
        manifest = {
            "catalogs": [
                None,
                "catalog",
                {"type": "movie"},
                {"type": "movie", "id": 3, "name": "Bad"},
                {"type": "movie", "id": "bad-name", "name": 3},
                {"type": "movie", "id": "popular", "extra": [None, "search"]},
                {
                    "type": "movie",
                    "id": "new",
                    "name": "New",
                    "extra": [None, {"name": "search"}],
                },
                {"type": "series", "id": "series"},
            ]
        }

        self.assertEqual(
            router._catalog_specs(manifest, "movie"),
            [
                {"id": "popular", "name": "popular", "has_search": False},
                {"id": "new", "name": "New", "has_search": True},
            ],
        )

    def test_catalog_specs_reject_invalid_root_shapes(self):
        for manifest in (None, [], {"catalogs": None}, {"catalogs": {}}):
            with self.subTest(manifest=manifest):
                self.assertEqual(router._catalog_specs(manifest, "movie"), [])

    def test_provider_meta_requires_current_object_shape(self):
        original = router.fetch_data
        try:
            for response in (None, [], {"meta": []}, {"meta": None}):
                with self.subTest(response=response):
                    router.fetch_data = lambda url, value=response: value
                    self.assertIsNone(router._fetch_provider_meta("movie", "tt123"))

            expected = {"id": "tt123", "name": "Title"}
            router.fetch_data = lambda url: {"meta": expected}
            self.assertIs(router._fetch_provider_meta("movie", "tt123"), expected)
        finally:
            router.fetch_data = original
