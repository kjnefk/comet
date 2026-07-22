import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from comet.background_scraper.worker import BackgroundScraperWorker


class BackgroundWorkerLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_insert_failure_clears_published_runtime_state(self):
        worker = BackgroundScraperWorker()
        worker._insert_run_row = AsyncMock(side_effect=RuntimeError("insert failed"))
        worker._reset_running_items = AsyncMock()
        worker._finalize_run_row = AsyncMock()

        with self.assertRaisesRegex(RuntimeError, "insert failed"):
            await worker._run_scraping_cycle()

        self.assertIsNone(worker.current_run_id)
        self.assertIsNone(worker.metadata_scraper)
        worker._reset_running_items.assert_not_awaited()
        worker._finalize_run_row.assert_not_awaited()

    async def test_reset_failure_still_finalizes_and_clears_runtime_state(self):
        worker = BackgroundScraperWorker()
        worker._insert_run_row = AsyncMock()
        worker._reset_running_items = AsyncMock(
            side_effect=RuntimeError("reset failed")
        )
        worker._finalize_run_row = AsyncMock()

        with self.assertRaisesRegex(RuntimeError, "reset failed"):
            await worker._run_scraping_cycle()

        worker._finalize_run_row.assert_awaited_once()
        self.assertIsNone(worker.current_run_id)
        self.assertIsNone(worker.metadata_scraper)

    async def test_finalize_failure_clears_runtime_state(self):
        worker = BackgroundScraperWorker()
        worker._insert_run_row = AsyncMock()
        worker._reset_running_items = AsyncMock()
        worker._finalize_run_row = AsyncMock(
            side_effect=RuntimeError("finalize failed")
        )

        with self.assertRaisesRegex(RuntimeError, "finalize failed"):
            await worker._run_scraping_cycle()

        self.assertIsNone(worker.current_run_id)
        self.assertIsNone(worker.metadata_scraper)

    async def test_continuous_runner_propagates_cancellation(self):
        worker = BackgroundScraperWorker()
        entered_sleep = asyncio.Event()

        async def blocked_sleep(_delay):
            entered_sleep.set()
            await asyncio.Event().wait()

        with (
            patch(
                "comet.background_scraper.worker.DistributedLock.acquire",
                new=AsyncMock(return_value=False),
            ),
            patch("comet.background_scraper.worker.asyncio.sleep", new=blocked_sleep),
        ):
            task = asyncio.create_task(worker._run_continuous())
            await entered_sleep.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        self.assertFalse(worker.is_running)


class BackgroundWorkerQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_requeue_dead_items_rolls_back_both_tables_on_failure(self):
        worker = BackgroundScraperWorker()

        class Transaction:
            def __init__(self):
                self.exit_error = None

            async def __aenter__(self):
                return self

            async def __aexit__(self, error_type, error, traceback):
                self.exit_error = error

        transaction = Transaction()
        fetch_val = AsyncMock(side_effect=[2, 3])
        execute = AsyncMock(side_effect=[None, RuntimeError("episode update failed")])

        with (
            patch(
                "comet.background_scraper.worker.database.transaction",
                return_value=transaction,
            ),
            patch("comet.background_scraper.worker.database.fetch_val", fetch_val),
            patch("comet.background_scraper.worker.database.execute", execute),
            self.assertRaisesRegex(RuntimeError, "episode update failed"),
        ):
            await worker.requeue_dead_items()

        self.assertIsInstance(transaction.exit_error, RuntimeError)
        self.assertEqual(fetch_val.await_count, 2)
        self.assertEqual(execute.await_count, 2)


if __name__ == "__main__":
    unittest.main()
