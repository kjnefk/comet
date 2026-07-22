import unittest
from unittest.mock import patch

from comet.services.indexer_manager import IndexerManager


class _ResponseContext:
    def __init__(self, status, payload=None, error=None):
        self.status = status
        self.payload = payload
        self.error = error
        self.exited = False
        self.json_called = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        self.exited = True

    async def json(self):
        self.json_called = True
        if self.error is not None:
            raise self.error
        return self.payload


class _Session:
    def __init__(self, response):
        self.response = response

    def get(self, url, **kwargs):
        del url, kwargs
        return self.response


class IndexerManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_prowlarr_response_closes_without_reading_error_body(self):
        response = _ResponseContext(503)
        manager = IndexerManager()

        with patch("comet.services.indexer_manager.settings.PROWLARR_URL", "http://p"):
            result = await manager._fetch_prowlarr_json(
                _Session(response), "/api/v1/indexer", {}
            )

        self.assertEqual(result, (503, None))
        self.assertFalse(response.json_called)
        self.assertTrue(response.exited)

    async def test_prowlarr_response_closes_when_json_decode_fails(self):
        response = _ResponseContext(200, error=ValueError("invalid JSON"))
        manager = IndexerManager()

        with (
            patch("comet.services.indexer_manager.settings.PROWLARR_URL", "http://p"),
            self.assertRaisesRegex(ValueError, "invalid JSON"),
        ):
            await manager._fetch_prowlarr_json(
                _Session(response), "/api/v1/indexer", {}
            )

        self.assertTrue(response.json_called)
        self.assertTrue(response.exited)
