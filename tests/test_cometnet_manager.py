import asyncio
import unittest

from comet.cometnet.manager import CometNetService


class CometNetManagerTests(unittest.IsolatedAsyncioTestCase):
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
