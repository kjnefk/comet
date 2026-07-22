import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import comet.services.debrid_cache as debrid_cache


class DebridCacheTaskTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        await debrid_cache.shutdown_cache_writes()

    async def test_shutdown_drains_scheduled_cache_writes(self):
        started = asyncio.Event()
        finish = asyncio.Event()

        async def write_cache(service, availability):
            self.assertEqual(service, "realdebrid")
            self.assertEqual(availability, [{"info_hash": "hash"}])
            started.set()
            await finish.wait()

        with patch.object(debrid_cache, "cache_availability", new=write_cache):
            task = debrid_cache.schedule_cache_availability(
                "realdebrid", [{"info_hash": "hash"}]
            )
            await started.wait()
            shutdown = asyncio.create_task(debrid_cache.shutdown_cache_writes())
            await asyncio.sleep(0)
            self.assertFalse(shutdown.done())
            finish.set()
            await shutdown

        self.assertTrue(task.done())
        self.assertFalse(debrid_cache._cache_write_tasks)

    async def test_scheduled_failure_is_observed_and_removed(self):
        write_cache = AsyncMock(side_effect=RuntimeError("database unavailable"))
        fake_logger = MagicMock()

        with (
            patch.object(debrid_cache, "cache_availability", new=write_cache),
            patch.object(debrid_cache, "logger", new=fake_logger),
        ):
            task = debrid_cache.schedule_cache_availability("alldebrid", [])
            await asyncio.gather(task, return_exceptions=True)
            await asyncio.sleep(0)

        self.assertFalse(debrid_cache._cache_write_tasks)
        fake_logger.warning.assert_called_once()
