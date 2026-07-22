import asyncio
import unittest

from comet.cometnet.discovery import DiscoveryService


class CometNetDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_stop_clears_cancelled_worker_reference(self):
        service = DiscoveryService()
        service._running = True
        service._discovery_task = asyncio.create_task(asyncio.Event().wait())
        task = service._discovery_task

        await service.stop()

        self.assertTrue(task.cancelled())
        self.assertIsNone(service._discovery_task)
