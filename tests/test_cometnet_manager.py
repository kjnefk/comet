import asyncio
import unittest
from unittest.mock import patch

from comet.cometnet.manager import CometNetService


class CometNetManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_start_cleans_every_initialized_component(self):
        service = CometNetService(enabled=True)

        class Component:
            def __init__(self):
                self.stopped = 0

            async def stop(self):
                self.stopped += 1

        class Upnp:
            def __init__(self):
                self.stopped = 0

            def stop(self):
                self.stopped += 1

        transport = Component()
        discovery = Component()
        gossip = Component()
        upnp = Upnp()

        async def fail_start():
            service.transport = transport
            service.discovery = discovery
            service.gossip = gossip
            service.upnp = upnp
            service._state_save_task = asyncio.create_task(asyncio.Event().wait())
            raise RuntimeError("startup failed")

        with (
            patch.object(service, "_start", new=fail_start),
            patch("comet.cometnet.manager.shutdown_crypto_executor") as shutdown_crypto,
            self.assertRaisesRegex(RuntimeError, "startup failed"),
        ):
            await service.start()

        self.assertEqual(transport.stopped, 1)
        self.assertEqual(discovery.stopped, 1)
        self.assertEqual(gossip.stopped, 1)
        self.assertEqual(upnp.stopped, 1)
        self.assertIsNone(service._state_save_task)
        shutdown_crypto.assert_called_once_with()

    async def test_background_tasks_are_cancelled_and_drained(self):
        service = CometNetService()
        service._running = True
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def worker():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        task = service._start_background_task(worker())
        await started.wait()

        service._running = False
        await service._stop_background_tasks()

        self.assertTrue(task.cancelled())
        self.assertTrue(cancelled.is_set())
        self.assertFalse(service._background_tasks)

    async def test_background_task_is_not_started_after_shutdown(self):
        service = CometNetService()
        ran = False

        async def worker():
            nonlocal ran
            ran = True

        task = service._start_background_task(worker())
        await asyncio.sleep(0)

        self.assertIsNone(task)
        self.assertFalse(ran)
