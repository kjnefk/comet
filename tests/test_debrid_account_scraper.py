import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from databases import Database

import comet.services.debrid_account_scraper as account_scraper


class DebridAccountSnapshotTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_snapshot_replacement_rolls_back_all_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.db"
            database = Database(f"sqlite+aiosqlite:///{path}")
            await database.connect()
            try:
                await database.execute(
                    """
                    CREATE TABLE debrid_account_magnets (
                        debrid_service TEXT NOT NULL,
                        account_key_hash TEXT NOT NULL,
                        magnet_id TEXT NOT NULL,
                        info_hash TEXT NOT NULL,
                        name TEXT NOT NULL,
                        size BIGINT,
                        status TEXT NOT NULL,
                        added_at REAL NOT NULL,
                        synced_at REAL NOT NULL,
                        PRIMARY KEY (debrid_service, account_key_hash, magnet_id)
                    )
                    """
                )
                await database.execute(
                    """
                    CREATE TABLE debrid_account_sync_state (
                        debrid_service TEXT NOT NULL,
                        account_key_hash TEXT NOT NULL,
                        last_sync_at REAL NOT NULL CHECK (last_sync_at < 0),
                        PRIMARY KEY (debrid_service, account_key_hash)
                    )
                    """
                )
                await database.execute(
                    """
                    INSERT INTO debrid_account_magnets (
                        debrid_service, account_key_hash, magnet_id, info_hash,
                        name, size, status, added_at, synced_at
                    ) VALUES (
                        'realdebrid', 'account', 'old', 'old-hash',
                        'old', 1, 'cached', 1, 1
                    )
                    """
                )

                replacement = {
                    "debrid_service": "realdebrid",
                    "account_key_hash": "account",
                    "magnet_id": "new",
                    "info_hash": "new-hash",
                    "name": "new",
                    "size": 2,
                    "status": "cached",
                    "added_at": 2,
                    "synced_at": 2,
                }
                with patch.object(account_scraper, "database", database):
                    with self.assertRaises(Exception):
                        await account_scraper._replace_account_snapshot(
                            "realdebrid", "account", 2, [replacement]
                        )

                rows = await database.fetch_all(
                    """
                    SELECT magnet_id, info_hash
                    FROM debrid_account_magnets
                    ORDER BY magnet_id
                    """
                )
                self.assertEqual(
                    [dict(row) for row in rows],
                    [{"magnet_id": "old", "info_hash": "old-hash"}],
                )
                self.assertIsNone(
                    await database.fetch_one("SELECT 1 FROM debrid_account_sync_state")
                )
            finally:
                await database.disconnect()


class DebridAccountTaskTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        await account_scraper.shutdown_account_sync_tasks()

    async def test_shutdown_releases_lock_when_task_has_not_started(self):
        lock = AsyncMock()
        sync = AsyncMock()

        with patch.object(account_scraper, "_sync_single_account", new=sync):
            task = account_scraper._schedule_sync_task(
                lock, object(), "realdebrid", "key", "ip", "account"
            )
            await account_scraper.shutdown_account_sync_tasks()

        self.assertTrue(task.cancelled())
        sync.assert_not_awaited()
        lock.release.assert_awaited_once()
        self.assertFalse(account_scraper._background_tasks)

    async def test_shutdown_cancels_running_sync_and_releases_lock(self):
        started = asyncio.Event()

        async def sync_account(*args):
            started.set()
            await asyncio.Event().wait()

        lock = AsyncMock()

        async def run_locked(operation):
            return await operation

        lock.run.side_effect = run_locked
        with patch.object(account_scraper, "_sync_single_account", new=sync_account):
            task = account_scraper._schedule_sync_task(
                lock, object(), "alldebrid", "key", "ip", "account"
            )
            await started.wait()
            await account_scraper.shutdown_account_sync_tasks()

        self.assertTrue(task.cancelled())
        lock.release.assert_awaited()
        self.assertFalse(account_scraper._background_tasks)
