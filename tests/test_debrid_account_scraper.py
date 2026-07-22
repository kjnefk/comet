import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
